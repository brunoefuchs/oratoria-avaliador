# Research: Avaliador de Oratória / Comunicação Landscape

**Data:** 2026-05-06
**Coverage:** 78% (1 wave, 12 buscas paralelas + cutoff Jan 2026)
**Stop reason:** Coverage suficiente para decisão de roadmap; follow-up recomendado para itens [LOW] confidence.

## TL;DR (1 parágrafo por track)

**Track 1 — SOTA Acadêmico:** AVI Challenge 2025 é o benchmark vivo mais relevante (3 modalidades, 5 dims). Tendência clara de literatura 2024-2025: combater **modality imbalance** (modelos preferem texto, subutilizam acústico) e **disentangle prosódia** de conteúdo linguístico nos embeddings SSL. Late fusion segue robusto; cross-attention transformer é SOTA mas complexidade alta. Camadas iniciais de wav2vec2/HuBERT captam paralinguística — insight imediatamente acionável.

**Track 2 — Concorrentes:** Yoodli e Poised lideram B2C/B2B (~7 dims expostas, $10-20/mo). Orai e Speeko focam em currículo. Virtual Orator é VR de prática (não avalia). Verble cobre debate. **Nenhum** captura: ground truth blind, 14 dims com famílias estruturais, PT-BR cultural, presença Patsy-Rodenburg-style. Esses são vetores de diferenciação reais para Oratória Avaliador.

**Track 3 — Rubricas humanas:** Toastmasters cobre Speech objectives + Content + Delivery + Language. TOEFL/ETS estrutura em Delivery + Language Use + Topic Development. Cross-walk vs 14 dims revela 2 gaps prováveis: **estrutura narrativa** (arco gancho-meio-payoff) e **ressonância vocal** (chest/mask/head, Roger Love). Presença (Patsy 2nd Circle) é qualitativa — operacionalizar como score composto, não classificador.

**Track 4 — Tecnologia:** **HuBERT/WavLM** são drop-in pra wav2vec2 (memória diz que saiu do HF). **OpenFace 3.0** (paper 2025) é candidato sólido pra py-feat (que bloqueia Py3.12). MediaPipe FaceLandmarker blendshapes podem servir como bridge curto. **L2CS-Net / ETH-XGaze** servem como fallback de gaze. emotion2vec+, TRILLsson, Praat são features incrementais.

## 4 Findings acionáveis aprovados (decisão Bruno 2026-05-06)

1. **Migrar wav2vec2 → WavLM-base+** — drop-in HF, layers 3-10 weighted-sum, NÃO ASR-tuned. Baixo risco.
2. **Bridge MediaPipe blendshapes → AUs** — Apache 2.0, destrava Py3.12. OpenFace 3.0 está bloqueado comercialmente (CMU non-commercial license). Spec em `05-mediapipe-au-bridge-spec.md`.
3. **Adicionar dim `discourse_arc` na família "narrativa"** — slot arquitetural já reservado pela decisão 2026-04-29 (técnica vs narrativa, ver memória). Gap claro vs Toastmasters; concorrentes não cobrem. Auditoria do código mostrou que `opening_analyzer` + `storytelling_analyzer` já cobrem hook/CTA — dim nova fica no arco macro do discurso. Estender storytelling com callback abertura↔fechamento sem dim adicional. Feature flag `NARRATIVE_FAMILY_ENABLED`. Critério de promoção: Pearson ≥0.6 vs Gui em ≥5/7 vídeos (bar Epic 9). Família técnica intocada; remoção limpa se falhar.
4. **Reproduzir AVI Challenge 2025 baseline** — gap 18-38pts vs Gui é relativo; comparar contra benchmark absoluto orienta priorização.

**Rejeitado:** ~~5. Presença (2nd Circle) como score composto~~ — risco de feedback genérico > valor. Princípio "não medir > medir errado".

## Tabela Cross-Walk Rubric × 14 Dims (Track 3)

