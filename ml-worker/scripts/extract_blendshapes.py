"""Story 10.2 Fase 0 — Spike Blendshapes Extraction.

Habilita output_face_blendshapes=True no FaceLandmarker e dump 52 ARKit
blendshape coefficients por frame nos 7 vídeos do bench.

Standalone deliverable: CSV por vídeo + summary.md. Desbloqueio Py3.12
informacional (prova que MediaPipe blendshapes funcionam no stack atual).

NÃO modifica facial_analyzer.py main code — script paralelo isolado.

Uso:
    cd ml-worker && source .venv/bin/activate
    python scripts/extract_blendshapes.py
"""

from __future__ import annotations

import csv
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cv2  # type: ignore
import mediapipe as mp  # type: ignore


# Caminhos (mesma config do facial_analyzer)
FACE_MODEL_PATH = "/tmp/mediapipe_models/face_landmarker.task"

# 7 vídeos do bench v6 (mesmo set do WavLM smoke)
BENCH_VIDEOS = [
    ("GUI ITAJAI", "/tmp/oratoria_4jm0u9oh/video.MP4"),
    ("ALUNA MORENA", "/tmp/oratoria_0bo4g9zy/video.MP4"),
    ("GUI PRIME", "/tmp/oratoria_xl74dgn_/video.mp4"),
    ("ALUNO MONO", "/tmp/oratoria_2qe817ay/video.mp4"),
    ("ALUNA LOIRA", "/tmp/oratoria_aolggwtn/video.MP4"),
    ("GUI WENDEL", "/tmp/oratoria_co1336if/video.MP4"),
    ("GUI ARARANGUA", "/tmp/oratoria_8pijzq01/video.MP4"),
]

SAMPLE_EVERY_N_FRAMES = 5  # ~6 fps em vídeo 30fps — equilíbrio sinal vs custo


