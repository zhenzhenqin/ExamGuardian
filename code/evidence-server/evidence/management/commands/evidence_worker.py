import logging
import time
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from evidence.detectors import Faces, analyze_segment, versions
from evidence.models import SCENARIOS, AnalysisJob, Audit, Flag, Observation, Session
from evidence.services import finalize, finish, media_path, purge

logger = logging.getLogger(__name__)


@transaction.atomic
def claim():
    candidate = AnalysisJob.objects.filter(state=AnalysisJob.State.PENDING).order_by("pk").first()
    if not candidate:
        return None
    session = Session.objects.select_for_update().filter(pk=candidate.session_id).first()
    if not session or session.state == Session.State.PURGING:
        return None
    found = AnalysisJob.objects.filter(pk=candidate.pk, state=AnalysisJob.State.PENDING).update(
        state=AnalysisJob.State.RUNNING, started_at=timezone.now(), error="")
    return candidate if found else None


def analyze(job, sample=analyze_segment, detector=Faces):
    faces = None
    try:
        faces = detector(job.vision)
        tool_versions = versions(faces)
        observations, flags = [], []
        last_by_kind = {}
        for segment in job.session.segments.all():
            duration = segment.end_ms - segment.start_ms
            for kind, start, end in sample(media_path(segment.file_name), faces, duration):
                start += segment.start_ms
                end += segment.start_ms
                observations.append(Observation(job=job, segment=segment, kind=kind, start_ms=start, end_ms=end))
                if kind not in job.rules:
                    continue
                tail = last_by_kind.get(kind)
                if tail and -250 <= start - tail[2] <= 150:
                    tail[2] = max(tail[2], end)
                else:
                    tail = [segment, start, end, kind]
                    flags.append(tail)
                    last_by_kind[kind] = tail
        published = []
        for segment, start, end, kind in flags:
            threshold, weight = job.rules[kind]
            if end - start >= threshold:
                published.append(Flag(
                    job=job, segment=segment, kind=kind, start_ms=start, end_ms=end, priority=weight,
                    reason=f"{SCENARIOS[kind]} {(end-start)/1000:.2f} 秒，达到 {threshold/1000:g} 秒阈值",
                ))
        with transaction.atomic():
            if not AnalysisJob.objects.select_for_update().filter(pk=job.pk, state=AnalysisJob.State.RUNNING).exists():
                return
            Observation.objects.bulk_create(observations)
            Flag.objects.bulk_create(published)
            AnalysisJob.objects.filter(pk=job.pk).update(
                state=AnalysisJob.State.DONE, versions=tool_versions,
                priority=sum(flag.priority for flag in published), finished_at=timezone.now(),
            )
            Audit.objects.create(action="analyzed", session_ref=job.session_id)
    except Exception as exc:
        logger.exception("Analysis job %s failed", job.pk)
        AnalysisJob.objects.filter(pk=job.pk, state=AnalysisJob.State.RUNNING).update(
            state=AnalysisJob.State.FAILED, error=str(exc)[:200], finished_at=timezone.now(),
        )
    finally:
        if faces is not None:
            faces.close()


def maintain(now):
    AnalysisJob.objects.filter(state=AnalysisJob.State.RUNNING, started_at__lt=now - timedelta(hours=6)).update(
        state=AnalysisJob.State.FAILED, error="分析任务超时，可重新安排。", finished_at=now)
    limit = now - timedelta(seconds=settings.EG_MAX_SESSION_SECONDS)
    for session_id in Session.objects.filter(state=Session.State.ACTIVE, started_at__lte=limit).values_list("pk", flat=True):
        with transaction.atomic():
            session = Session.objects.select_for_update().get(pk=session_id)
            finish(session, session.started_at + timedelta(seconds=settings.EG_MAX_SESSION_SECONDS))
    closing = Session.objects.filter(state=Session.State.CLOSING, close_after__lte=now).values_list("pk", flat=True)
    for session_id in closing:
        finalize(session_id, now=now)
    expired = Session.objects.filter(expires_at__lte=now).values_list("pk", flat=True)
    for session_id in expired:
        try:
            purge(session_id)
        except OSError:
            logger.exception("Evidence purge will retry for %s", session_id)
    cutoff = (now - timedelta(hours=1)).timestamp()
    for temp in settings.EG_MEDIA_ROOT.glob("upload-*.tmp"):
        if temp.is_file() and temp.stat().st_mtime < cutoff:
            temp.unlink(missing_ok=True)


class Command(BaseCommand):
    help = "Finalize intake, process analyses and purge expired evidence. Run one worker per deployment."

    def add_arguments(self, parser):
        parser.add_argument("--watch", action="store_true")
        parser.add_argument("--poll", type=int, default=5)

    def handle(self, **options):
        while True:
            maintain(timezone.now())
            while job := claim():
                analyze(job)
            if not options["watch"]:
                return
            time.sleep(max(1, options["poll"]))