| Rubric source | Coberto pelo projeto | Gap potencial |
|---|---|---|
| Toastmasters: Voice (Delivery) | ✅ Sound (pitch/volume/pace) | — |
| Toastmasters: Gestures | ✅ Look (gesture/body) | — |
| Toastmasters: Eye contact | ✅ Look (gaze) | — |
| Toastmasters: Content/Organization | ❓ | **Narrative structure** |
| Toastmasters: Language/Vocabulary | ❓ | **Rhetorical devices, sticky language** |
| TOEFL: Pronunciation | ✅ articulation passivo | — |
| TOEFL: Flow/Pacing | ✅ Sound: pacing | — |
| TOEFL: Topic Development | ❓ | **Coherence linguístico** |
| Patsy Rodenburg: 2nd Circle | ❓ Feel (parcial) | **Reciprocidade — score composto** |
| Roger Love: Melody (5 padrões) | ✅ Sound: variety/melody | **Padrões nomeados** |
| Roger Love: Resonance | ❓ | **Chest/mask/head — gap claro** |

## Tabela Diferenciação (Track 2)

| Concorrente | Foco | Vector que Oratória Avaliador supera |
|---|---|---|
| Yoodli | Roleplay + integração calls | Profundidade dims (14 vs 7), PT-BR, mentor calibrado |
| Poised | Real-time during calls | Reflection profunda > tempo real raso |
| Orai | App mobile + cursos | Avaliação granular vs lições genéricas |
| Speeko | Currículo adaptativo | 14 dims diagnósticas vs 3-4 superficiais |
| Virtual Orator | VR practice | Não compete — VR é prática, não avaliação |
| Verble | Debate/argumentação | Foco diferente, complementar |

## Lista Priorizada Tech (Track 4)

1. [ALTA] HuBERT/WavLM em vez de wav2vec2
2. [ALTA] OpenFace 3.0 em vez de py-feat
3. [MÉDIA] Camadas iniciais wav2vec2/HuBERT pra prosódia
4. [MÉDIA] L2CS-Net fallback gaze
5. [BAIXA] emotion2vec+ feature
6. [BAIXA] Praat/parselmouth jitter/shimmer

## Papers Shortlist (Track 1, Top 7)

| # | Citação | Foco |
|---|---|---|
| 1 | arXiv:2507.22676 (2025) | AVI Challenge baseline |
| 2 | arXiv:2508.12591 (2025) | MLLM unificado, curriculum learning |
| 3 | arXiv:2502.19387 (2025) | Disentanglement linguístico/paralinguístico |
| 4 | arXiv:2505.13688 (2025) | Gaze + multimodal turn-taking |
| 5 | PMC12733550 (2025) | Multimodal transformer fusion explainable |
| 6 | arXiv:2506.02891 (2025) | OpenFace 3.0 |
| 7 | MDPI Applied Sciences 5823 (2025) | Early vs late fusion comparison |

## Files

- `00-query-original.md` — pergunta + contexto
- `01-deep-research-prompt.md` — prompt decomposto em 12 sub-queries
- `02-research-report.md` — findings completos por track
- `03-recommendations.md` — 5 acionáveis + secundárias + anti-recomendações
- `curiosity_queue.yaml` — perguntas abertas
- `evolving_report.md` — síntese operacional
- `metrics.yaml` — métricas de pipeline
- `pipeline-state.yaml` — estado das fases
- `execution-log.jsonl` — log mínimo
- `04-deep-read-openface-hubert.md` — follow-up deep-read OpenFace 3.0 + HuBERT/WavLM layer-wise (verdict Py3.12, recipes layer-wise, 2 gates)
- `05-mediapipe-au-bridge-spec.md` — spec da rota 2 (MediaPipe blendshapes → AUs) após bloqueio commercial OpenFace 3.0; mapping table 22 AUs, protocolo de validação contra py-feat, plano fases 0-4
- `06-test-comparativo-concorrentes.md` — Wave 2 de evidência pública (Duarte, G2, Reddit, support docs). Contradiz wave 1 em 3 pontos: Verble não é debate AI, Speeko licenciou Roger Love, críticas públicas validam moat de feedback diagnóstico. Gap top: practice mode multi-persona (Yoodli)

## Próximos passos

- Para **implementar** qualquer recomendação: acionar `@pm` pra priorização e `@dev` pra execução. Esta pesquisa é informativa.
- Para **aprofundar** algum item: usar follow-up `04-*.md` na MESMA pasta.
