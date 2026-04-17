"""Frame sampler — Story 9.6 (Epic 9).

Extrai N frames uniformemente espaçados de um video via ffmpeg (ja instalado),
encoda em base64 PNG reduzida para envio a Gemini Vision.

Uso:
    frames = sample_frames_base64(video_path, fps=0.5, max_frames=120)
    # frames = [{"timestamp_s": 2.0, "image_b64": "..."}, ...]
"""

from __future__ import annotations

import base64
import subprocess
from pathlib import Path

import structlog

logger = structlog.get_logger()

DEFAULT_RESOLUTION = "512x512"  # max dimension pra Gemini Vision


def _extract_frames_ffmpeg(
    video_path: str, fps: float, max_frames: int, resolution: str = DEFAULT_RESOLUTION
) -> list[Path]:
    """Extrai frames via ffmpeg com fps custom + resize. Retorna lista de Paths."""
    output_dir = Path(video_path).parent / "frames_gesture_semantic"
    output_dir.mkdir(exist_ok=True)
    pattern = str(output_dir / "frame_%04d.png")

    # Limpar frames antigos
    for old in output_dir.glob("frame_*.png"):
        old.unlink()

    # -frames:v limita quantidade + scale reduz resolucao pra ~512px max dim
    cmd = [
        "ffmpeg",
        "-i",
        video_path,
        "-vf",
        f"fps={fps},scale='min({resolution.split('x')[0]},iw)':-2",
        "-frames:v",
        str(max_frames),
        "-q:v",
        "3",
        "-y",
        pattern,
    ]

    try:
        subprocess.run(cmd, capture_output=True, timeout=180, check=True)
    except subprocess.CalledProcessError as e:
        logger.warning("ffmpeg_frame_extraction_failed", stderr=e.stderr.decode()[:500])
        return []
    except subprocess.TimeoutExpired:
        logger.warning("ffmpeg_frame_extraction_timeout")
        return []

    return sorted(output_dir.glob("frame_*.png"))


def sample_frames_base64(
    video_path: str,
    fps: float = 0.5,
    max_frames: int = 120,
) -> list[dict]:
    """Sample frames + retorna lista de {timestamp_s, image_b64}.

    Args:
        video_path: caminho do video
        fps: frames por segundo (default 0.5 = 1 frame/2s)
        max_frames: cap duro pra evitar runaway cost

    Returns:
        Lista de {timestamp_s: float, image_b64: str}. Lista vazia em falha.
    """
    frame_paths = _extract_frames_ffmpeg(video_path, fps, max_frames)
    if not frame_paths:
        return []

    result = []
    for i, path in enumerate(frame_paths):
        try:
            with open(path, "rb") as f:
                img_bytes = f.read()
            b64 = base64.b64encode(img_bytes).decode("ascii")
            timestamp = i / fps
            result.append({"timestamp_s": round(timestamp, 2), "image_b64": b64})
        except Exception as e:  # noqa: BLE001
            logger.warning("frame_encoding_failed", path=str(path), error=str(e))

    logger.info("frames_sampled", count=len(result), fps=fps)
    return result


# Custo aproximado Gemini Flash (input: ~$0.075/1M tokens, images ~258 tokens cada)
# Pra N frames a ~258 tokens cada + prompt 2k tokens + output 2k tokens:
# custo ~= (N*258 + 2000) * 0.000000075 + 2000 * 0.0000003
GEMINI_FLASH_INPUT_COST_PER_TOKEN = 0.000000075
GEMINI_FLASH_OUTPUT_COST_PER_TOKEN = 0.0000003
GEMINI_FLASH_IMAGE_TOKENS = 258
PROMPT_TOKEN_ESTIMATE = 2000
OUTPUT_TOKEN_ESTIMATE = 2000


def estimate_cost(num_frames: int) -> float:
    """Estima custo USD pra num_frames (Gemini Flash pricing).

    Story 9.6 AC1 budget guard.
    """
    input_tokens = num_frames * GEMINI_FLASH_IMAGE_TOKENS + PROMPT_TOKEN_ESTIMATE
    output_tokens = OUTPUT_TOKEN_ESTIMATE
    cost = (
        input_tokens * GEMINI_FLASH_INPUT_COST_PER_TOKEN
        + output_tokens * GEMINI_FLASH_OUTPUT_COST_PER_TOKEN
    )
    return round(cost, 4)
