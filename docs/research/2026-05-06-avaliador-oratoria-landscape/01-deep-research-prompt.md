# Deep Research Prompt

## Objetivo

Mapear o landscape de avaliação automática de oratória/comunicação para informar decisões de roadmap do projeto Oratória Avaliador (que já tem 14 dims em produção).

## Decomposição em 12 sub-queries (4 tracks × 3)

### Track 1 — SOTA Acadêmico 2024-2026
1.1. Multimodal automatic public speaking assessment 2025 (transformer fusion prosody+gaze+gesture).
1.2. Datasets POM, MIT Interview, AVI Challenge 2025, FICS — benchmarks.
1.3. Late vs early vs intermediate fusion — comparações 2024-2025.

### Track 2 — Concorrentes Comerciais
2.1. Yoodli/Poised/Orai/Speeko — features, dimensões, pricing.
2.2. Virtual Orator / Verble / VR-based — diferenciação.
2.3. Yoodli deep-dive — relatório, métricas expostas.

### Track 3 — Rubricas Humanas
3.1. Toastmasters Pathways — critérios e evaluation forms.
3.2. ETS TOEFL/IELTS Speaking rubric — delivery/language use/topic development.
3.3. Patsy Rodenburg "Second Circle" — framework de presença.

### Track 4 — Tecnologia Substituta
4.1. wav2vec2 alternatives — HuBERT, WavLM, w2v-BERT 2.0, prosody.
4.2. py-feat alternatives — OpenFace 3.0, LibreFace, PyFaceAU (Py3.12).
4.3. Gaze estimation — L2CS-Net, ETH-XGaze, recentes 2024-2025.

## Output esperado

- `02-research-report.md` — findings detalhados por track
- `03-recommendations.md` — recomendações priorizadas (sem código de produção)
- README.md com TL;DR + cross-walk Track 3 + tabela diferenciação Track 2 + lista priorizada Track 4 + papers shortlist Track 1.

## Restrições

- Não implementar.
- Confidence tags em cada finding.
- Citações verificadas.
