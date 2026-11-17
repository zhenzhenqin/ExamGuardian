import json
from datetime import UTC, datetime
from functools import wraps
from uuid import UUID

from django.conf import settings
from django.core import signing
from django.db import OperationalError, transaction
from django.http import JsonResponse
from django.urls import reverse
from django.utils.crypto import constant_time_compare
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .models import CaptureEvent, Exam, Session
from .recording import UploadError, store_segment
from .services import elapsed, finish, start_session

SALT = "exam-guardian.student-upload"
EVENT_CODES = {
    "device_denied", "device_failed", "track_ended", "record_error", "network_lost",
    "network_restored", "client_ready", "client_paused", "queue_full", "storage_unavailable",
    "segment_rejected",
}


def reply(data, status=200):
    response = JsonResponse(data, status=status)
    response["Cache-Control"] = "no-store"
    return response


def error(message, status=400):
    return reply({"error": message}, status)


def checked_int(value, minimum=0, maximum=2**31 - 1):
    if type(value) not in (str, int):
        raise ValueError
    number = int(value)
    if not minimum <= number <= maximum:
        raise ValueError
    return number


def json_data(request):
    body = json.loads(request.body)
    if not isinstance(body, dict):
        raise ValueError
    return body


def start_payload(session, consent):
    data = {"state": session.state, "elapsedMs": elapsed(session), "segmentMs": settings.EG_SEGMENT_MS}
    if consent and session.state == Session.State.ACTIVE:
        data.update(
            sessionId=str(session.pk),
            token=signing.dumps(str(session.pk), salt=SALT),
            segmentUrl=reverse("evidence_segment", args=[session.pk]),
            eventUrl=reverse("evidence_event", args=[session.pk]),
            statusUrl=reverse("evidence_status", args=[session.pk]),
        )
    return data


def integration(function):
    @wraps(function)
    def wrapped(request):
        authorization = request.headers.get("Authorization", "")
        secret = settings.EG_MOODLE_SECRET
        if not secret or not constant_time_compare(authorization, f"Bearer {secret}"):
            return error("集成服务凭证无效。", 403)
        try:
            return function(request, json_data(request))
        except (ValueError, TypeError, KeyError, OverflowError):
            return error("作答事件格式无效。")
        except OperationalError:
            return error("服务繁忙，稍后重试。", 503)
    return wrapped


@csrf_exempt
@require_POST
@integration
def moodle_start(request, body):
    cmid = checked_int(body.get("cmid"), 1)
    quiz_id = checked_int(body.get("quizId"), 1)
    attempt = str(checked_int(body.get("attemptId"), 1))
    student = body.get("studentRef")
    consent = body.get("consent")
    if not isinstance(student, str) or len(student) != 64 or any(c not in "0123456789abcdef" for c in student):
        raise ValueError
    if type(consent) is not bool:
        raise ValueError
    exam = Exam.objects.filter(source_site=settings.EG_MOODLE_SITE, cmid=cmid, quiz_id=quiz_id, enabled=True).first()
    if exam is None:
        return error("该测验未启用证据采集。", 403)
    session = start_session(exam, attempt, student, consent)
    return reply(start_payload(session, consent))


@csrf_exempt
@require_POST
@integration
@transaction.atomic
def moodle_end(request, body):
    attempt = str(checked_int(body["attemptId"], 1))
    ended = datetime.fromtimestamp(checked_int(body["endedAt"], 1, 4102444800), tz=UTC)
    session = Session.objects.select_for_update().filter(source_site=settings.EG_MOODLE_SITE, attempt=attempt).first()
    if session:
        finish(session, ended)
    return reply({"ok": True})


def student(function):
    @wraps(function)
    def wrapped(request, session_id):
        authorization = request.headers.get("Authorization", "")
        if not authorization.startswith("Bearer "):
            return error("缺少会话凭证。", 403)
        try:
            value = signing.loads(authorization[7:], salt=SALT,
                                  max_age=settings.EG_MAX_SESSION_SECONDS + settings.EG_UPLOAD_GRACE_SECONDS)
        except signing.BadSignature:
            return error("会话凭证失效。", 403)
        if value != str(session_id):
            return error("该凭证不属于当前作答。", 403)
        session = Session.objects.filter(pk=session_id, started_at__isnull=False).exclude(state=Session.State.PURGING).first()
        if not session:
            return error("找不到该采集会话。", 404)
        try:
            return function(request, session)
        except (ValueError, TypeError, KeyError, OverflowError):
            return error("采集请求参数无效。")
        except UploadError as exc:
            return error(str(exc), exc.status)
        except OperationalError:
            return error("服务繁忙，稍后重试。", 503)
    return wrapped


@require_GET
def health(request):
    return reply({"status": "ok"})


@require_GET
@student
def status(request, session):
    return reply({"state": session.state, "segments": session.segments.count(), "elapsedMs": elapsed(session)})


@csrf_exempt
@require_POST
@student
def segment(request, session):
    if "clip" not in request.FILES:
        return error("缺少录制文件。")
    key = UUID(request.POST["key"])
    start = checked_int(request.POST["startMs"])
    end = checked_int(request.POST["endMs"])
    device = checked_int(request.POST["deviceAtMs"], 0, 4102444800000)
    saved, created = store_segment(session.pk, key, start, end, device, request.FILES["clip"])
    return reply({"id": saved.pk, "sha256": saved.sha256, "startMs": saved.start_ms,
                  "endMs": saved.end_ms}, 201 if created else 200)


@csrf_exempt
@require_POST
@student
def event(request, session):
    body = json_data(request)
    key, code = UUID(body["key"]), body["code"]
    if code not in EVENT_CODES:
        return error("不支持的采集状态。")
    with transaction.atomic():
        session = Session.objects.select_for_update().get(pk=session.pk)
        if session.state not in [Session.State.ACTIVE, Session.State.CLOSING]:
            return error("该作答已结束接收。", 409)
        at = checked_int(body["atMs"], maximum=min(elapsed(session) + 2000, settings.EG_MAX_SESSION_SECONDS * 1000))
        if session.events.count() >= 300 and not session.events.filter(key=key).exists():
            return error("采集状态记录已达上限。", 413)
        CaptureEvent.objects.get_or_create(session=session, key=key, defaults={"code": code, "at_ms": at})
    return reply({"ok": True})
