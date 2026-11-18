"""Verify the original upload, teacher records and media paths on a local fixture."""
import argparse
import hashlib
import json
import time
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

from playwright.sync_api import expect, sync_playwright

from moodle_browser_acceptance import login, start_attempt, submit


def run(args):
    site = urlparse(args.base)
    if site.scheme != "http" or site.hostname not in ("localhost", "127.0.0.1"):
        raise ValueError("Run this test only on a loopback Moodle fixture.")
    fixture = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
    cmid = fixture["cmid"]
    clip = Path(args.clip).read_bytes()
    second_clip = Path(args.second_clip).read_bytes()
    assert clip != second_clip
    prefix = f"{args.base}/local/examguardianmedia"
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=args.chromium)
        a = login(browser, args.base, fixture["students"][0])
        b = login(browser, args.base, fixture["students"][1])
        teacher = login(browser, args.base, fixture["teacher"])
        start_attempt(a, args.base, cmid)
        start_attempt(b, args.base, cmid)
        marker = a.locator("#exam-guardian-media")
        expect(marker).to_be_visible()
        attempt = marker.get_attribute("data-attempt")
        sesskey = marker.get_attribute("data-sesskey")
        b_key = b.locator("#exam-guardian-media").get_attribute("data-sesskey")
        fields = {"attempt": attempt, "sesskey": sesskey, "capturems": int(time.time() * 1000),
                  "durationms": 4000, "clipkey": uuid4().hex[:24]}

        def upload(page, contents=clip, **changes):
            return page.request.post(prefix + "/upload.php", multipart={
                **(fields | changes), "clip": {"name": "synthetic.webm", "mimeType": "video/webm", "buffer": contents},
            })

        assert a.request.get(prefix + "/upload.php").status == 405
        assert a.request.post(prefix + "/upload.php", form={"attempt": attempt}).status == 403
        assert upload(a, sesskey="invalid").status == 403
        assert upload(b, sesskey=b_key).status == 403
        assert upload(a, clipkey="invalid").status == 400
        assert upload(a, contents=b"not a webm file" * 10).status == 400
        accepted = upload(a)
        assert accepted.status == 201, accepted.status
        clip_id = accepted.json()["id"]
        replay = upload(a)
        assert replay.status == 200 and replay.json()["id"] == clip_id
        assert upload(a, contents=second_clip).status == 409
        for index in range(9):
            retry = upload(a, clipkey=uuid4().hex[:24])
            assert retry.status == 201, (index, retry.status)
        assert upload(a, clipkey=uuid4().hex[:24]).status == 409
        index_url = f"{prefix}/index.php?cmid={cmid}&attempt={attempt}"
        clip_url = f"{prefix}/clip.php?id={clip_id}"
        assert teacher.request.post(index_url).status == 405
        assert teacher.request.post(clip_url).status == 405
        response = teacher.request.get(index_url)
        assert response.ok and f"EG-{clip_id}" in response.text()
        assert hashlib.sha256(clip).hexdigest() in response.text()
        empty = teacher.request.get(f"{prefix}/index.php?cmid={cmid}&attempt=2147483647")
        assert empty.ok and "暂无音视频片段" in empty.text()
        playback = teacher.request.get(clip_url)
        assert playback.ok and playback.headers["content-type"].startswith("video/webm")
        assert playback.body() == clip
        part = teacher.request.get(clip_url, headers={"Range": "bytes=0-31"})
        assert part.status == 206 and part.body() == clip[:32], part.status
        assert teacher.request.get(prefix + "/clip.php?id=2147483647").status == 404
        for denied_url in (index_url, clip_url):
            denied = b.request.get(denied_url, max_redirects=0)
            assert denied.status in (302, 303, 403, 404), denied.status
        submit(a)
        assert upload(a, clipkey=uuid4().hex[:24]).status == 409
        submit(b)
        report = {"upload": "pass", "index": "pass", "playback": "pass", "range": 206,
                  "studentDenied": True, "uploadLimit": 10, "finished": True}
        print(json.dumps(report), flush=True)
        browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://localhost:8081")
    parser.add_argument("--chromium")
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--clip", required=True)
    parser.add_argument("--second-clip", required=True)
    run(parser.parse_args())
