import hashlib
import json
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import AnalysisJob, Audit, Session

CONSENT_VERSION = "2026-11-17"
FINAL_STATES = [Session.State.COMPLETE, Session.State.INCOMPLETE]
IDLE_SECONDS = 90


def elapsed(session, at=None):
    if not session.started_at:
        return 0
    return max(0, int(((at or timezone.now()) - session.started_at).total_seconds() * 1000))


@transaction.atomic
def start_session(exam, attempt, student_ref, consent):
    session, _ = Session.objects.select_for_update().get_or_create(
        source_site=exam.source_site, attempt=attempt,
        defaults={"exam": exam, "student_ref": student_ref, "location": exam.location},
    )
    if session.exam_id != exam.pk or session.student_ref != student_ref:
        raise ValueError("作答身份与已有记录不一致。")
    if session.state in [Session.State.WAITING, Session.State.DECLINED]:
        now = timezone.now()
        session.consent_version = CONSENT_VERSION
        session.consent_at = now
        session.state = Session.State.ACTIVE if consent else Session.State.DECLINED
        if consent:
            session.started_at = now
        else:
            session.expires_at = now + timedelta(days=exam.retention_days)
        session.save()
        Audit.objects.create(action="consent" if consent else "declined", session_ref=session.pk)
    return session


def finish(session, ended_at):
    if session.state != Session.State.ACTIVE:
        return
    now = timezone.now()
    session.ended_at = min(ended_at, now)
    session.end_ms = min(elapsed(session, session.ended_at), settings.EG_MAX_SESSION_SECONDS * 1000)
    session.close_after = session.ended_at + timedelta(seconds=settings.EG_UPLOAD_GRACE_SECONDS)
    session.expires_at = now + timedelta(days=session.exam.retention_days)
    session.state = Session.State.CLOSING
    session.save(update_fields=["ended_at", "end_ms", "close_after", "expires_at", "state"])


def coverage(session, segments, *, final=False):
    end_ms = session.end_ms if session.ended_at else (elapsed(session) if final else 0)
    if not end_ms:
        end_ms = max((segment.end_ms for segment in segments), default=0)
    cursor = 0
    gaps = []
    for segment in segments:
        start = min(segment.start_ms, end_ms)
        end = min(segment.end_ms, end_ms)
        if start > cursor:
            gaps.append((cursor, start))
        cursor = max(cursor, end)
    if cursor < end_ms:
        gaps.append((cursor, end_ms))
    covered = end_ms - sum(end - start for start, end in gaps)
    return end_ms, covered, gaps


@transaction.atomic
def finalize(session_id, *, now=None):
    now = now or timezone.now()
    session = Session.objects.select_for_update().filter(pk=session_id, state=Session.State.CLOSING,
                                                        close_after__lte=now).first()
    if not session:
        return
    end, covered, gaps = coverage(session, list(session.segments.all()), final=True)
    has_long_gap = any(end - start > 1000 for start, end in gaps)
    session.state = (Session.State.COMPLETE if end and covered / end >= 0.99 and not has_long_gap
                     else Session.State.INCOMPLETE)
    session.save(update_fields=["state"])
    Audit.objects.create(action=session.state, session_ref=session.pk)


def rule_snapshot(rules):
    return hashlib.sha256(json.dumps(rules, sort_keys=True).encode()).hexdigest()[:12]


def create_job(session, vision="mediapipe"):
    rules = session.exam.rules()
    return AnalysisJob.objects.create(session=session, rules=rules, rule_version=rule_snapshot(rules), vision=vision)


def media_path(name):
    root = settings.EG_MEDIA_ROOT.resolve()
    path = (root / name).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Invalid media path")
    return path


def purge(session_id):
    with transaction.atomic():
        session = Session.objects.select_for_update().get(pk=session_id)
        if session.jobs.filter(state=AnalysisJob.State.RUNNING).exists():
            return False
        session.state = Session.State.PURGING
        session.save(update_fields=["state"])
    for name in session.segments.values_list("file_name", flat=True):
        media_path(name).unlink(missing_ok=True)
    folder = media_path(str(session.pk))
    # Private session directory may also contain an unpublished file from a stopped upload.
    if folder.is_dir():
        for file in folder.glob("*.webm"):
            file.unlink(missing_ok=True)
        if not any(folder.iterdir()):
            folder.rmdir()
    with transaction.atomic():
        deleted, _ = Session.objects.filter(pk=session.pk, state=Session.State.PURGING).delete()
        if deleted:
            Audit.objects.filter(session_ref=session.pk).delete()
            Audit.objects.create(action="purged", session_ref=session.pk)
    return True
