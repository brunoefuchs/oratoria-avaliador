# WavLM-base+ Smoke Test — 2026-05-06

**Story 10.1 — Path 1 v2 (infra-only)**

## Resultado

- Vídeos processados: 7/7
- VRAM peak: 0.000 GB (target <0.5 GB) — PASS ✅
- Embedding shape: (768,) ✅
- Pairwise cosine sim mean: 0.858 (distingue speakers) ✅

## Per-video stats

| Apelido | Status | Shape | Norm | Elapsed (s) |
|---|---|---|---|---|
| GUI ITAJAI | ✅ | (768,) | 1.67 | 27.1 |
| ALUNA MORENA | ✅ | (768,) | 2.38 | 6.2 |
| GUI PRIME | ✅ | (768,) | 2.06 | 4.1 |
| ALUNO MONO | ✅ | (768,) | 1.91 | 3.7 |
| ALUNA LOIRA | ✅ | (768,) | 2.39 | 2.0 |
| GUI WENDEL | ✅ | (768,) | 1.61 | 2.2 |
| GUI ARARANGUA | ✅ | (768,) | 2.16 | 2.7 |

## Conclusão

WavLM-base+ infra disponível e funcional. Sem consumer ainda — features prontas pra dims futuras (vocal_resonance, custom VAD head Epic 11+).
