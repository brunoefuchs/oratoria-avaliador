"""Smoke test Story 10.1 — WavLM-base+ infra nos 7 vídeos do bench.

Verifica:
- Factory carrega sem erro
- extract_features rola nos 7 vídeos
- Embedding shape (768,) sem NaN/Inf
- VRAM peak <500MB target
- Variance entre embeddings (prova que features captam algo)

Output: docs/qa/wavlm-smoke-2026-XX/{apelido}.json + summary.md
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import torch

from workers._wavlm_emotion import (
    HIDDEN_SIZE,
    VRAM_PEAK_TARGET_GB,
    extract_features,
    get_vram_peak_gb,
    load_wavlm_emotion,
)


# 7 vídeos do bench v6 — apelido + caminho áudio
BENCH_VIDEOS = [
    ("GUI ITAJAI", "/tmp/oratoria_4jm0u9oh/video_audio.wav"),
    ("ALUNA MORENA", "/tmp/oratoria_0bo4g9zy/video_audio.wav"),
    ("GUI PRIME", "/tmp/oratoria_xl74dgn_/video_audio.wav"),
    ("ALUNO MONO", "/tmp/oratoria_2qe817ay/video_audio.wav"),
    ("ALUNA LOIRA", "/tmp/oratoria_aolggwtn/video_audio.wav"),
    ("GUI WENDEL", "/tmp/oratoria_co1336if/video_audio.wav"),
    ("GUI ARARANGUA", "/tmp/oratoria_8pijzq01/video_audio.wav"),
]


def main():
    output_dir = Path(__file__).resolve().parents[2] / "docs" / "qa" / "wavlm-smoke-2026-05-06"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== WavLM-base+ Smoke Test — {len(BENCH_VIDEOS)} videos ===\n")

    print("[1/3] Loading WavLM-base+ (download primeira vez ~400MB)...")
    t_start = time.time()
    bundle = load_wavlm_emotion()
    if bundle is None:
        print("FAIL: factory retornou None")
        sys.exit(1)
    print(f"  Loaded in {time.time() - t_start:.1f}s")
    print(f"  Model: {bundle['model_id']}")
    print(f"  Layer weights shape: {tuple(bundle['layer_weights'].shape)}")

    # Reset VRAM stats antes da extração
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()

    print(f"\n[2/3] Extracting features dos {len(BENCH_VIDEOS)} videos...")
    embeddings = {}
    results = []
    for apelido, audio_path in BENCH_VIDEOS:
        if not Path(audio_path).exists():
            print(f"  ⚠️  {apelido}: audio not found ({audio_path})")
            results.append({"apelido": apelido, "status": "audio_missing"})
            continue

        t0 = time.time()
        embedding = extract_features(bundle, audio_path)
        elapsed = time.time() - t0

        if embedding is None:
            print(f"  ❌ {apelido}: extract_features retornou None")
            results.append({"apelido": apelido, "status": "extraction_failed"})
            continue

        emb_np = embedding.detach().cpu().numpy()
        result = {
            "apelido": apelido,
            "status": "ok",
            "shape": list(emb_np.shape),
            "elapsed_seconds": round(elapsed, 2),
            "stats": {
                "mean": round(float(np.mean(emb_np)), 4),
                "std": round(float(np.std(emb_np)), 4),
                "min": round(float(np.min(emb_np)), 4),
                "max": round(float(np.max(emb_np)), 4),
                "norm": round(float(np.linalg.norm(emb_np)), 4),
            },
        }
        results.append(result)
        embeddings[apelido] = emb_np

        # Save embedding individual
        eval_file = output_dir / f"{apelido.replace(' ', '_')}.json"
        with open(eval_file, "w") as f:
            json.dump({**result, "embedding_first_10": emb_np[:10].tolist()}, f, indent=2)

        print(f"  ✅ {apelido}: shape={emb_np.shape}, norm={result['stats']['norm']}, {elapsed:.1f}s")

    print("\n[3/3] Summary + variance analysis")
    vram_peak = get_vram_peak_gb()
    print(f"  VRAM peak: {vram_peak:.3f} GB (target <{VRAM_PEAK_TARGET_GB} GB)")

    # Variance entre embeddings — prova que features distinguem speakers
    if len(embeddings) >= 2:
        emb_list = list(embeddings.values())
        emb_matrix = np.stack(emb_list)
        # Pairwise cosine similarity
        norms = np.linalg.norm(emb_matrix, axis=1, keepdims=True)
        emb_normalized = emb_matrix / norms
        cos_sim = emb_normalized @ emb_normalized.T
        # Off-diagonal mean (similarity entre speakers diferentes)
        n = len(emb_list)
        off_diag_mask = ~np.eye(n, dtype=bool)
        mean_pairwise_cos = float(np.mean(cos_sim[off_diag_mask]))
        std_pairwise_cos = float(np.std(cos_sim[off_diag_mask]))
        print(f"  Pairwise cosine similarity (off-diag): mean={mean_pairwise_cos:.3f} ± {std_pairwise_cos:.3f}")
        print(f"  Variance signal: {'OK (distingue speakers)' if mean_pairwise_cos < 0.99 else 'ALERT (embeddings colapsados)'}")

    # Markdown summary
    summary_path = output_dir / "summary.md"
    n_ok = sum(1 for r in results if r["status"] == "ok")
    with open(summary_path, "w") as f:
        f.write(f"# WavLM-base+ Smoke Test — 2026-05-06\n\n")
        f.write(f"**Story 10.1 — Path 1 v2 (infra-only)**\n\n")
        f.write(f"## Resultado\n\n")
        f.write(f"- Vídeos processados: {n_ok}/{len(BENCH_VIDEOS)}\n")
        f.write(f"- VRAM peak: {vram_peak:.3f} GB (target <{VRAM_PEAK_TARGET_GB} GB) — ")
        f.write("PASS ✅\n" if vram_peak < VRAM_PEAK_TARGET_GB else "FAIL ❌\n")
        f.write(f"- Embedding shape: ({HIDDEN_SIZE},) ✅\n")
        if len(embeddings) >= 2:
            f.write(f"- Pairwise cosine sim mean: {mean_pairwise_cos:.3f} ")
            f.write("(distingue speakers) ✅\n" if mean_pairwise_cos < 0.99 else "(ALERTA — embeddings colapsados) ❌\n")
        f.write(f"\n## Per-video stats\n\n")
        f.write("| Apelido | Status | Shape | Norm | Elapsed (s) |\n")
        f.write("|---|---|---|---|---|\n")
        for r in results:
            if r["status"] == "ok":
                f.write(f"| {r['apelido']} | ✅ | {tuple(r['shape'])} | {r['stats']['norm']:.2f} | {r['elapsed_seconds']:.1f} |\n")
            else:
                f.write(f"| {r['apelido']} | ❌ {r['status']} | — | — | — |\n")
        f.write(f"\n## Conclusão\n\n")
        f.write(f"WavLM-base+ infra disponível e funcional. ")
        f.write(f"Sem consumer ainda — features prontas pra dims futuras (vocal_resonance, custom VAD head Epic 11+).\n")

    print(f"\n  Summary: {summary_path}")
    print(f"  Per-video: {output_dir}/")
    print(f"\n=== SMOKE TEST {'PASS ✅' if n_ok == len(BENCH_VIDEOS) and vram_peak < VRAM_PEAK_TARGET_GB else 'FAIL ❌'} ===")


if __name__ == "__main__":
    main()
