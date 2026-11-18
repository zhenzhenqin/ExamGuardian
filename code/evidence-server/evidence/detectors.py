import hashlib
from importlib import metadata
from pathlib import Path

import av
from django.conf import settings


class Faces:
    def __init__(self, method):
        self.method = method
        if method == "haar":
            import cv2

            self.cv2 = cv2
            path = settings.EG_HAAR_MODEL
            if not path.is_file():
                path = Path(cv2.data.haarcascades, "haarcascade_frontalface_default.xml")
            if not path.is_file():
                raise ValueError("OpenCV model missing. Run fetch_face_model.")
            xml = path.read_text(encoding="utf-8")
            self.detector = cv2.CascadeClassifier()
            storage = cv2.FileStorage(xml, cv2.FILE_STORAGE_READ | cv2.FILE_STORAGE_MEMORY)
            try:
                loaded = storage.isOpened() and self.detector.read(storage.getFirstTopLevelNode())
            finally:
                storage.release()
            if not loaded or self.detector.empty():
                raise ValueError("OpenCV classifier missing.")
            self.version = {"opencv": cv2.__version__, "model": "haarcascade_frontalface_default",
                            "modelSha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        else:
            import mediapipe as mp
            from mediapipe.tasks import python
            from mediapipe.tasks.python import vision

            self.mp = mp
            model = settings.EG_FACE_MODEL
            if not model.is_file():
                raise ValueError("MediaPipe model missing. Run fetch_face_model.")
            model_data = model.read_bytes()
            self.detector = vision.FaceDetector.create_from_options(vision.FaceDetectorOptions(
                base_options=python.BaseOptions(model_asset_buffer=model_data),
                running_mode=vision.RunningMode.IMAGE,
                min_detection_confidence=0.5,
            ))
            self.version = {"mediapipe": mp.__version__, "modelSha256": hashlib.sha256(model_data).hexdigest()}

    def close(self):
        if self.method != "haar":
            self.detector.close()

    def count(self, frame):
        if self.method == "haar":
            image = frame.to_ndarray(format="gray")
            return len(self.detector.detectMultiScale(image, scaleFactor=1.1, minNeighbors=5, minSize=(24, 24)))
        image = self.mp.Image(image_format=self.mp.ImageFormat.SRGB, data=frame.to_ndarray(format="rgb24"))
        return len(self.detector.detect(image).detections)


def intervals(samples, interval, duration, *, jitter=20):
    previous = None
    for start, kind in samples:
        if start >= duration:
            break
        end = min(duration, start + interval)
        if previous and previous[0] == kind and start - previous[2] <= jitter:
            previous = (kind, previous[1], end)
        else:
            if previous and previous[0]:
                yield previous
            previous = (kind, start, end)
    if previous and previous[0]:
        yield previous


def video_samples(path, faces):
    next_sample = 0
    base = None
    with path.open("rb") as file, av.open(file, format="matroska") as recording:
        for frame in recording.decode(video=0):
            if frame.time is None:
                continue
            base = frame.time if base is None else base
            position = round((frame.time - base) * 1000)
            if position < next_sample:
                continue
            next_sample = (position // 500 + 1) * 500
            count = faces.count(frame)
            yield position, "NO_FACE" if count == 0 else "ONE_FACE" if count == 1 else "MULTIPLE_FACES"


def audio_samples(path):
    import webrtcvad

    vad = webrtcvad.Vad(2)
    converter = av.AudioResampler(format="s16", layout="mono", rate=16000)
    position = 0
    pending = bytearray()
    frame_bytes = 640
    with path.open("rb") as file, av.open(file, format="matroska") as recording:
        for frame in recording.decode(audio=0):
            for converted in converter.resample(frame):
                pending.extend(bytes(converted.planes[0])[:converted.samples * 2])
            while len(pending) >= frame_bytes:
                active = vad.is_speech(bytes(pending[:frame_bytes]), 16000)
                del pending[:frame_bytes]
                yield position, "VOICE_ACTIVITY" if active else None
                position += 20


def analyze_segment(path, faces, duration):
    results = list(intervals(video_samples(path, faces), 500, duration, jitter=100))
    if not results:
        raise ValueError("Video frames could not be decoded.")
    results.extend(intervals(audio_samples(path), 20, duration))
    return results


def versions(faces):
    return {**faces.version, "pyav": av.__version__, "webrtcvad": metadata.version("webrtcvad-wheels"),
            "visionSampleMs": 500, "vadFrameMs": 20, "vadMode": 2}
