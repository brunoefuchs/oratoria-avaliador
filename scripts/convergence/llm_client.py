"""OpenRouter client — 1 SDK roteando pros 3 modelos.

Por que OpenRouter em vez de 3 SDKs:
- `httpx` já está nas dependências do ml-worker
- 1 endpoint só, 3 models strings diferentes
- Rate limit gerenciado pela OpenRouter
- Pricing unificado, cap fácil de aplicar
"""

from __future__ import annotations

import base64
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path

import httpx


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Model mapping — ajuste via env vars se nomes mudarem.
MODELS = {
    "gemini": os.environ.get("CONVERGENCE_GEMINI_MODEL", "google/gemini-2.5-flash"),
    "claude": os.environ.get("CONVERGENCE_CLAUDE_MODEL", "anthropic/claude-opus-4.1"),
    "gpt": os.environ.get("CONVERGENCE_GPT_MODEL", "openai/gpt-5"),
}

DEFAULT_TIMEOUT = 180.0


@dataclass
class EvaluationResult:
    llm: str
    model_version: str
    score_geral: float
    scores_por_dimensao: dict[str, float]
    pontos_fortes: list[str]
    pontos_fracos: list[str]
    raw_response: str
    latency_seconds: float


class OpenRouterError(RuntimeError):
    pass


def _encode_video_as_data_url(path: Path) -> str:
    data = path.read_bytes()
    b64 = base64.b64encode(data).decode("ascii")
    mime = "video/mp4" if path.suffix.lower() == ".mp4" else "application/octet-stream"
    return f"data:{mime};base64,{b64}"


def _build_messages(prompt: str, video_path: Path | None, video_url: str | None) -> list[dict]:
    """Constructs OpenAI-style messages with a multimodal content block."""
    content: list[dict] = [{"type": "text", "text": prompt}]
    if video_url:
        content.append({"type": "video_url", "video_url": {"url": video_url}})
    elif video_path:
        content.append({"type": "video_url", "video_url": {"url": _encode_video_as_data_url(video_path)}})
    return [{"role": "user", "content": content}]


def _parse_llm_json(text: str) -> dict:
    """LLMs sometimes wrap JSON in ```json fences or add preamble. Strip it."""
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        stripped = "\n".join(lines)
    first_brace = stripped.find("{")
    last_brace = stripped.rfind("}")
    if first_brace == -1 or last_brace == -1:
        raise OpenRouterError(f"No JSON found in LLM response: {text[:200]}")
    return json.loads(stripped[first_brace : last_brace + 1])


def evaluate_with_llm(
    llm: str,
    prompt: str,
    video_path: Path | None = None,
    video_url: str | None = None,
    api_key: str | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> EvaluationResult:
    """Run a single evaluation against one LLM via OpenRouter.

    Args:
        llm: one of "gemini" | "claude" | "gpt"
        prompt: evaluation prompt (see prompts.py)
        video_path: local path to video file (mutually exclusive with video_url)
        video_url: public URL of video (mutually exclusive with video_path)
        api_key: OpenRouter API key (defaults to env OPENROUTER_API_KEY)
        timeout: request timeout in seconds
    """
    if llm not in MODELS:
        raise ValueError(f"Unknown LLM {llm!r}. Options: {list(MODELS)}")
    if not (video_path or video_url):
        raise ValueError("Provide either video_path or video_url")

    key = api_key or os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise OpenRouterError("OPENROUTER_API_KEY not set")

    model = MODELS[llm]
    messages = _build_messages(prompt, video_path, video_url)

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/brunoefuchs/oratoria-avaliador",
        "X-Title": "oratoria-avaliador convergence harness",
    }
    payload = {"model": model, "messages": messages, "temperature": 0.0}

    t0 = time.monotonic()
    with httpx.Client(timeout=timeout) as client:
        resp = client.post(OPENROUTER_URL, headers=headers, json=payload)
    latency = time.monotonic() - t0

    if resp.status_code != 200:
        raise OpenRouterError(f"{llm} ({model}) returned {resp.status_code}: {resp.text[:300]}")

    body = resp.json()
    try:
        text = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as exc:
        raise OpenRouterError(f"Malformed response from {llm}: {body}") from exc

    parsed = _parse_llm_json(text)

    return EvaluationResult(
        llm=llm,
        model_version=model,
        score_geral=float(parsed.get("score_geral", 0)),
        scores_por_dimensao={k: float(v) for k, v in parsed.get("scores_por_dimensao", {}).items()},
        pontos_fortes=list(parsed.get("pontos_fortes", []))[:3],
        pontos_fracos=list(parsed.get("pontos_fracos", []))[:3],
        raw_response=text,
        latency_seconds=latency,
    )


def evaluate_all(
    prompt: str,
    video_path: Path | None = None,
    video_url: str | None = None,
) -> dict[str, EvaluationResult]:
    """Run all 3 LLMs sequentially (OpenRouter throttles internally).

    Sequential > parallel because: OpenRouter 429s hit the same account.
    Parallelism gains ~60s on 10 videos, not worth retry logic complexity.
    """
    results: dict[str, EvaluationResult] = {}
    for llm in MODELS:
        results[llm] = evaluate_with_llm(llm, prompt, video_path, video_url)
    return results
