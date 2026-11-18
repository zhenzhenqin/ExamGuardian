"""Exercise the adapter on an ordinary-browser Moodle lab quiz."""
import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import expect, sync_playwright


def login(browser, base, student):
    context = browser.new_context()
    context.add_init_script(path=str(Path(__file__).with_name("synthetic_devices.js")))
    page = context.new_page()
    login_url = f"{base}/login/index.php"
    page.goto(login_url)
    token = page.locator("#login input[name=logintoken]").get_attribute("value")
    response = context.request.post(login_url, form={
        "username": student["username"], "password": student["password"], "logintoken": token,
    })
    if not response.ok or "Invalid login" in response.text():
        raise AssertionError("Moodle refused the local fixture login.")
    page.goto(f"{base}/my/")
    expect(page.locator(".usermenu")).to_be_visible()
    return page


def start_attempt(page, base, cmid):
    page.goto(f"{base}/mod/quiz/view.php?id={cmid}")
    page.locator(".quizstartbuttondiv [type=submit]").click()
    page.wait_for_url(re.compile(r"/mod/quiz/attempt.php"))


def start(page, base, cmid):
    start_attempt(page, base, cmid)
    panel = page.locator("[data-eg-capture]")
    expect(panel).to_be_visible()
    return panel


def submit(page):
    for _ in range(6):
        if "summary.php" in page.url:
            break
        choices = page.locator("#responseform .que input[type=radio]")
        if choices.count():
            choices.first.check()
        page.locator("#mod_quiz-next-nav").click()
    page.wait_for_url(re.compile(r"/mod/quiz/summary.php"))
    page.locator("#frm-finishattempt button").click()
    with page.expect_response(lambda response: "/mod/quiz/processattempt.php" in response.url and
                              response.request.method == "POST") as submitted:
        page.locator("[data-region=modal]:visible [data-action=save]").click()
    assert submitted.value.status in (302, 303), submitted.value.status
    page.wait_for_url(re.compile(r"/mod/quiz/(review|view)\.php"), wait_until="domcontentloaded")


def record(page, panel, *, navigate=False):
    records = []

    def response_seen(response):
        if "/eg-ingest/" in response.url and response.url.endswith("/segments/") and response.ok:
            records.append(response.status)

    page.on("response", response_seen)
    with page.expect_response(lambda resp: resp.url.endswith("/local/examguardianmedia/session.php") and resp.ok) as registered:
        panel.locator("[data-eg-start]").click()
    grant = registered.value.json()
    status_url = page.url.split("/mod/quiz/", 1)[0] + grant["statusUrl"]
    assert page.request.get(status_url).status == 403
    status_headers = {"Authorization": "Bearer " + grant["token"]}
    status = page.request.get(status_url, headers=status_headers)
    assert status.ok and status.json()["state"] == "active"
    expect(panel.locator("[data-eg-preview]")).to_be_visible(timeout=18000)
    page.wait_for_timeout(11000)
    expect(panel.locator("[data-eg-status]")).to_contain_text(re.compile(r"已确认 [1-9]"), timeout=15000)
    if navigate:
        page.locator("#responseform .que input[type=radio]").first.check()
        page.locator("#mod_quiz-next-nav").click()
        expect(panel.locator("[data-eg-preview]")).to_be_visible(timeout=15000)
        page.wait_for_timeout(6500)
    panel.locator("[data-eg-stop]").click()
    page.wait_for_timeout(1800)
    submit(page)
    page.remove_listener("response", response_seen)
    return len(records)


def run(args):
    site = urlparse(args.base)
    if site.scheme != "http" or site.hostname not in ["127.0.0.1", "localhost"]:
        raise ValueError("Run this test on a loopback Moodle fixture.")
    fixture = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=args.chromium,
            args=["--autoplay-policy=no-user-gesture-required", "--disable-background-timer-throttling"],
        )
        first = login(browser, args.base, fixture["students"][0])
        second = login(browser, args.base, fixture["students"][1])
        a = start(first, args.base, fixture["cmid"])
        b = start(second, args.base, fixture["cmid"])
        attempt_a = a.get_attribute("data-attempt")
        attempt_b = b.get_attribute("data-attempt")
        registration = f"{args.base}/local/examguardianmedia/session.php"
        public = browser.new_context()
        assert public.request.get(registration).status == 405
        assert public.request.post(registration, form={"attempt": attempt_a, "consent": 1}).status == 403
        public.close()
        assert first.request.post(registration, form={"attempt": attempt_a, "consent": 1}).status == 403
        cross = second.request.post(
            registration, form={
                "attempt": attempt_a, "sesskey": b.get_attribute("data-csrf-value"), "consent": "1",
            },
        )
        assert cross.status == 403, cross.status
        sesskey_a = a.get_attribute("data-csrf-value")
        for value in (9, "1draft", ""):
            invalid = first.request.post(registration, form={"attempt": attempt_a, "sesskey": sesskey_a, "consent": value})
            assert invalid.status == 403, (value, invalid.status)
        clips_a = record(first, a, navigate=True)
        finished = first.request.post(registration, form={"attempt": attempt_a, "sesskey": sesskey_a, "consent": 1})
        assert finished.status == 403
        print(f"Moodle attempt {attempt_a}: {clips_a} acknowledged clips, submitted.", flush=True)
        clips_b = record(second, b)
        print(f"Moodle attempt {attempt_b}: {clips_b} acknowledged clips, submitted.", flush=True)
        again = start(first, args.base, fixture["cmid"])
        attempt_again = again.get_attribute("data-attempt")
        assert len({attempt_a, attempt_b, attempt_again}) == 3
        again.locator("[data-eg-decline]").click()
        expect(again.locator("[data-eg-status]")).to_contain_text("已记录拒绝采集")
        submit(first)
        print(f"Moodle repeat attempt {attempt_again}: declined recording, submitted.", flush=True)
        report = {"source": "Moodle lab quiz via Chromium with test-only synthetic tracks",
                  "browser": browser.version, "cmid": fixture["cmid"], "quiz_id": fixture["quizId"],
                  "finished": [attempt_a, attempt_b, attempt_again], "clipAcknowledgements": [clips_a, clips_b],
                  "moodleCrossAccountDenied": True, "declinedAttempt": attempt_again,
                  "sessionMethodAnonymousCsrfAndFinishedChecked": True, "proxyStatusAuthorization": True}
        Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False), flush=True)
        browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://localhost:8081")
    parser.add_argument("--chromium")
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--output", required=True)
    run(parser.parse_args())
