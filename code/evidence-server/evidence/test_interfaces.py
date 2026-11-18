"""Request-level checks for the custom routes and the administration workflow."""
import json
from datetime import timedelta
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from uuid import uuid4

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command, CommandError
from django.db import OperationalError
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import PANEL, REVIEWER, AnalysisJob, Assignment, Audit, CaptureEvent, Exam, Flag, Session
from .services import finalize
from .tests import media_sample


@override_settings(
    EG_ENABLE_STANDALONE=True,
    EG_MOODLE_SITE="test-moodle",
    EG_MOODLE_SECRET="local-interface-tests",
    EG_MOODLE_REVIEW_BASE="http://localhost:8081",
)
class InterfaceMatrix(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.exam = Exam.objects.create(name="接口验收测验", source_site="test-moodle", cmid=6,
                                       quiz_id=2, location="Test lab")
        users = get_user_model()
        cls.admin = users.objects.create_superuser("matrix-admin", password="matrix-admin-test-only")
        cls.reviewer = users.objects.create_user("matrix-reviewer", password="matrix-reviewer-test-only")
        cls.reviewer.groups.add(Group.objects.create(name=REVIEWER))
        cls.panel = users.objects.create_user("matrix-panel")
        cls.panel.groups.add(Group.objects.create(name=PANEL))
        cls.student = users.objects.create_user("matrix-student")
        cls.webm = media_sample()

    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        media = override_settings(EG_MEDIA_ROOT=Path(directory.name))
        media.enable()
        self.addCleanup(media.disable)

    @staticmethod
    def service_headers():
        return {"Authorization": "Bearer local-interface-tests"}

    def moodle_start(self, **updates):
        body = {"attemptId": 10, "studentRef": "a"*64, "cmid": 6, "quizId": 2, "consent": True}
        body.update(updates)
        return self.client.post("/internal/moodle/start/", body, content_type="application/json",
                                headers=self.service_headers())

    def session(self, **updates):
        response = self.moodle_start(**updates)
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()

    @staticmethod
    def grant(info):
        return {"Authorization": "Bearer " + info["token"]}

    def media_segment(self, info, **updates):
        fields = {"key": str(uuid4()), "startMs": 0, "endMs": 1000, "deviceAtMs": 0,
                  "clip": SimpleUploadedFile("sample.webm", self.webm)}
        fields.update(updates)
        return self.client.post(info["segmentUrl"], fields, headers=self.grant(info))

    def test_root_health_and_methods(self):
        self.assertRedirects(self.client.get("/"), "/demo/", fetch_redirect_response=False)
        self.assertEqual(self.client.post("/").status_code, 405)
        with override_settings(EG_ENABLE_STANDALONE=False):
            self.assertRedirects(self.client.get("/"), "/review/", fetch_redirect_response=False)
        health = self.client.get("/health/")
        self.assertEqual(health.json(), {"status": "ok"})
        self.assertEqual(health.headers["Cache-Control"], "no-store")
        self.assertEqual(self.client.post("/health/").status_code, 405)

    def test_login_and_logout_csrf_session(self):
        browser = Client(enforce_csrf_checks=True)
        login = browser.get("/login/")
        self.assertContains(login, "登录")
        self.assertEqual(browser.get("/review/").status_code, 302)
        fields = {"username": self.reviewer.username, "password": "wrong-pass"}
        self.assertEqual(browser.post("/login/", fields).status_code, 403)
        fields["csrfmiddlewaretoken"] = browser.cookies["csrftoken"].value
        self.assertEqual(browser.post("/login/", fields).status_code, 200)
        self.assertNotIn("_auth_user_id", browser.session)
        fields["password"] = "matrix-reviewer-test-only"
        self.assertRedirects(browser.post("/login/", fields), "/review/", fetch_redirect_response=False)
        self.assertEqual(browser.get("/review/").status_code, 200)
        self.assertEqual(browser.get("/logout/").status_code, 405)
        self.assertEqual(browser.post("/logout/").status_code, 403)
        self.assertRedirects(browser.post("/logout/", {"csrfmiddlewaretoken": browser.cookies["csrftoken"].value}),
                             "/login/", fetch_redirect_response=False)
        self.assertEqual(browser.get("/review/").status_code, 302)

    def test_demo_page_script_consent_and_exit(self):
        self.assertEqual(self.client.post("/demo/").status_code, 405)
        self.assertEqual(self.client.get("/demo/session/").status_code, 405)
        self.assertEqual(self.client.get("/demo/end/").status_code, 405)
        self.assertEqual(self.client.post("/demo/session/", {"consent": "1"}).status_code, 403)
        self.assertEqual(self.client.post("/demo/end/").status_code, 403)
        self.assertContains(self.client.get("/demo/"), "独立采集练习")
        old_attempt = self.client.session["attempt"]
        self.assertContains(self.client.get("/demo/?page=2"), old_attempt)
        script = self.client.get("/demo/capture.js")
        self.assertEqual(script.headers["Content-Type"], "text/javascript")
        self.assertIn(b"MediaRecorder", b"".join(script.streaming_content))
        self.assertEqual(self.client.post("/demo/capture.js").status_code, 405)
        self.assertEqual(self.client.post("/demo/session/", {"consent": "invalid"}).status_code, 400)
        refused = self.client.post("/demo/session/", {"consent": "0"}).json()
        self.assertEqual(refused["state"], "declined")
        self.assertNotIn("token", refused)
        self.assertContains(self.client.post("/demo/end/"), "练习已提交")
        self.assertNotIn("attempt", self.client.session)
        self.assertContains(self.client.get("/demo/"), "独立采集练习")
        self.assertNotEqual(old_attempt, self.client.session["attempt"])
        Exam.objects.filter(source_site="standalone").update(enabled=False)
        self.assertEqual(self.client.post("/demo/session/", {"consent": "1"}).status_code, 403)
        with override_settings(EG_ENABLE_STANDALONE=False):
            for method, url in [(self.client.get, "/demo/"), (self.client.get, "/demo/capture.js"),
                                (self.client.post, "/demo/session/"), (self.client.post, "/demo/end/")]:
                with self.subTest(url=url):
                    self.assertEqual(method(url).status_code, 404)

    def test_integration_requests_and_disabled_exam(self):
        for url in ("/internal/moodle/start/", "/internal/moodle/end/"):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 405)
                self.assertEqual(self.client.post(url, {}, content_type="application/json").status_code, 403)
                self.assertEqual(self.client.post(url, b"{", content_type="application/json",
                                                  headers=self.service_headers()).status_code, 400)
                self.assertEqual(self.client.post(url, [], content_type="application/json",
                                                  headers=self.service_headers()).status_code, 400)
        self.assertEqual(self.moodle_start(quizId=3).status_code, 403)
        self.assertEqual(self.moodle_start(consent=1).status_code, 400)
        self.assertEqual(self.moodle_start(studentRef="invalid").status_code, 400)
        self.assertEqual(self.moodle_start(attemptId=-1).status_code, 400)
        self.assertEqual(Session.objects.count(), 0)
        Exam.objects.filter(pk=self.exam.pk).update(enabled=False)
        self.assertEqual(self.moodle_start().status_code, 403)

    def test_status_ready_and_service_unavailable(self):
        info = self.session()
        url = info["statusUrl"]
        self.assertEqual(self.client.post(url).status_code, 405)
        self.assertEqual(self.client.get(url).status_code, 403)
        valid = self.client.get(url, headers=self.grant(info))
        self.assertEqual(valid.status_code, 200)
        self.assertEqual(valid.json()["segments"], 0)
        response = self.media_segment(info)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.client.get(url, headers=self.grant(info)).json()["segments"], 1)
        with patch("evidence.api.Session.objects.filter", side_effect=OperationalError("unavailable")):
            self.assertEqual(self.client.get(url, headers=self.grant(info)).status_code, 503)
        with patch("django.core.signing.time.time", return_value=timezone.now().timestamp() + 24 * 3600):
            self.assertEqual(self.client.get(url, headers=self.grant(info)).status_code, 403)
        Session.objects.filter(pk=info["sessionId"]).update(state=Session.State.PURGING)
        self.assertEqual(self.client.get(url, headers=self.grant(info)).status_code, 404)

    def test_events_method_payload_replay_and_deadline(self):
        info = self.session()
        headers = self.grant(info)
        url = info["eventUrl"]
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(self.client.post(url, {}, content_type="application/json").status_code, 403)
        payload = {"key": str(uuid4()), "code": "network_lost", "atMs": 0}
        for updates in ({"key": "wrong"}, {"key": []}, {"code": "wrong"}, {"code": []}, {"atMs": -1}, {"atMs": 900000}):
            with self.subTest(updates=updates):
                self.assertEqual(self.client.post(url, payload | updates, content_type="application/json",
                                                  headers=headers).status_code, 400)
        for _ in range(2):
            self.assertEqual(self.client.post(url, payload, content_type="application/json", headers=headers).status_code, 200)
        session = Session.objects.get(pk=info["sessionId"])
        self.assertEqual(session.events.count(), 1)
        conflicting = self.client.post(url, payload | {"code": "network_restored"}, content_type="application/json",
                                       headers=headers)
        self.assertEqual(conflicting.status_code, 409)
        new_event = payload | {"key": str(uuid4()), "code": "network_restored"}
        self.assertEqual(self.client.post(url, new_event, content_type="application/json", headers=headers).status_code, 200)
        Session.objects.filter(pk=session.pk).update(state=Session.State.CLOSING,
                                                      close_after=timezone.now() - timedelta(seconds=1))
        self.assertEqual(self.client.post(url, new_event, content_type="application/json", headers=headers).status_code, 409)
        self.assertEqual(session.events.count(), 2)
        Session.objects.filter(pk=session.pk).update(state=Session.State.ACTIVE, close_after=None)
        CaptureEvent.objects.bulk_create([
            CaptureEvent(session=session, key=uuid4(), code="client_ready", at_ms=0) for _ in range(298)
        ])
        self.assertEqual(self.client.post(url, payload, content_type="application/json", headers=headers).status_code, 200)
        too_many = self.client.post(url, payload | {"key": str(uuid4())}, content_type="application/json", headers=headers)
        self.assertEqual(too_many.status_code, 413)

    def test_segment_method_size_and_session_quota(self):
        info = self.session()
        url = info["segmentUrl"]
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(self.client.post(url).status_code, 403)
        self.assertEqual(self.client.post(url, headers=self.grant(info)).status_code, 400)
        for updates in ({"key": "bad"}, {"startMs": "NaN"}, {"deviceAtMs": -1}):
            with self.subTest(updates=updates):
                self.assertEqual(self.media_segment(info, **updates).status_code, 400)
        with override_settings(EG_MAX_SEGMENT_BYTES=100):
            self.assertEqual(self.media_segment(info).status_code, 413)
        with override_settings(EG_MAX_SESSION_BYTES=len(self.webm)):
            self.assertEqual(self.media_segment(info).status_code, 201)
            self.assertEqual(self.media_segment(info, startMs=1000, endMs=2000).status_code, 413)
        self.assertEqual(Session.objects.get().segments.count(), 1)

    def test_end_to_complete_and_grace_window(self):
        info = self.session()
        session = Session.objects.get()
        end = timezone.now().replace(microsecond=0)
        Session.objects.filter(pk=session.pk).update(started_at=end - timedelta(seconds=1))
        for attempt in (999, 10, 10):
            self.assertEqual(self.client.post("/internal/moodle/end/", {"attemptId": attempt, "endedAt": int(end.timestamp())},
                                              content_type="application/json", headers=self.service_headers()).status_code, 200)
        session.refresh_from_db()
        self.assertEqual(session.state, Session.State.CLOSING)
        finalize(session.pk, now=end)
        session.refresh_from_db()
        self.assertEqual(session.state, Session.State.CLOSING)
        self.assertEqual(self.media_segment(info).status_code, 201)
        finalize(session.pk, now=session.close_after)
        session.refresh_from_db()
        self.assertEqual(session.state, Session.State.COMPLETE)
        self.assertEqual(Audit.objects.filter(action=Session.State.COMPLETE, session_ref=session.pk).count(), 1)
        self.assertNotIn("token", self.session())

    def test_review_list_filters_assignment_and_priority(self):
        self.session()
        self.session(attemptId=11)
        self.session(attemptId=12)
        first = Session.objects.get(attempt="10")
        second = Session.objects.get(attempt="11")
        Assignment.objects.bulk_create([Assignment(session=first, user=self.reviewer),
                                        Assignment(session=second, user=self.reviewer)])
        AnalysisJob.objects.create(session=first, state=AnalysisJob.State.DONE, rules={}, rule_version="one", priority=10)
        AnalysisJob.objects.create(session=first, state=AnalysisJob.State.PENDING, rules={}, rule_version="two", priority=0)
        self.client.force_login(self.student)
        self.assertEqual(self.client.get("/review/").status_code, 403)
        self.client.force_login(self.reviewer)
        self.assertEqual(self.client.post("/review/").status_code, 405)
        self.assertEqual(list(self.client.get("/review/").context["sessions"]), [first, second])
        self.assertEqual(list(self.client.get("/review/?attempt=11").context["sessions"]), [second])
        self.assertEqual(list(self.client.get("/review/?attempt=12").context["sessions"]), [])

    def test_review_detail_method_note_fields_and_moodle_link(self):
        self.session()
        session = Session.objects.get()
        url = reverse("review_detail", args=[session.pk])
        Assignment.objects.create(session=session, user=self.reviewer)
        self.client.force_login(self.reviewer)
        self.assertContains(self.client.get(url), "http://localhost:8081/mod/quiz/review.php?attempt=10")
        self.assertEqual(self.client.put(url).status_code, 405)
        for note in ("  ", "a"*2001):
            self.assertEqual(self.client.post(url, {"note": note, "decision": "explained"}).status_code, 400)
        for revision in ("invalid", str(2**63), str(2**64)):
            self.assertEqual(self.client.post(url, {"note": "ok", "decision": "explained", "revision": revision}).status_code, 400)
        self.assertEqual(session.entries.count(), 0)

    def test_analysis_endpoint_permissions_tools_and_pending_deduplication(self):
        info = self.session()
        session = Session.objects.get()
        url = reverse("queue_analysis", args=[session.pk])
        self.assertEqual(self.client.post(url).status_code, 302)
        self.client.force_login(self.reviewer)
        self.assertEqual(self.client.post(url).status_code, 403)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(self.client.post(url).status_code, 404)
        self.assertEqual(self.media_segment(info).status_code, 201)
        Session.objects.update(state=Session.State.COMPLETE)
        self.assertEqual(self.client.post(url, {"vision": "unknown"}).status_code, 400)
        for _ in range(2):
            self.assertEqual(self.client.post(url, {"vision": "haar"}).status_code, 302)
        job = session.jobs.get()
        self.assertEqual((job.vision, job.state), ("haar", AnalysisJob.State.PENDING))
        self.assertEqual(Audit.objects.filter(action="queued_analysis").count(), 1)

    def test_media_full_suffix_missing_file_and_accel(self):
        info = self.session()
        clip = self.media_segment(info).json()["id"]
        session = Session.objects.get()
        url = reverse("media", args=[clip])
        Assignment.objects.create(session=session, user=self.panel)
        self.client.force_login(self.panel)
        self.assertEqual(self.client.post(url).status_code, 405)
        full = self.client.get(url)
        self.assertEqual(full.status_code, 200)
        self.assertEqual(full.headers["Content-Type"], "video/webm")
        self.assertIn("no-store", full.headers["Cache-Control"])
        self.assertEqual(b"".join(full.streaming_content), self.webm)
        suffix = self.client.get(url, headers={"Range": "bytes=-20"})
        self.assertEqual(suffix.status_code, 206)
        self.assertEqual(b"".join(suffix.streaming_content), self.webm[-20:])
        with override_settings(EG_ACCEL_MEDIA=True):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.headers["X-Accel-Redirect"].startswith("/_eg_private/"))
        path = next(settings.EG_MEDIA_ROOT.rglob("*.webm"))
        path.unlink()
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_evaluate_command_matches_labels_and_rejects_another_session(self):
        info = self.session()
        self.assertEqual(self.media_segment(info).status_code, 201)
        session = Session.objects.get()
        job = AnalysisJob.objects.create(session=session, state=AnalysisJob.State.DONE,
                                         rules={"NO_FACE": [250, 1]}, rule_version="matrix")
        Flag.objects.create(job=job, segment=session.segments.get(), kind="NO_FACE", start_ms=0, end_ms=800,
                            reason="test observation", priority=1)
        labels = settings.EG_MEDIA_ROOT / "labels.json"
        sample = {"sessionId": str(session.pk), "events": [{"kind": "NO_FACE", "startMs": 0, "endMs": 900}],
                  "normalIntervals": [[900, 1000]]}
        labels.write_text(json.dumps(sample), encoding="utf-8")
        result = StringIO()
        call_command("evaluate_evidence", job.pk, labels, stdout=result)
        report = json.loads(result.getvalue())
        self.assertEqual(report["byKind"]["未检出人脸"]["tp"], 1)
        self.assertEqual(report["normalAlertsPerMinute"], 0)
        labels.write_text(json.dumps(sample | {"sessionId": str(uuid4())}), encoding="utf-8")
        with self.assertRaises(CommandError):
            call_command("evaluate_evidence", job.pk, labels)

    def test_admin_exam_form_assignment_and_readonly_audit(self):
        self.session()
        session = Session.objects.get()
        change = reverse("admin:evidence_session_change", args=[session.pk])
        self.client.force_login(self.reviewer)
        self.assertEqual(self.client.get("/admin/").status_code, 302)
        self.client.force_login(self.admin)
        self.assertContains(self.client.get("/admin/"), "Exam")
        for name in ("admin:auth_user_changelist", "admin:auth_user_add", "admin:auth_group_add", "admin:evidence_exam_add",
                     "admin:evidence_session_changelist", "admin:evidence_audit_changelist"):
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)
        self.assertEqual(self.client.post(reverse("admin:auth_group_add"), {"name": "matrix-extra"}).status_code, 302)
        self.assertTrue(Group.objects.filter(name="matrix-extra").exists())
        self.assertEqual(self.client.post(reverse("admin:auth_user_add"), {
            "username": "matrix-new-user", "usable_password": "true",
            "password1": "sample-password!2940", "password2": "sample-password!2940",
        }).status_code, 302)
        self.assertTrue(get_user_model().objects.filter(username="matrix-new-user").exists())
        self.assertEqual(self.client.get(reverse("admin:evidence_session_add")).status_code, 403)
        audit = Audit.objects.get()
        self.assertEqual(self.client.get(reverse("admin:evidence_audit_change", args=[audit.pk])).status_code, 200)
        self.assertEqual(self.client.post(reverse("admin:evidence_audit_change", args=[audit.pk]),
                                          {"action": "changed"}).status_code, 403)
        exam = self.exam
        fields = {"name": exam.name, "source_site": exam.source_site, "cmid": exam.cmid, "quiz_id": exam.quiz_id,
                  "location": exam.location, "retention_days": 0}
        for name in ("no_face_ms", "multiple_faces_ms", "voice_ms", "no_face_weight", "multiple_faces_weight", "voice_weight"):
            fields[name] = getattr(exam, name)
        edit = reverse("admin:evidence_exam_change", args=[exam.pk])
        self.assertEqual(self.client.post(edit, fields).status_code, 200)
        self.assertEqual(self.client.post(edit, fields | {"retention_days": 21}).status_code, 302)
        exam.refresh_from_db()
        self.assertEqual(exam.retention_days, 21)
        self.assertFalse(exam.enabled)
        self.assertEqual(self.moodle_start().status_code, 403)
        inline = {"assignments-TOTAL_FORMS": 1, "assignments-INITIAL_FORMS": 0,
                  "assignments-MIN_NUM_FORMS": 0, "assignments-MAX_NUM_FORMS": 1000, "_save": "Save"}
        self.assertEqual(self.client.post(change, inline | {"assignments-0-user": self.student.pk}).status_code, 200)
        self.assertFalse(session.assignments.exists())
        self.assertEqual(self.client.post(change, inline | {"assignments-0-user": self.reviewer.pk,
                                                              "state": Session.State.COMPLETE}).status_code, 302)
        assignment = session.assignments.get(user=self.reviewer)
        session.refresh_from_db()
        self.assertEqual(session.state, Session.State.ACTIVE)
        self.assertEqual(self.client.post(change, inline | {"assignments-INITIAL_FORMS": 1, "assignments-0-id": assignment.pk,
                                                           "assignments-0-user": self.reviewer.pk,
                                                           "assignments-0-DELETE": "on"}).status_code, 302)
        self.client.force_login(self.reviewer)
        self.assertEqual(self.client.get(reverse("review_detail", args=[session.pk])).status_code, 404)
