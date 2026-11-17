import uuid

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

SCENARIOS = {
    "NO_FACE": "未检出人脸",
    "ONE_FACE": "检出一张脸",
    "MULTIPLE_FACES": "检出多张脸",
    "VOICE_ACTIVITY": "检测到语音活动",
}
REVIEWER = "证据复核员"
PANEL = "评审成员"


class Exam(models.Model):
    name = models.CharField(max_length=180)
    source_site = models.CharField(max_length=80)
    cmid = models.PositiveIntegerField()
    quiz_id = models.PositiveIntegerField()
    enabled = models.BooleanField(default=True)
    location = models.CharField(max_length=120)
    retention_days = models.PositiveSmallIntegerField(default=30, validators=[MinValueValidator(1), MaxValueValidator(365)])
    no_face_ms = models.PositiveIntegerField(default=3000, validators=[MinValueValidator(250)])
    multiple_faces_ms = models.PositiveIntegerField(default=2000, validators=[MinValueValidator(250)])
    voice_ms = models.PositiveIntegerField(default=3000, validators=[MinValueValidator(20)])
    no_face_weight = models.PositiveSmallIntegerField(default=1)
    multiple_faces_weight = models.PositiveSmallIntegerField(default=2)
    voice_weight = models.PositiveSmallIntegerField(default=1)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["source_site", "cmid"], name="unique_exam_activity")]

    def __str__(self):
        return f"{self.name} ({self.source_site}/{self.cmid})"

    def rules(self):
        return {
            "NO_FACE": [self.no_face_ms, self.no_face_weight],
            "MULTIPLE_FACES": [self.multiple_faces_ms, self.multiple_faces_weight],
            "VOICE_ACTIVITY": [self.voice_ms, self.voice_weight],
        }


class Session(models.Model):
    class State(models.TextChoices):
        WAITING = "waiting", "等待同意"
        DECLINED = "declined", "未同意"
        ACTIVE = "active", "采集中"
        CLOSING = "closing", "归档中"
        COMPLETE = "complete", "已归档"
        INCOMPLETE = "incomplete", "部分素材缺失"
        PURGING = "purging", "删除中"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    exam = models.ForeignKey(Exam, on_delete=models.PROTECT)
    source_site = models.CharField(max_length=80)
    attempt = models.CharField(max_length=80)
    student_ref = models.CharField(max_length=100)
    location = models.CharField(max_length=120)
    created_at = models.DateTimeField(auto_now_add=True)
    consent_version = models.CharField(max_length=20, blank=True)
    consent_at = models.DateTimeField(null=True)
    started_at = models.DateTimeField(null=True)
    ended_at = models.DateTimeField(null=True)
    close_after = models.DateTimeField(null=True, db_index=True)
    end_ms = models.PositiveIntegerField(default=0)
    expires_at = models.DateTimeField(null=True, db_index=True)
    state = models.CharField(max_length=12, choices=State.choices, default=State.WAITING)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["source_site", "attempt"], name="unique_source_attempt")]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.exam.name} / {self.attempt}"


class Segment(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name="segments")
    key = models.UUIDField()
    start_ms = models.PositiveIntegerField()
    end_ms = models.PositiveIntegerField()
    duration_ms = models.PositiveIntegerField()
    received_at = models.DateTimeField(auto_now_add=True)
    device_at_ms = models.PositiveBigIntegerField(null=True)
    size = models.PositiveIntegerField()
    sha256 = models.CharField(max_length=64)
    file_name = models.CharField(max_length=110)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["session", "key"], name="unique_segment_key")]
        indexes = [models.Index(fields=["session", "start_ms"])]
        ordering = ["start_ms", "id"]


class CaptureEvent(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name="events")
    key = models.UUIDField()
    code = models.CharField(max_length=40)
    at_ms = models.PositiveIntegerField()
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["session", "key"], name="unique_event_key")]
        ordering = ["at_ms", "id"]


class Assignment(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name="assignments")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["session", "user"], name="unique_review_assignment")]

    def __str__(self):
        return f"{self.session} → {self.user}"


class ReviewEntry(models.Model):
    class Decision(models.TextChoices):
        EXPLAINED = "explained", "有合理解释"
        FOLLOW_UP = "follow_up", "需要进一步复核"
        INCONCLUSIVE = "inconclusive", "证据不足"
        COMMENT = "comment", "评审评论"

    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name="entries")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    decision = models.CharField(max_length=16, choices=Decision.choices)
    note = models.TextField(max_length=2000)
    supersedes = models.ForeignKey("self", null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)


class AnalysisJob(models.Model):
    class State(models.TextChoices):
        PENDING = "pending", "待分析"
        RUNNING = "running", "分析中"
        DONE = "done", "已分析"
        FAILED = "failed", "失败"

    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name="jobs")
    state = models.CharField(max_length=10, choices=State.choices, default=State.PENDING)
    rules = models.JSONField()
    rule_version = models.CharField(max_length=32)
    vision = models.CharField(max_length=20, default="mediapipe")
    versions = models.JSONField(default=dict)
    priority = models.PositiveIntegerField(default=0)
    error = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True)
    finished_at = models.DateTimeField(null=True)


class Observation(models.Model):
    job = models.ForeignKey(AnalysisJob, on_delete=models.CASCADE, related_name="observations")
    segment = models.ForeignKey(Segment, on_delete=models.CASCADE)
    kind = models.CharField(max_length=20, choices=list(SCENARIOS.items()))
    start_ms = models.PositiveIntegerField()
    end_ms = models.PositiveIntegerField()


class Flag(models.Model):
    job = models.ForeignKey(AnalysisJob, on_delete=models.CASCADE, related_name="flags")
    segment = models.ForeignKey(Segment, on_delete=models.CASCADE)
    kind = models.CharField(max_length=20, choices=list(SCENARIOS.items()))
    start_ms = models.PositiveIntegerField()
    end_ms = models.PositiveIntegerField()
    reason = models.CharField(max_length=180)
    priority = models.PositiveIntegerField()


class Audit(models.Model):
    action = models.CharField(max_length=40)
    session_ref = models.UUIDField(db_index=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    when = models.DateTimeField(auto_now_add=True)
