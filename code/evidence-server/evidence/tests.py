from datetime import timedelta
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

import av
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core import signing
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .api import SALT
from .management.commands.evidence_worker import analyze, claim, maintain
from .management.commands.evaluate_evidence import score
from .models import PANEL, REVIEWER, AnalysisJob, Assignment, Audit, Exam, ReviewEntry, Session
from .services import coverage, create_job


def media_sample(*, dual=True):
    content = BytesIO()
    with av.open(content, "w", format="webm") as recording:
        video = recording.add_stream("libvpx", rate=10)
        video.width, video.height, video.pix_fmt = 80, 60, "yuv420p"
        audio = recording.add_stream("libopus", rate=48000) if dual else None
        if audio:
            audio.layout = "mono"
        for _ in range(10):
            frame = av.VideoFrame(80, 60, "yuv420p")
            for plane in frame.planes:
                plane.update(bytes([128]) * plane.buffer_size)
            recording.mux(video.encode(frame))
            if audio:
                sound = av.AudioFrame(format="s16", layout="mono", samples=4800)
                sound.sample_rate = 48000
                sound.planes[0].update(bytes(sound.planes[0].buffer_size))
                recording.mux(audio.encode(sound))
        recording.mux(video.encode(None))
        if audio:
            recording.mux(audio.encode(None))
    return content.getvalue()


