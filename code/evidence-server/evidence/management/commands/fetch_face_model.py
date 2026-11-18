import hashlib
import subprocess
from tempfile import TemporaryDirectory
from urllib.error import URLError
from urllib.request import urlopen

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

MODEL_URL = ("https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/"
             "float16/1/blaze_face_short_range.tflite")
MODEL_SHA256 = "b4578f35940bf5a1a655214a1cce5cab13eba73c1297cd78e1a04c2380b0152f"
HAAR_TAG = "4.13.0"
HAAR_FILE = "data/haarcascades/haarcascade_frontalface_default.xml"
HAAR_SHA256 = "0f7d4527844eb514d4a4948e822da90fbb16a34a0bbbbc6adc6498747a5aafb0"


def download(url):
    with urlopen(url, timeout=30) as response:
        return response.read(1024 * 1024 + 1)


def haar_asset():
    try:
        return download(f"https://raw.githubusercontent.com/opencv/opencv/{HAAR_TAG}/{HAAR_FILE}")
    except (URLError, TimeoutError):
        # A filtered checkout also works on hosts where raw.githubusercontent.com is unreachable.
        with TemporaryDirectory(prefix="eg-opencv-") as checkout:
            subprocess.run(
                ["git", "clone", "--quiet", "--filter=blob:none", "--no-checkout", "--depth", "1",
                 "--branch", HAAR_TAG, "https://github.com/opencv/opencv.git", checkout],
                check=True, timeout=75,
            )
            return subprocess.check_output(["git", "-C", checkout, "show", f"HEAD:{HAAR_FILE}"], timeout=60)


def save_model(path, expected, fetch):
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        content = fetch()
        if hashlib.sha256(content).hexdigest() != expected:
            raise CommandError(f"Unexpected checksum for {path.name}.")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)


class Command(BaseCommand):
    help = "Fetch and verify the official MediaPipe and OpenCV face detector models."

    def handle(self, **options):
        try:
            save_model(settings.EG_FACE_MODEL, MODEL_SHA256, lambda: download(MODEL_URL))
            save_model(settings.EG_HAAR_MODEL, HAAR_SHA256, haar_asset)
        except (OSError, subprocess.SubprocessError) as exc:
            raise CommandError(f"Could not fetch detector models: {exc}") from exc
        self.stdout.write(f"{settings.EG_FACE_MODEL.name}: {MODEL_SHA256}")
        self.stdout.write(f"{settings.EG_HAAR_MODEL.name}: {HAAR_SHA256}")
