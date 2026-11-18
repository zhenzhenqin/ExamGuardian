"""Verify and capture the existing loopback Moodle fixture's recorded attempts."""
import argparse
import json
import os
import secrets
import sys
from pathlib import Path

import django
from playwright.sync_api import expect, sync_playwright

SERVER = Path(__file__).resolve().parents[4] / "code" / "evidence-server"
OUTPUT = Path(os.getenv("EG_QA_DIR", SERVER / "var" / "acceptance-repro")).resolve()
sys.path[:0] = [str(SERVER), str(SERVER / "tools")]
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "exam_guardian.settings")
django.setup()

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import connection
from evidence.management.commands.evidence_worker import analyze
from evidence.models import REVIEWER, AnalysisJob, Assignment, Session
from evidence.services import coverage, create_job, finalize
from moodle_browser_acceptance import login as moodle_login

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--chromium")
parser.add_argument("--fixture", type=Path, default=SERVER / "var" / "moodle-fixture.json")
parser.add_argument("--teacher-fixture", type=Path,
                    default=SERVER / "var" / "moodle-legacy-interfaces.json")
args = parser.parse_args()
fixture = json.loads(args.fixture.read_text(encoding="utf-8-sig"))
(OUTPUT / "screenshots").mkdir(parents=True, exist_ok=True)
attempts = json.loads((OUTPUT / "moodle.json").read_text(encoding="utf-8"))["finished"]
moodle = "http://localhost:8081"
evidence = "http://127.0.0.1:8091"

def shot(page, name):
    page.screenshot(path=str(OUTPUT / "screenshots" / f"{name}.png"), full_page=True)

assert connection.vendor == "mysql", connection.vendor
sessions = [Session.objects.get(exam__cmid=fixture["cmid"], attempt=attempt) for attempt in attempts]
metrics = []
for i, session in enumerate(sessions):
    finalize(session.pk)
    session.refresh_from_db()
    segments = list(session.segments.all())
    if i < 2:
        assert session.state in (Session.State.COMPLETE, Session.State.INCOMPLETE)
        assert len(segments) >= 1
    else:
        assert session.state == Session.State.DECLINED and not segments
    end, covered, gaps = coverage(session, segments)
    metrics.append({
        "attempt": session.attempt, "state": session.state, "segments": len(segments),
        "durationMs": end, "coveragePct": round(100 * covered / end, 3) if end else None,
        "maxGapMs": max((b - a for a, b in gaps), default=0),
    })

selected = sessions[0]
analysis = []
for detector in ("mediapipe", "haar"):
    job = selected.jobs.filter(vision=detector, state=AnalysisJob.State.DONE).first()
    if job is None:
        job = create_job(selected, detector)
        AnalysisJob.objects.filter(pk=job.pk).update(state=AnalysisJob.State.RUNNING)
        analyze(job)
    job.refresh_from_db()
    analysis.append({
        "id": job.pk, "detector": detector, "state": job.state,
        "observations": job.observations.count(), "flags": job.flags.count(),
        "priority": job.priority, "versions": job.versions, "error": job.error,
    })
password = secrets.token_urlsafe(24)
user = get_user_model().objects.create_user(username="qa-review-" + secrets.token_hex(4), password=password)
user.groups.add(Group.objects.get(name=REVIEWER))
for session in sessions:
    Assignment.objects.create(session=session, user=user)
connection.close()

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=args.chromium)
    page = browser.new_page()
    assert page.goto(f"{evidence}/health/").ok
    page.goto(f"{evidence}/login/")
    page.locator("#id_username").fill(user.username)
    page.locator("#id_password").fill(password)
    page.get_by_role("button", name="登录", exact=True).click()
    expect(page.get_by_role("heading", name="证据工作台")).to_be_visible()
    shot(page, "moodle-07-reviewer-workbench")
    detail = f"{evidence}/review/{selected.pk}/"
    page.goto(detail)
    link = page.get_by_role("link", name="在 Moodle 查看答卷")
    expect(link).to_be_visible()
    assert f"attempt={selected.attempt}" in link.get_attribute("href")
    page.wait_for_function("document.querySelector('[data-replay]').readyState >= 1")
    media = page.locator("[data-play]").first.get_attribute("data-play")
    response = page.request.get(f"{evidence}{media}", headers={"Range": "bytes=0-31"})
    assert response.status == 206 and len(response.body()) == 32
    page.locator("[data-play]").first.click()
    page.wait_for_function("document.querySelector('[data-replay]').currentTime > 0.1")
    shot(page, "moodle-08-authorized-playback")
    note = f"本机验收：已核对 Moodle 作答与合成双轨片段（{user.username}）。"
    page.locator("#note").fill(note)
    page.get_by_role("button", name="保存意见").click()
    expect(page.get_by_text(note, exact=True)).to_be_visible()
    for result in analysis:
        page.goto(f"{detail}?job={result['id']}")
        shot(page, f"moodle-09-analysis-{result['detector']}")
    page.goto(f"{evidence}/review/{sessions[2].pk}/")
    expect(page.get_by_text("本次作答没有可播放的素材。")).to_be_visible()
    shot(page, "moodle-10-review-declined")

    teacher_credentials = fixture.get("teacher")
    if teacher_credentials is None:
        teacher_credentials = json.loads(args.teacher_fixture.read_text(encoding="utf-8-sig"))["teacher"]
    teacher = moodle_login(browser, moodle, teacher_credentials)
    teacher.goto(f"{moodle}/mod/quiz/review.php?attempt={selected.attempt}")
    expect(teacher.locator(".que").first).to_be_visible()
    shot(teacher, "moodle-11-teacher-answer-sheet")

    student = moodle_login(browser, moodle, fixture["students"][0])
    student.goto(f"{moodle}/mod/quiz/view.php?id=6")
    expect(student.get_by_text("Start Safe Exam Browser", exact=True)).to_be_visible()
    assert not student.locator(".quizstartbuttondiv [type=submit]").count()
    shot(student, "seb-01-moodle-launch-gate")
    seb = browser.new_page()
    seb_home = seb.goto("http://127.0.0.1:8080/gui", wait_until="domcontentloaded")
    assert seb_home.ok
    seb.wait_for_timeout(1400)
    shot(seb, "seb-02-server-entry")
    browser.close()

report = {
    "sessions": metrics, "analysis": analysis, "rangeStatus": response.status,
    "rangeBytes": 32, "moodleAnswerLink": True, "reviewSaved": True,
    "sebServerHttpStatus": seb_home.status, "normalBrowserQuizGate": True,
}
(OUTPUT / "moodle-evidence.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, ensure_ascii=False), flush=True)
assert all(result["state"] == "done" for result in analysis), analysis
