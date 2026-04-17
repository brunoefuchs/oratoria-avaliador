# CHANGELOG — squad oratoria-avaliador

## [0.7.0-alpha.3] — 2026-04-17

### Story 9.4 — openSMILE eGeMAPS + pyannote VAD (Epic 9 Wave 2, CPU-only)

**Status:** Ready for Review

#### Added
- `OPENSMILE_ENABLED` feature flag (default false)
- `PYANNOTE_VAD_ENABLED` feature flag (default false)
- `workers/_prosody_extras.py` — `extract_egemaps()` + `detect_pauses()` com fallback librosa
- `tests/test_prosody_extras.py` — 11 testes mockados
- `pyproject.toml` `[project.optional-dependencies] prosody` — opensmile + pyannote.audio

#### Changed
- `voice_analyzer.analyze_prosody` adiciona campos opcionais quando flags ON:
  - `egemaps: dict[str, float]` — 88 features eGeMAPSv02
  - `pauses_classified: dict` — micro/hesitation/retorical + ratio + source
- Lazy imports garantem pipeline não quebra se libs não instaladas

#### Pause classification thresholds
- Micro: <0.4s (natural)
- Hesitation: 0.4–1.2s (nervosismo)
- Retorical: >1.2s (Vinh "highlighter verbal")

#### Cascata pauses detection
1. pyannote VAD (requer HF_TOKEN) — preferido
2. librosa silence-detection — fallback
3. lista vazia + source="none" — graceful degradation

#### Tests
- 11 novos em test_prosody_extras.py (mockado, zero instalação real)
- Regression: 266/266 PASS (+11 de 255)
- Lint + format: clean

#### Deferred
- Install real via `pip install -e ".[prosody]"` — ambiente prod
- HF_TOKEN setup doc — docs/guides/ (follow-up)
- Performance overhead real (AC5) — medição pós-merge em shadow

---

## [0.7.0-alpha.2] — 2026-04-17

### Story 9.2 — Whisper large-v3-turbo + VRAM Orchestrator (Epic 9 Wave 1)

**Status:** InReview (branch `feature/9.2-whisper-turbo-vram-orchestrator`)

#### Added
- `WHISPER_TURBO_ENABLED` feature flag (default true, opt-out rollback)
- `MODEL_ORCHESTRATOR_ENABLED` feature flag (default false até Gate 1 PASS — AC9 pós-merge)
- `workers/_model_loader.py` — `ModelGPU` context manager + `MODEL_FACTORIES` registry
- `scripts/vram_check.py` — Gate 1 hardware smoke (exit 0/1/2)
- `scripts/wer_benchmark.py` — AC6 WER comparison (skip gracioso sem fixtures)
- `tests/test_model_loader.py` — 7 testes mockados (registry, context, thread-safe)
- `tests/test_voice_analyzer_turbo.py` — 7 testes AC1 resolution + AC2 fallback

#### Changed
- `voice_analyzer.transcribe_audio`: model_name now `str | None`, resolve via flag/env
- `voice_analyzer._load_whisper_with_fallback`: fallback automático turbo → medium
- `voice_analyzer.transcribe_audio`: try/finally unload VRAM quando orchestrator ativo
- `app.py`: passa `None` pra transcribe_audio (deixa flag resolver)
- `pyproject.toml`: adiciona `voice_analyzer.py` a per-file-ignores E501

#### Gate 1 — Hardware smoke (real RTX 4060 Laptop 8.59GB)
| Model | Peak VRAM | Status |
|---|---|---|
| whisper_turbo | 4.93 GB | ✅ |
| whisper_medium | 4.58 GB | ✅ |
| Peak global | **4.93 GB** | ≤ 7.5GB budget |

**Verdict: PASS** — RTX 4060 suporta Epic 9 completo.

#### Deferred
- AC6 WER benchmark execução — roadmap Story 9.1.1 (precisa fixtures de áudio)
- AC9 default flip `MODEL_ORCHESTRATOR_ENABLED=true` — follow-up commit pós-merge
- jiwer lib add — só quando fixtures existirem

#### Tests
- Regression: 255/255 PASS (241 baseline + 14 novos)
- Lint: `ruff check` All checks passed
- Format: `ruff format --check` clean

---

## [0.7.0-alpha.1] — 2026-04-17

### Story 9.1 — Aggregator Refactor + Confidence Badges (Epic 9)

**Status:** InReview (feature branch, pre-@qa gate)

#### Added
- `SECONDARY_DIMENSIONS` (7 dims) em `contracts/dimensions.py` — separa análise
  complementar (archetypes, tonality, opening, identity, storytelling, temporal,
  congruence) de scoring core.
- `DIMENSION_CONFIDENCE` mapping hardcoded (5 alta, 4 media, 4 baixa).
- `SCHEMA_VERSION_V060` / `SCHEMA_VERSION_V070` constantes.
- `STATE_OF_ART_ENABLED` feature flag em `config.py` (default false).
- Novo payload field `dimension_confidence: dict[str, str]` (flag ON).
- Novo payload field `schema_version` (1.2.0 flag ON / 1.1.0 flag OFF).
- `ConfidenceBadge` React component + tipos TypeScript.
- Legenda + badges per-card em `report/[id]/page.tsx`.
- Prompt awareness em `report_generator.py` — seção "CONFIANCA DAS MEDICOES"
  com instrução hedge para dims 🔴.

#### Changed
- `SCORING_DIMENSIONS` reduz de 10 → 6 (posture, gesture, voice, fillers,
  variety, facial). facial promovida de "scoring fantasma" para scoring real.
- `PESOS_DEFAULT` reescrito (6 dims, soma 1.00) — valores HEURISTIC_V1.
- `PESOS_POR_CONTEXTO` reescrito para 6 contextos × 6 dims.
- `aggregate_metrics()` flag-aware via `is_state_of_art_enabled()`.
- `AggregatedMetrics` Pydantic ganha fields opcionais dimension_confidence +
  schema_version.

#### Preserved (rollback safety)
- `SCORING_DIMENSIONS_V060` (10 dims) — legacy backup.
- `PESOS_DEFAULT_V060` + `PESOS_POR_CONTEXTO_V060` — pre-Epic 9 preservado.
- `aggregate_metrics_legacy()` intocado (Epic 8 guarantee).
- Flag OFF → comportamento bit-idêntico v0.6.0 garantido por tests.

#### Tests
- 18 novos em `tests/test_dimensions.py` (v0.7.0 topology + confidence + schema)
- 13 novos em `tests/test_aggregator_story_9_1.py` (AC1, 2, 3, 4, 5, 7, 8)
- Fixture `all_success_results` ampliada para ALL_DIMENSIONS (13)
- **Regression:** 240/240 PASS

#### Known followups
- **Story 9.7** (condicional): calibração pesos contextuais pós-Gate 3 com
  ground truth Gui Reginatto. Disparada se Pearson <0.75 ou desvio sistemático
  por contexto detectado.
- **Gate 2 smoke** em 10 vídeos de calibração — docs/qa/gate2-story91-smoke.md
  agendado para @qa executar (replay Supabase, delta ≤15pt, rastreabilidade).

#### Migration notes (consumers)
- Frontend: campo `dimension_confidence` é opcional — verificar via `?.` antes de renderizar.
- Backend consumers: `AggregatedMetrics.schema_version` é opcional, checar `is not None`.
- Nenhuma breaking change com flag OFF.

---

## [0.6.0] — 2026-04-15 (validated)

Baseline pre-Epic 9. Score 9.0/10 no validate-squad.

Ver `docs/validation-report-2026-04-15-v0.6.0.md` para detalhes.