def extract_video(video_path: str, out_csv: Path) -> dict:
    """Extrai blendshapes de 1 vídeo. Retorna stats."""
    BaseOptions = mp.tasks.BaseOptions
    FaceLandmarker = mp.tasks.vision.FaceLandmarker
    FaceLandmarkerOptions = mp.tasks.vision.FaceLandmarkerOptions
    VisionRunningMode = mp.tasks.vision.RunningMode

    options = FaceLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=FACE_MODEL_PATH),
        running_mode=VisionRunningMode.VIDEO,
        num_faces=1,
        output_face_blendshapes=True,  # ← chave da Fase 0
        output_facial_transformation_matrixes=False,
    )

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return {"status": "video_open_failed"}

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    blendshape_names = None
    rows = []
    sampled = 0
    detected = 0

    with FaceLandmarker.create_from_options(options) as landmarker:
        idx = 0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if idx % SAMPLE_EVERY_N_FRAMES != 0:
                idx += 1
                continue

            ts_ms = int((idx / fps) * 1000)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

            try:
                result = landmarker.detect_for_video(mp_img, ts_ms)
            except Exception:
                idx += 1
                continue

            sampled += 1
            time_s = round(idx / fps, 2)

            if not result.face_blendshapes:
                row = {"frame": idx, "time_s": time_s, "face_detected": 0}
                rows.append(row)
                idx += 1
                continue

            detected += 1
            bs_list = result.face_blendshapes[0]  # 1 face
            if blendshape_names is None:
                blendshape_names = [b.category_name for b in bs_list]

            row = {"frame": idx, "time_s": time_s, "face_detected": 1}
            for b in bs_list:
                row[b.category_name] = round(b.score, 4)
            rows.append(row)
            idx += 1

    cap.release()

    # Write CSV
    if blendshape_names is None:
        return {"status": "no_face_detected_anywhere", "sampled": sampled, "total_frames": total_frames}

    fieldnames = ["frame", "time_s", "face_detected"] + blendshape_names
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with open(out_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for r in rows:
            for k in fieldnames:
                r.setdefault(k, "")
            writer.writerow(r)

    return {
        "status": "ok",
        "sampled": sampled,
        "detected": detected,
        "detection_rate": round(detected / max(1, sampled) * 100, 1),
        "total_frames": total_frames,
        "fps": round(fps, 1),
        "blendshape_count": len(blendshape_names),
        "blendshape_names": blendshape_names,
    }


def main():
    output_dir = Path(__file__).resolve().parents[2] / "docs" / "qa" / "blendshape-spike-2026-05-06"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== Blendshape Spike — Story 10.2 Fase 0 ===\n")

    all_stats = {}
    blendshape_names_canonical = None
    for apelido, video_path in BENCH_VIDEOS:
        if not Path(video_path).exists():
            print(f"  ⚠️  {apelido}: video missing ({video_path})")
            all_stats[apelido] = {"status": "video_missing"}
            continue

        out_csv = output_dir / f"{apelido.replace(' ', '_')}.csv"
        print(f"  Processing {apelido}...", end=" ", flush=True)
        t0 = time.time()
        stats = extract_video(video_path, out_csv)
        elapsed = time.time() - t0
        stats["elapsed_seconds"] = round(elapsed, 1)

        if stats.get("status") == "ok":
            if blendshape_names_canonical is None:
                blendshape_names_canonical = stats["blendshape_names"]
            print(
                f"✅ {stats['blendshape_count']} blendshapes × "
                f"{stats['detected']}/{stats['sampled']} frames "
                f"({stats['detection_rate']}%) — {elapsed:.1f}s"
            )
        else:
            print(f"❌ {stats.get('status')}")

        # Drop blendshape_names from individual stats (canonical at top)
        stats_save = {k: v for k, v in stats.items() if k != "blendshape_names"}
        all_stats[apelido] = stats_save

    # Master summary
    summary_path = output_dir / "summary.md"
    with open(summary_path, "w") as f:
        f.write("# Blendshape Spike — Story 10.2 Fase 0\n\n")
        f.write("**Data:** 2026-05-06\n\n")
        f.write("**Objetivo:** Verificar que MediaPipe FaceLandmarker expõe blendshapes ")
        f.write("ARKit-style nos 7 vídeos do bench. Standalone deliverable; desbloqueio ")
        f.write("Py3.12 informacional.\n\n")

        if blendshape_names_canonical:
            f.write(f"## Blendshapes detectados ({len(blendshape_names_canonical)})\n\n")
            f.write("```\n")
            f.write(", ".join(blendshape_names_canonical))
            f.write("\n```\n\n")

        f.write("## Per-vídeo stats\n\n")
        f.write("| Apelido | Status | Frames sampled | Face detected | Detection % | Elapsed (s) |\n")
        f.write("|---|---|---|---|---|---|\n")
        for apelido in [v[0] for v in BENCH_VIDEOS]:
            s = all_stats.get(apelido, {})
            if s.get("status") == "ok":
                f.write(
                    f"| {apelido} | ✅ | {s['sampled']} | {s['detected']} | "
                    f"{s['detection_rate']}% | {s['elapsed_seconds']} |\n"
                )
            else:
                f.write(f"| {apelido} | ❌ {s.get('status', '?')} | — | — | — | — |\n")

        n_ok = sum(1 for s in all_stats.values() if s.get("status") == "ok")
        f.write(f"\n## Conclusão Fase 0\n\n")
        f.write(f"- Vídeos processados com sucesso: **{n_ok}/{len(BENCH_VIDEOS)}**\n")
        if blendshape_names_canonical:
            f.write(f"- Blendshapes ARKit-style expostos: **{len(blendshape_names_canonical)}**\n")
            f.write(f"- Esperado pra mapping table de `05-mediapipe-au-bridge-spec.md`: 52 → ")
            f.write("✅ confirmado\n" if len(blendshape_names_canonical) >= 52 else "⚠️ menos que esperado\n")
        f.write(f"\n**Próxima fase:** Fase 1 — bridge module determinístico ")
        f.write("`_facs_blendshape_bridge.py` (ver story 10.2 AC2).\n")

    # Save aggregate JSON
    with open(output_dir / "stats.json", "w") as f:
        json.dump({"per_video": all_stats, "blendshape_names": blendshape_names_canonical}, f, indent=2)

    print(f"\n  Outputs: {output_dir}/")
    print(f"  Summary: {summary_path}")
    print(f"\n=== FASE 0 {'PASS ✅' if n_ok >= 5 else 'PARTIAL ⚠️'} ===")


if __name__ == "__main__":
    main()
