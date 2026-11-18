"""Run the repository acceptance scripts with PNG capture at selected checkpoints."""
import os
import sys
from pathlib import Path

SERVER = Path(__file__).resolve().parents[4] / "code" / "evidence-server"
OUTPUT = Path(os.getenv("EG_QA_DIR", SERVER / "var" / "acceptance-repro")).resolve()
SHOTS = OUTPUT / "screenshots"
SHOTS.mkdir(parents=True, exist_ok=True)

def shot(page, name):
    page.screenshot(path=str(SHOTS / f"{name}.png"), full_page=True, animations="disabled")

def run_instrumented(script_name, hooks):
    script = SERVER / "tools" / script_name
    source = script.read_text(encoding="utf-8")
    for anchor, before, after in hooks:
        if source.count(anchor) != 1:
            raise SystemExit(f"Screenshot checkpoint changed in {script.name}: {anchor}")
        source = source.replace(anchor, before + anchor + after, 1)
    sys.argv[0] = str(script)
    exec(compile(source, str(script), "exec"), {
        "__name__": "__main__", "__file__": str(script), "shot": shot,
    })

def standalone(long_run):
    group = "long" if long_run else "standalone"
    run_instrumented("browser_acceptance.py", [
        ('        page.locator("[data-eg-start]").click()\n',
         f'        shot(page, "{group}-01-consent")\n', ''),
        ('        if args.pre_roll:\n',
         f'        shot(page, "{group}-02-recording")\n', ''),
        ('                assert page.locator("[data-eg-capture]").get_attribute("data-attempt") == attempt\n',
         '', '                shot(page, "standalone-03-reconnected-next-page")\n'),
        ('        page.get_by_role("button", name="交卷").click()\n',
         f'        shot(page, "{group}-04-upload-confirmed")\n', ''),
        ('        expect(page.get_by_role("heading", name="练习已提交")).to_be_visible()\n',
         '', f'        shot(page, "{group}-05-submitted")\n'),
        ('        expect(screen.locator("[data-replay-status]")).to_contain_text(str(segments[1].pk))\n',
         '', f'        shot(screen, "{group}-06-review-playback")\n'),
        ('        expect(panel_screen.get_by_text("自动化验收评审评论", exact=True)).to_be_visible()\n',
         '', f'        shot(panel_screen, "{group}-07-review-history")\n'),
    ])

def moodle():
    run_instrumented("moodle_browser_acceptance.py", [
        ('        b = start(second, args.base, fixture["cmid"])\n',
         '        shot(first, "moodle-01-consent")\n', ''),
        ('    if navigate:\n',
         '    if navigate:\n        shot(page, "moodle-02-recording-confirmed")\n', ''),
        ('        page.wait_for_timeout(6500)\n',
         '', '        shot(page, "moodle-03-recording-next-page")\n'),
        ('        finished = first.request.post(registration, form={"attempt": attempt_a, "sesskey": sesskey_a, "consent": 1})\n',
         '        shot(first, "moodle-04-submitted-with-recording")\n', ''),
        ('        submit(first)\n',
         '        shot(first, "moodle-05-declined-recording")\n',
         '        shot(first, "moodle-06-submitted-after-decline")\n'),
    ])

def legacy():
    sys.path.insert(0, str(SERVER / "tools"))
    run_instrumented("moodle_legacy_acceptance.py", [
        ('        submit(a)\n',
         '        teacher.goto(index_url)\n'
         '        shot(teacher, "legacy-01-teacher-media")\n', ''),
    ])

os.chdir(SERVER)
mode = sys.argv.pop(1) if len(sys.argv) > 1 else None
if mode == "moodle":
    moodle()
elif mode == "legacy":
    legacy()
elif mode in {"standalone", "long"}:
    standalone(mode == "long")
else:
    raise SystemExit("Use standalone, long, moodle, or legacy.")
