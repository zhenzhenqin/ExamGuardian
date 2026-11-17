"""Run against a loopback Django instance using synthetic Chromium media devices."""
import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def run(args):
    import django

    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "exam_guardian.settings")
    django.setup()

    from django.contrib.auth import get_user_model
    from django.contrib.auth.models import Group
    from django.utils import timezone

    from evidence.models import PANEL, REVIEWER, Assignment, ReviewEntry, Session
    from evidence.services import coverage, finalize

    users = get_user_model()
    secret = os.urandom(24).hex()
    names = ["review-" + secret[:6], "panel-" + secret[:6], "other-" + secret[:6]]
    reviewer, panel, other = [users.objects.create_user(name, password=secret) for name in names]
    for user, role in [(reviewer, REVIEWER), (panel, PANEL), (other, REVIEWER)]:
        user.groups.add(Group.objects.get_or_create(name=role)[0])
    with ThreadPoolExecutor(max_workers=1) as database, sync_playwright() as playwright:
        def orm(function, *values):
            return database.submit(function, *values).result()

        browser = playwright.chromium.launch(
            executable_path=args.chromium,
            args=["--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream",
                  "--disable-background-timer-throttling", "--autoplay-policy=no-user-gesture-required"],
        )
        context = browser.new_context(permissions=["camera", "microphone"])
        if not args.native_fake:
            context.add_init_script(path=str(Path(__file__).with_name("synthetic_devices.js")))
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        saved = []

        def capture_response(response):
            if "/eg-ingest/" in response.url and response.url.endswith("/segments/") and response.ok:
                saved.append(response.status)

        page.on("response", capture_response)
        page.goto(f"{args.base}/demo/")
        attempt = page.locator("[data-eg-capture]").get_attribute("data-attempt")
        page.locator("[data-eg-start]").click()
        expect(page.locator("[data-eg-preview]")).to_be_visible(timeout=15000)
        page.wait_for_function("""() => {
            const stream = document.querySelector('[data-eg-preview]').srcObject;
            return stream?.getAudioTracks().length === 1 && stream?.getVideoTracks().length === 1;
        }""")
        then = time.monotonic()
        offline_done = False
        next_report = 60
        while (passed := time.monotonic() - then) < args.seconds:
            if args.disrupt and passed >= 6 and not offline_done:
                offline_done = True
                context.set_offline(True)
                page.wait_for_timeout(6200)
                context.set_offline(False)
                page.wait_for_timeout(1800)
                page.get_by_text("下一页", exact=True).click()
                expect(page.locator("[data-eg-preview]")).to_be_visible(timeout=15000)
                assert page.locator("[data-eg-capture]").get_attribute("data-attempt") == attempt
            if passed >= next_report:
                print(f"{next_report}s elapsed, {len(saved)} confirmed clips", flush=True)
                next_report += 60
            page.wait_for_timeout(300)
        page.locator("[data-eg-stop]").click()
        expect(page.locator("[data-eg-status]")).to_contain_text("已确认", timeout=15000)
        page.wait_for_timeout(120)
        page.get_by_role("button", name="交卷").click()
        expect(page.get_by_role("heading", name="练习已提交")).to_be_visible()
        def saved_evidence():
            session = Session.objects.get(source_site="standalone", attempt=attempt)
            assert session.state == Session.State.CLOSING
            finalize(session.pk, now=session.close_after)
            session.refresh_from_db()
            segments = list(session.segments.all())
            codes = set(session.events.values_list("code", flat=True))
            Assignment.objects.create(session=session, user=reviewer)
            Assignment.objects.create(session=session, user=panel)
            return session, segments, codes

        session, segments, codes = orm(saved_evidence)
        assert len(segments) > 1 and len(saved) >= 1, (len(segments), errors)
        duration, covered, gaps = coverage(session, segments)
        if args.seconds >= 600 and not args.disrupt:
            assert duration >= 600000, duration
        if args.disrupt:
            assert {"network_lost", "network_restored"} <= codes, codes

        def login(user):
            desk = browser.new_context()
            screen = desk.new_page()
            screen.goto(f"{args.base}/login/")
            screen.locator("#id_username").fill(user.username)
            screen.locator("#id_password").fill(secret)
            screen.get_by_role("button", name="登录", exact=True).click()
            expect(screen.get_by_role("heading", name="证据工作台")).to_be_visible()
            return screen

        screen = login(reviewer)
        screen.goto(f"{args.base}/review/{session.pk}/")
        video = screen.locator("[data-replay]")
        expect(video).to_be_visible()
        screen.wait_for_function("document.querySelector('[data-replay]').readyState >= 1")
        response = screen.request.get(f"{args.base}/review/media/{segments[0].pk}/", headers={"Range": "bytes=0-31"})
        assert response.status == 206 and len(response.body()) == 32, response.status
        screen.locator("[data-play]").nth(1).click()
        expect(screen.locator("[data-replay-status]")).to_contain_text(str(segments[1].pk))
        screen.locator("#note").fill("自动化验收复核意见")
        screen.get_by_role("button", name="保存意见").click()
        expect(screen.get_by_text("自动化验收复核意见", exact=True)).to_be_visible()
        screen.get_by_role("button", name="新建修订").click()
        screen.locator("#note").fill("自动化验收复核意见修订")
        screen.get_by_role("button", name="保存意见").click()
        assert orm(lambda: ReviewEntry.objects.filter(session=session, supersedes__isnull=False).exists())
        panel_screen = login(panel)
        panel_screen.goto(f"{args.base}/review/{session.pk}/")
        panel_screen.locator("#note").fill("自动化验收评审评论")
        panel_screen.get_by_role("button", name="保存意见").click()
        expect(panel_screen.get_by_text("自动化验收评审评论", exact=True)).to_be_visible()
        other_screen = login(other)
        assert other_screen.request.get(f"{args.base}/review/media/{segments[0].pk}/").status == 404
        assert not errors, errors
        report = {
            "source": "standalone, Chromium native fake devices" if args.native_fake else
                      "standalone, test-only canvas and Web Audio tracks",
            "measuredAt": timezone.now().isoformat(), "browser": browser.version,
            "segments": len(segments), "durationMs": duration, "dualTrackCoverageMs": covered,
            "coveragePct": round(covered / duration * 100, 3), "maxGapMs": max((b-a for a, b in gaps), default=0),
            "fileBytes": sum(item.size for item in segments), "reviewedAndRevised": True,
            "rangePlayback": True, "unassignedAccessDenied": True, "networkAndPageChange": args.disrupt,
            "state": session.state, "sessionId": str(session.pk),
        }
        if args.output:
            Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False), flush=True)
        if args.seconds >= 600 and not args.disrupt:
            assert covered / duration >= 0.99, (covered, duration, sorted(gaps, key=lambda gap: gap[1] - gap[0])[-5:])
        browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8090")
    parser.add_argument("--seconds", type=int, default=18)
    parser.add_argument("--chromium")
    parser.add_argument("--disrupt", action="store_true")
    parser.add_argument("--native-fake", action="store_true")
    parser.add_argument("--output")
    run(parser.parse_args())