@override_settings(EG_MOODLE_SITE="test-moodle", EG_MOODLE_SECRET="test-integration-credential", EG_UPLOAD_GRACE_SECONDS=5)
class EvidenceAcceptance(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.exam = Exam.objects.create(name="Lab", source_site="test-moodle", cmid=6, quiz_id=2, location="Room")
        users = get_user_model()
        cls.reviewer = users.objects.create_user("reviewer")
        cls.reviewer.groups.add(Group.objects.create(name=REVIEWER))
        cls.panel = users.objects.create_user("panel")
        cls.panel.groups.add(Group.objects.create(name=PANEL))
        cls.student = users.objects.create_user("student")
        cls.admin = users.objects.create_superuser("admin", password="test-only")
        cls.webm = media_sample()

    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        patch = override_settings(EG_MEDIA_ROOT=Path(self.temp.name))
        patch.enable()
        self.addCleanup(patch.disable)

    def start(self, *, attempt=10, student="a"*64, consent=True, secret="test-integration-credential"):
        return self.client.post("/internal/moodle/start/", {
            "attemptId": attempt, "studentRef": student, "cmid": 6, "quizId": 2, "consent": consent,
        }, content_type="application/json", headers={"Authorization": f"Bearer {secret}"})

    def consent(self, **kwargs):
        result = self.start(**kwargs)
        self.assertEqual(result.status_code, 200, result.content)
        return result.json()

    def upload(self, data, *, start=0, key=None, content=None, token=None):
        return self.client.post(data["segmentUrl"], {
            "key": key or str(uuid4()), "startMs": start, "endMs": start + 1000, "deviceAtMs": 0,
            "clip": SimpleUploadedFile("test.webm", self.webm if content is None else content),
        }, headers={"Authorization": "Bearer " + (token or data["token"])})

    def test_consent_identity_and_credentials(self):
        self.assertEqual(self.start(secret="wrong").status_code, 403)
        self.assertEqual(self.consent(consent=False)["state"], "declined")
        self.assertEqual(Session.objects.get().segments.count(), 0)
        one = self.consent()
        self.assertEqual(self.consent()["sessionId"], one["sessionId"])
        self.assertEqual(self.start(student="b"*64).status_code, 400)
        two = self.consent(attempt=11, student="b"*64)
        self.assertNotEqual(one["sessionId"], two["sessionId"])
        self.assertEqual(self.upload(two, token=one["token"]).status_code, 403)
        denied = self.client.get(two["statusUrl"], headers={"Authorization": "Bearer invalid"})
        self.assertEqual(denied.status_code, 403)

    def test_upload_idempotency_integrity_and_overlap(self):
        session = self.consent()
        key = str(uuid4())
        first = self.upload(session, key=key)
        self.assertEqual(first.status_code, 201, first.content)
        duplicate = self.upload(session, key=key)
        self.assertEqual(duplicate.status_code, 200)
        self.assertEqual(first.json(), duplicate.json())
        self.assertEqual(self.upload(session, key=key, start=150).status_code, 409)
        self.assertEqual(self.upload(session, start=450).status_code, 409)
        self.assertEqual(self.upload(session, start=100000).status_code, 422)
        self.assertEqual(self.upload(session, start=1000, content=media_sample(dual=False)).status_code, 422)
        self.assertEqual(self.upload(session, start=1000, content=b"a"*100).status_code, 400)
        self.assertEqual(len(list(Path(self.temp.name).rglob("*.webm"))), 1)

    def test_end_gap_and_retry(self):
        info = self.consent()
        now = timezone.now().replace(microsecond=0)
        Session.objects.update(started_at=now - timedelta(seconds=8))
        self.assertEqual(self.upload(info, start=5000).status_code, 201)
        for _ in range(2):
            response = self.client.post("/internal/moodle/end/", {"attemptId": 10, "endedAt": int(now.timestamp())},
                    content_type="application/json", headers={"Authorization": "Bearer test-integration-credential"})
            self.assertEqual(response.status_code, 200)
        session = Session.objects.get()
        later = timezone.now() + timedelta(seconds=10)
        maintain(later)
        session.refresh_from_db()
        self.assertEqual(session.state, Session.State.INCOMPLETE)
        expected, covered, gaps = coverage(session, list(session.segments.all()))
        self.assertEqual(expected, 8000)
        self.assertGreater(covered, 900)
        self.assertEqual(gaps[0], (0, 5000))
        self.assertEqual(self.upload(info, start=6000).status_code, 409)

    def test_review_range_and_saved_revision_panel(self):
        info = self.consent()
        segment_id = self.upload(info).json()["id"]
        session = Session.objects.get()
        page = reverse("review_detail", args=[session.pk])
        clip = reverse("media", args=[segment_id])
        self.assertEqual(self.client.get(clip).status_code, 302)
        self.client.force_login(self.student)
        self.assertEqual(self.client.get(clip).status_code, 403)
        self.client.force_login(self.reviewer)
        self.assertEqual(self.client.get(clip).status_code, 404)
        self.assertEqual(self.client.get(page).status_code, 404)
        Assignment.objects.create(session=session, user=self.reviewer)
        self.assertEqual(self.client.get(page).status_code, 200)
        response = self.client.get(clip, headers={"Range": "bytes=10-39"})
        self.assertEqual(response.status_code, 206)
        self.assertEqual(b"".join(response.streaming_content), self.webm[10:40])
        self.assertEqual(self.client.get(clip, headers={"Range": "bytes=999999-"}).status_code, 416)
        self.assertEqual(self.client.post(page, {"decision": "comment", "note": "wrong role"}).status_code, 403)
        self.assertEqual(self.client.post(page, {"decision": "explained", "note": "first"}).status_code, 302)
        first = session.entries.get()
        self.assertEqual(self.client.post(page, {"decision": "follow_up", "note": "revision", "revision": first.pk}).status_code, 302)
        self.assertEqual(session.entries.get(supersedes=first).note, "revision")
        Assignment.objects.create(session=session, user=self.panel)
        self.client.force_login(self.panel)
        self.assertEqual(self.client.post(page, {"decision": "explained", "note": "wrong role"}).status_code, 403)
        self.assertEqual(self.client.post(page, {"decision": "comment", "note": "panel note"}).status_code, 302)
        self.assertContains(self.client.get(page), "panel note")
        self.assertEqual(ReviewEntry.objects.count(), 3)

    def test_analysis_haar_replay_and_expiry(self):
        info = self.consent()
        self.assertEqual(self.upload(info).status_code, 201)
        self.exam.no_face_ms = 500
        self.exam.save()
        session = Session.objects.select_related("exam").get()
        session.state = Session.State.COMPLETE
        session.save()
        job = create_job(session, "haar")
        analyze(claim())
        job.refresh_from_db()
        self.assertEqual(job.state, AnalysisJob.State.DONE, job.error)
        self.assertTrue(job.flags.filter(kind="NO_FACE").exists())
        self.assertFalse(job.observations.filter(kind="VOICE_ACTIVITY").exists())
        self.assertIn("opencv", job.versions)
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(reverse("review_detail", args=[session.pk])), "NO_FACE", count=0)
        self.assertContains(self.client.get(reverse("review_detail", args=[session.pk])), "达到")
        Session.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
        maintain(timezone.now())
        self.assertFalse(Session.objects.exists())
        self.assertFalse(AnalysisJob.objects.exists())
        self.assertFalse(list(Path(self.temp.name).rglob("*.webm")))
        self.assertEqual(list(Audit.objects.values_list("action", flat=True)), ["purged"])

    @override_settings(EG_ENABLE_STANDALONE=True)
    def test_demo_csrf_and_repeat_after_submit(self):
        demo = Client(enforce_csrf_checks=True)
        self.assertEqual(demo.get("/demo/").status_code, 200)
        token = demo.cookies["csrftoken"].value
        self.assertEqual(demo.post("/demo/session/", {"consent": "1"}).status_code, 403)
        response = demo.post("/demo/session/", {"consent": "1", "csrfmiddlewaretoken": token})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(demo.post("/demo/end/", {"csrfmiddlewaretoken": token}).status_code, 200)
        demo.get("/demo/")
        again = demo.post("/demo/session/", {"consent": "1", "csrfmiddlewaretoken": token})
        self.assertNotEqual(again.json()["sessionId"], response.json()["sessionId"])

    def test_interval_scoring_uses_each_prediction_once(self):
        score_result = score([(20000, 25000)], [(21000, 26000), (22000, 25000)])
        self.assertEqual(score_result, {"tp": 1, "fp": 1, "fn": 0, "precision": 0.5, "recall": 1})
