import hashlib
from urllib.request import urlopen

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

MODEL_URL = ("https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/"
             "float16/1/blaze_face_short_range.tflite")
MODEL_SHA256 = "b4578f35940bf5a1a655214a1cce5cab13eba73c1297cd78e1a04c2380b0152f"


class Command(BaseCommand):
    help = "Fetch the official MediaPipe short-range face detector model."

    def handle(self, **options):
        with urlopen(MODEL_URL, timeout=30) as response:
            data = response.read(1024 * 1024 + 1)
        digest = hashlib.sha256(data).hexdigest()
        if len(data) > 1024 * 1024 or data[4:8] != b"TFL3" or digest != MODEL_SHA256:
            raise CommandError("Unexpected MediaPipe model file.")
        model = settings.EG_FACE_MODEL
        model.parent.mkdir(parents=True, exist_ok=True)
        model.write_bytes(data)
        self.stdout.write(f"{model} SHA-256 {digest}")
