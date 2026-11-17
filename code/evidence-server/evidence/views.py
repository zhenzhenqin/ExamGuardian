import re
from uuid import uuid4

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import FileResponse, Http404, HttpResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .api import error, reply, start_payload
from .models import PANEL, REVIEWER, AnalysisJob, Audit, Exam, ReviewEntry, Segment, Session
from .services import FINAL_STATES, coverage, create_job, finish, media_path, start_session

EVENT_LABELS = {
    "device_denied": "设备权限被拒绝", "device_failed": "设备不可用", "track_ended": "设备断开",
    "record_error": "录制失败", "network_lost": "网络断开", "network_restored": "网络恢复",
    "client_ready": "设备已连接", "client_paused": "录制暂停", "queue_full": "待上传队列已满",
    "storage_unavailable": "浏览器存储不可用", "segment_rejected": "片段接收失败",
}


def home(request):
    if request.user.is_authenticated or not settings.EG_ENABLE_STANDALONE:
        return redirect("review_list")
    return redirect("demo")


def student_demo(request):
    if not settings.EG_ENABLE_STANDALONE:
        raise Http404
    if "demo_student" not in request.session:
        request.session["demo_student"] = uuid4().hex[:12]
    return request.session["demo_student"]


@require_GET
def demo_script(request):
    if not settings.EG_ENABLE_STANDALONE:
        raise Http404
    script = settings.EG_CAPTURE_SCRIPT
    if not script.is_file():
        raise Http404
    return FileResponse(script.open("rb"), content_type="text/javascript")


@require_GET
def demo(request):
    student_demo(request)
    if "attempt" not in request.session:
        request.session["attempt"] = uuid4().hex[:12]
    return render(request, "evidence/demo.html", {"attempt": request.session["attempt"],
                   "page": 2 if request.GET.get("page") == "2" else 1})


@require_POST
def demo_session(request):
    student = student_demo(request)
    attempt = request.session.get("attempt")
    if not attempt:
        return error("请从练习页面打开作答。", 403)
    consent = request.POST.get("consent")
    if consent not in ("0", "1"):
        return error("请先确认录制选择。")
    exam, _ = Exam.objects.get_or_create(source_site="standalone", cmid=1, defaults={
        "name": "独立采集练习", "quiz_id": 1, "location": "本机练习环境",
    })
    if not exam.enabled:
        return error("该练习未启用证据采集。", 403)
    session = start_session(exam, attempt, student, consent == "1")
    return reply(start_payload(session, consent == "1"))


@require_POST
@transaction.atomic
def demo_end(request):
    student = student_demo(request)
    session = Session.objects.select_for_update().filter(source_site="standalone",
        attempt=request.session.get("attempt"), student_ref=student).first()
    if session:
        finish(session, timezone.now())
    request.session.pop("attempt", None)
    return render(request, "evidence/demo_done.html", {"session": session})


def scope(request):
    if request.user.is_superuser:
        return Session.objects.all()
    if not request.user.groups.filter(name__in=[REVIEWER, PANEL]).exists():
        raise PermissionDenied
    return Session.objects.filter(assignments__user=request.user)


