import hashlib
import tempfile
from pathlib import Path
from uuid import uuid4

import av
from django.conf import settings
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from .models import Segment, Session
from .services import elapsed, media_path


class UploadError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def probe(path):
    try:
        with path.open("rb") as file:
            if file.read(4) != b"\x1a\x45\xdf\xa3":
                raise UploadError("仅接受 WebM 片段。")
            file.seek(0)
            with av.open(file, format="matroska") as container:
                if len(container.streams.video) != 1 or len(container.streams.audio) != 1:
                    raise UploadError("片段需要一条视频轨和一条音频轨。", 422)
                if container.streams.video[0].codec_context.name not in {"vp8", "vp9", "av1"} or (
                    container.streams.audio[0].codec_context.name not in {"opus", "vorbis"}
                ):
                    raise UploadError("WebM 编码不受支持。", 422)
                video = container.streams.video[0].codec_context
                if video.width * video.height > 1920 * 1080:
                    raise UploadError("视频分辨率过高。", 422)
                first, last = {}, {}
                for packet in container.demux(video=0, audio=0):
                    if packet.pts is None or not packet.size:
                        continue
                    stream = packet.stream.type
                    position = float(packet.pts * packet.time_base)
                    stop = position + float((packet.duration or 0) * packet.time_base)
                    first[stream] = min(position, first.get(stream, position))
                    last[stream] = max(stop, last.get(stream, stop))
                if len(first) != 2:
                    raise UploadError("音频或视频轨为空。", 422)
                duration = round((min(last.values()) - max(first.values())) * 1000)
                if duration < 50 or duration > 15000:
                    raise UploadError("媒体时长无效。", 422)
                return duration
    except (av.error.FFmpegError, OSError, ValueError) as exc:
        raise UploadError("文件无法读取为有效的 WebM 片段。", 422) from exc


def store_segment(session_id, key, start, claimed_end, device, uploaded):
    if not 32 <= uploaded.size <= settings.EG_MAX_SEGMENT_BYTES:
        raise UploadError("片段大小超出限制。", 413)
    settings.EG_MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
    sha = hashlib.sha256()
    destination = None
    committed = False
    with tempfile.NamedTemporaryFile(dir=settings.EG_MEDIA_ROOT, prefix="upload-", suffix=".tmp", delete=False) as temp:
        temporary = Path(temp.name)
        for chunk in uploaded.chunks():
            sha.update(chunk)
            temp.write(chunk)
    try:
        digest = sha.hexdigest()
        duration = probe(temporary)
        with transaction.atomic():
            session = Session.objects.select_for_update().filter(pk=session_id).first()
            if session is None:
                raise UploadError("该作答已删除。", 410)
            existing = session.segments.filter(key=key).first()
            if existing:
                if existing.sha256 != digest or existing.start_ms != start:
                    raise UploadError("该片段编号已被不同的录制使用。", 409)
                return existing, False
            if session.state not in (Session.State.ACTIVE, Session.State.CLOSING):
                raise UploadError("该作答已结束接收。", 409)
            now = timezone.now()
            if session.close_after and session.close_after <= now:
                raise UploadError("该作答收尾窗口已结束。", 409)
            limit = min(elapsed(session, now) + 2000, settings.EG_MAX_SESSION_SECONDS * 1000)
            if session.ended_at is not None:
                limit = min(limit, session.end_ms + 1500)
            end = min(start + duration, claimed_end, limit)
            if start < 0 or start + 50 > end or claimed_end - start > 15000:
                raise UploadError("片段时间不在会话范围内。", 422)
            if session.segments.filter(start_ms__lt=end - 250, end_ms__gt=start + 250).exists():
                raise UploadError("片段时间与已保存的录制重叠。", 409)
            used = session.segments.aggregate(total=Sum("size", default=0))["total"]
            if used + uploaded.size > settings.EG_MAX_SESSION_BYTES:
                raise UploadError("该作答已到媒体配额。", 413)
            name = f"{session_id}/{uuid4()}.webm"
            destination = media_path(name)
            destination.parent.mkdir(exist_ok=True)
            temporary.replace(destination)
            saved = Segment.objects.create(
                session=session, key=key, start_ms=start, end_ms=end, device_at_ms=device,
                duration_ms=duration, size=uploaded.size, sha256=digest, file_name=name,
            )
        committed = True
        return saved, True
    finally:
        temporary.unlink(missing_ok=True)
        if destination and not committed:
            destination.unlink(missing_ok=True)
