import subprocess
import time
from pathlib import Path

import structlog

logger = structlog.get_logger()


def split_video(video_path: str) -> tuple[str, str]:
    """Split video into audio (WAV 16kHz mono) and keep video reference.

    Returns (audio_path, video_path).
    """
    start = time.time()
    video_path_obj = Path(video_path)

    audio_path = str(video_path_obj.parent / f"{video_path_obj.stem}_audio.wav")

    cmd = [
        "ffmpeg",
        "-i",
        video_path,
        "-ar",
        "16000",
        "-ac",
        "1",
        "-f",
        "wav",
        "-y",
        audio_path,
    ]

    logger.info("ffmpeg_split_start", video_path=video_path)

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=300,
    )

    if result.returncode != 0:
        logger.error(
            "ffmpeg_split_failed",
            stderr=result.stderr[:500],
            returncode=result.returncode,
        )
        raise RuntimeError(f"FFmpeg failed: {result.stderr[:200]}")

    duration = time.time() - start
    logger.info(
        "ffmpeg_split_complete",
        audio_path=audio_path,
        duration_seconds=round(duration, 2),
    )

    return audio_path, video_path