def time_label(ms):
    minutes, seconds = divmod(ms // 1000, 60)
    return f"{minutes:02d}:{seconds:02d}.{ms % 1000:03d}"


@login_required
@require_GET
def review_list(request):
    sessions = scope(request).exclude(state=Session.State.PURGING).select_related("exam")
    attempt = request.GET.get("attempt", "").strip()[:80]
    if attempt:
        sessions = sessions.filter(attempt=attempt)
    return render(request, "evidence/review_list.html", {"sessions": sessions[:100], "attempt": attempt})


@login_required
@require_http_methods(["GET", "POST"])
def review_detail(request, session_id):
    sessions = scope(request).exclude(state=Session.State.PURGING).select_related("exam")
    session = get_object_or_404(sessions, pk=session_id)
    can_review = request.user.is_superuser or request.user.groups.filter(name=REVIEWER).exists()
    can_comment = request.user.groups.filter(name=PANEL).exists()
    if request.method == "POST":
        decision = request.POST.get("decision")
        note = request.POST.get("note", "").strip()
        if not note or len(note) > 2000:
            return HttpResponse("请输入 1–2000 字的复核说明。", status=400)
        if decision == ReviewEntry.Decision.COMMENT:
            if not (can_comment or request.user.is_superuser):
                raise PermissionDenied
        elif decision not in ReviewEntry.Decision.values or not can_review:
            raise PermissionDenied
        with transaction.atomic():
            session = get_object_or_404(sessions.select_for_update(), pk=session_id)
            older = None
            if revision := request.POST.get("revision"):
                if not revision.isascii() or not revision.isdecimal() or len(revision) > 19:
                    return HttpResponse("无效的意见编号。", status=400)
                older = get_object_or_404(session.entries, pk=int(revision), author=request.user)
                if (older.decision == ReviewEntry.Decision.COMMENT) != (decision == ReviewEntry.Decision.COMMENT):
                    raise PermissionDenied
            ReviewEntry.objects.create(session=session, author=request.user, decision=decision, note=note, supersedes=older)
            Audit.objects.create(action="review_revision" if older else "review_entry",
                                 session_ref=session.pk, actor=request.user)
        return redirect("review_detail", session_id=session.pk)
    segments = list(session.segments.all())
    end, covered, gaps = coverage(session, segments, final=session.state != Session.State.DECLINED)
    jobs = list(session.jobs.order_by("-created_at")[:20])
    selected = next((job for job in jobs if str(job.pk) == request.GET.get("job")), None)
    if not selected:
        selected = next((job for job in jobs if job.state == AnalysisJob.State.DONE), None)
    exam_link = ""
    if settings.EG_MOODLE_REVIEW_BASE and session.source_site == settings.EG_MOODLE_SITE and session.attempt.isdecimal():
        exam_link = f"{settings.EG_MOODLE_REVIEW_BASE.rstrip('/')}/mod/quiz/review.php?attempt={session.attempt}"
    return render(request, "evidence/review_detail.html", {
        "session": session, "exam_link": exam_link, "segments": [{
            "id": s.pk, "start": time_label(s.start_ms), "end": time_label(s.end_ms), "sha": s.sha256,
            "url": reverse("media", args=[s.pk]), "size": s.size,
        } for s in segments],
        "coverage": f"{(covered / end * 100):.1f}%" if end else "—",
        "covered": time_label(covered), "end": time_label(end),
        "gaps": [(time_label(a), time_label(b)) for a, b in gaps if b - a >= 100],
        "events": [(time_label(e.at_ms), EVENT_LABELS.get(e.code, e.code)) for e in session.events.all()],
        "entries": session.entries.select_related("author").order_by("-created_at"),
        "can_review": can_review, "can_comment": can_comment or request.user.is_superuser,
        "jobs": jobs, "selected": selected,
        "flags": [{
            "reason": flag.reason, "segment": flag.segment_id, "priority": flag.priority,
            "start": time_label(flag.start_ms), "end": time_label(flag.end_ms),
            "offset": f"{max(0, flag.start_ms - flag.segment.start_ms - 1000) / 1000:.3f}",
            "url": reverse("media", args=[flag.segment_id]),
        } for flag in (selected.flags.select_related("segment").order_by("start_ms") if selected else [])],
    })


@login_required
@require_POST
@transaction.atomic
def queue_analysis(request, session_id):
    if not request.user.is_superuser:
        raise PermissionDenied
    session = get_object_or_404(Session.objects.select_for_update().select_related("exam"), pk=session_id,
                               state__in=FINAL_STATES)
    vision = request.POST.get("vision", "mediapipe")
    if vision not in {"mediapipe", "haar"} or not session.segments.exists():
        return HttpResponse("需要有可用片段和有效检测工具。", status=400)
    if not session.jobs.filter(state__in=[AnalysisJob.State.PENDING, AnalysisJob.State.RUNNING]).exists():
        create_job(session, vision)
        Audit.objects.create(action="queued_analysis", session_ref=session.pk, actor=request.user)
    return redirect("review_detail", session_id=session.pk)


def media_headers(response):
    response["Cache-Control"] = "private, no-store"
    response["Content-Security-Policy"] = "default-src 'none'; sandbox"
    response["Accept-Ranges"] = "bytes"
    return response


@login_required
@require_GET
def media(request, segment_id):
    source = scope(request).exclude(state=Session.State.PURGING)
    segment = get_object_or_404(Segment.objects.filter(session__in=source), pk=segment_id)
    path = media_path(segment.file_name)
    if not path.is_file():
        raise Http404
    if settings.EG_ACCEL_MEDIA:
        response = HttpResponse(content_type="video/webm")
        response["X-Accel-Redirect"] = f"/_eg_private/{segment.file_name}"
        return media_headers(response)
    requested = request.headers.get("Range")
    if requested is None:
        return media_headers(FileResponse(path.open("rb"), content_type="video/webm"))
    size = path.stat().st_size
    bounds = re.fullmatch(r"bytes=(\d{0,18})-(\d{0,18})", requested)
    if bounds and any(bounds.groups()):
        start, end = bounds.groups()
        if start:
            start, end = int(start), min(int(end), size - 1) if end else size - 1
        else:
            start, end = max(0, size - int(end)), size - 1
        if start <= end:
            def read_range():
                with path.open("rb") as file:
                    file.seek(start)
                    left = end - start + 1
                    while left and (data := file.read(min(65536, left))):
                        yield data
                        left -= len(data)
            response = StreamingHttpResponse(read_range(), status=206, content_type="video/webm")
            response["Content-Range"] = f"bytes {start}-{end}/{size}"
            response["Content-Length"] = end - start + 1
            return media_headers(response)
    response = HttpResponse(status=416)
    response["Content-Range"] = f"bytes */{size}"
    return media_headers(response)
