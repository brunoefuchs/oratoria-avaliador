# Handoff — Sessão 2026-04-15 (Completa)

**Data:** 2026-04-15 → 2026-04-16 (madrugada)
**Duração:** ~6h
**Agentes ativos:** @oalanicolas → @qa Quinn → @dev Dex → @devops Gage (múltiplas rotações)
**Branch principal:** `feat/epic-8-scoring-workers` (local) | PRs #10, #14 mergeados no main

---

## TL;DR

Sessão começou como planejamento de ground truth (Story 7.7) e evoluiu pra smoke test real do harness multi-IA (Story 7.6) + descoberta e correção de 5 bugs de calibração no MediaPipe. Resultado: pipeline de avaliação de oratória testado end-to-end pela primeira vez com 3 modelos LLM + comparação cruzada com workers locais.

---

## 1. Story 7.6 — Harness de Convergência Multi-IA

### Entregue e mergeado (PR #10, commit 544244f)

**Implementação:** Python via SDKs diretos (Gemini + Claude Opus 4.5 + GPT-5)
- `scripts/convergence/` — 6 módulos: harness CLI, llm_client (frames), correlator (Pearson), prompts, persistence
- `supabase/migrations/010_convergence_runs.sql` + `011_convergence_alerts.sql`
- `docs/dev/convergence-harness.md`

**Divergências do spec original (TS/Next.js):**
- Python em vez de TypeScript (stack consistente com ml-worker)
- Extração de frames via ffmpeg (video nativo não suportado por Claude/GPT)
- Jaccard token overlap em vez de embeddings (sem dependência pesada)
- Dashboard Next.js deferido

**Fix pós-merge (CodeRabbit):** 7 bugs corrigidos no commit 8c570f5 (squashed no PR #10):
- Query errada em compare-ground-truth.py (evaluations → aggregated_metrics)
- Claude model default opus-4.1 → opus-4.6
- Batch mode não agregava pra Pearson real (adicionado build_batch_report)
- Loop de alertas só pra pontos_fortes (adicionado pontos_fracos)
- Validation XOR em video_path/video_url
- Migrations não idempotentes (DROP POLICY IF EXISTS)
- FK apontando pra tabela `videos` que não existe (→ `evaluations`)

### Smoke test executado (6 vídeos × 3 LLMs)

| Vídeo | Gemini | Claude | GPT |
|-------|--------|--------|-----|
| WhatsApp 53s | 66 | 68 | 66 |
| Insta-1 68s | 85 | 78 | 75 |
| Insta-2 79s | 90 | 78 | 75 |
| Insta-3 75s | 90 | 78 | 76 |
| Insta-4 63s | 89 | 72 | 72 |
| Insta-5 87s | 88 | 72 | 69 |

**Pearson real (N=6):**
- mean_r_overall: **+0.808** (abaixo do target 0.85)
- claude-gpt: +0.962 (alta convergência entre si)
- gemini diverge sistematicamente +12-18pts acima dos outros 2

**Padrão encontrado:** Gemini é sistematicamente mais generoso nos frames de Instagram. Claude e GPT convergem entre si. Gap Gemini vs Claude+GPT é o principal achado — ground truth do Gui vai resolver quem está certo.

---

## 2. Story 7.7 — Ground Truth Humano (Guilherme Reginatto)

### Artefatos entregues e mergeados (PR #10 + PR #14)

**PR #10 (mergeado):**
- `docs/sessions/2026-04/handoff-7.7-ground-truth-rubric-gui-reginatto.md` — rubric 11-dim v2 (pós-refinamentos R1-R4 do QA)
- `docs/qa/7.7-rubric-validation.md` — QA Gate v1 CONCERNS → v2 PASS
- `docs/templates/7.7-ground-truth-rubric.csv` — 31 colunas
- `docs/templates/7.7-sheet/` — 4 CSVs importáveis + IMPORT-INSTRUCTIONS.md
- `scripts/compare-ground-truth.py` — consolidação app vs Gui

**PR #14 (mergeado):**
- `docs/sessions/2026-04/7.7-curation-criteria-gui.md` — critérios R1-R7 + checklist dividido Gui/Bruno
- `docs/sessions/2026-04/7.7-briefing-script-gui.md` — roteiro 30min call (6 blocos)
- `docs/sessions/2026-04/7.7-recalibration-protocol.md` — árvore de decisão Fase 1B (4 casos)

### Refinamentos QA aplicados (R1-R4)
- R1: descritores intermediários (21-40 e 61-80) em todas 10 dims
- R2: escala múltiplos de 10 (reduz fadiga 48%)
- R3: calibração em 2 fases (Gui solo → Bruno revisa sem revelar scores)
- R4: overall em 3 campos estruturados (força/fraqueza/impressão, min 30 chars)

### Decisão de fontes de vídeos
- Gui traz ~7 de mentorados (mitigação de anchoring documentada)
- Bruno complementa com ~3 da NET
- Critérios R1-R7 aplicados (variedade duração/contexto/qualidade)

---

## 3. Supabase — Projeto novo configurado

- **Projeto:** `Oratoria APP`
- **Ref:** `hkwjjbsjhpdpyypyubnu`
- **URL:** `https://hkwjjbsjhpdpyypyubnu.supabase.co`
- **11 migrations aplicadas** (001-011, incluindo convergence_runs e convergence_alerts)
- **Keys atualizadas** em `.env`, `ml-worker/.env`, `apps/api/.env`
- **⚠️ ROTACIONAR:** service_role key + DB password foram expostos em chat. Rotacionar após estabilização.

---

## 4. MediaPipe — 5 bugs de calibração encontrados e corrigidos

### Método de descoberta

Cross-check automatizado: rodou pipeline MediaPipe + 3 LLMs (frames) no mesmo vídeo → comparou scores → Bruno validou visualmente.

### Bugs corrigidos (commit b8286f0)

| Bug | Arquivo | Métrica | Antes | Depois | Causa |
|-----|---------|---------|-------|--------|-------|
| **MP-1** | gesture_analyzer.py | eye_contact_pct | 100% | 95.4% | GAZE_THRESHOLD 0.35→0.22 + classificação tipo desvio (positivo/negativo/neutro) |
| **MP-2** | posture_analyzer.py | posture score | 76 | 66 | dinamismo_postural novo (30%) + open_posture peso 20%→10% |
| **MP-3** | gesture_analyzer.py | zona_ideal_pct | 1.5% | 91.4% | Threshold zona "media" 0.65→0.80 (bust video fix) |
| **MP-4** | posture_analyzer.py | padrao_movimento | ansioso | energetico | Novo padrão "energetico": desl_medio>0.025 + ratio_parado<20% |
| **MP-5** | archetype_classifier.py | archetype score | 9 | 43-45 | qualidade_dominante 40% novo + diversidade 40%→15% + floor 35 pra lock-in |

### Insight do Bruno (MP-1)
"Desvios de olhar não são todos negativos — olhar pra cima pensando é positivo." Implementado como classificação de tipo de desvio no _estimar_direcao_olhar().

### Bugs pendentes descobertos (não fixados)

| Bug | Dimensão | Problema | Evidência |
|-----|----------|----------|-----------|
| **MP-4b** | Postura | Threshold 0.025 muito alto — orador com desl_medio=0.019 fica "ansioso" | insta-5 (mentor): 64 vs LLMs 79 |
| **MP-6** | Opening | "Imagina a seguinte cena" não detectado como storytelling hook | insta-5 (mentor): 20 vs esperado 70-85 |
| **MP-7** | Variety | 100% monótono em orador que provavelmente varia | insta-5: 41, needs validation |
| **MP-5b** | Archetypes | Gap residual -32/-38 vs LLMs. Score ~45 pra lock-in vs LLMs ~77 | Estrutural — classificador acústico vs visual |

---

## 5. Cross-check completo — 3 vídeos testados

### WhatsApp 53s (orador estático, bust video)

| Dim | MP antes | MP depois | LLM avg | Gap v2 |
|-----|---------|-----------|---------|--------|
| Postura | 76 | 66 | 66 | +0.3 ✅ |
| Gestos | 68 | 85 | 67 | +18 (MP temporal > LLM visual) |
| Eye contact | 100% | 95.4% | — | ✅ realista |

### Insta-1 68s (orador energético, bust video)

| Dim | MP antes | MP depois | LLM avg | Gap v2 |
|-----|---------|-----------|---------|--------|
| Postura | 59 | 77 | 81 | -4 ✅ |
| Gestos | 29 | 29 | 81 | -52 (bust: mãos fora frame 73%) |
| Arquétipos | 9 | 43 | 81 | -38 (lock-in penalizado) |

### Insta-5 87s (vídeo do MENTOR — deveria ter nota alta)

| Dim | Pipeline | LLM avg | Gap | Status |
|-----|---------|---------|-----|--------|
| Opening | 20 | — | — | **BUG** |
| Variety | 41 | — | — | **Suspeito** |
| Archetypes | 45 | 77 | -32 | Estrutural |
| Postura | 64 | 79 | -15 | Threshold |
| Gestos | 69 | 79 | -10 | Parcial |
| Fillers | 100 | — | — | OK |
| Facial | 75 | — | — | OK |

**Conclusão:** pipeline subavalia orador expert. 4 de 8 dims abaixo do esperado.

---

## 6. Descoberta arquitetural — limitações do cross-check

### LLMs (frames) não medem voz/prosódia

O smoke test com frames validou apenas a **camada visual**. LLMs inferiram "voz" sem ouvir áudio — scores de voz/clareza são estimativas visuais, não medições.

### Pipeline real não envia vídeo pra LLM

O pipeline usa MediaPipe + Whisper LOCALMENTE. Gemini recebe só TEXTO (transcript + métricas). Cross-check visual (frames) não replica o pipeline real.

### Teste mais fidedigno (futuro)

Enviar o MESMO prompt textual (transcript + métricas dos workers) pros 3 LLMs. Mede convergência na INTERPRETAÇÃO, não na visão. Mais simples, mais fiel.

---

## 7. Decisão final — Vídeo de Referência do Mentor

Bruno decidiu: **pedir pro mentor gravar um vídeo 100%** (controlado, com intenção de ser referência).

### Spec do vídeo

| Critério | Valor |
|----------|-------|
| Duração | 1-3 minutos |
| Enquadramento | Meio corpo (cintura pra cima — mãos visíveis) |
| Áudio | Limpo, sem música/ruído |
| Abertura | 2+ técnicas (hook + pergunta, ou dado + história) |
| Voz | Varia tom (parte calma + parte enfática) |
| Gestos | Propositais, zona peito-cabeça, ambas mãos |
| Olhar | 80-90% câmera com desvios naturais |
| Edição | Raw (sem cortes) |

### Como será usado

1. Pipeline roda → baseline ideal (expected: 75-90 em tudo)
2. 3 LLMs rodam → cross-check
3. Gui avalia → ground truth humano (calibração zero da Story 7.7)
4. SE pipeline <70 em alguma dim → analyzer tem bug → fix com referência
5. SE pipeline 75-90 → calibrado → escala pra 10 vídeos

**Esse vídeo vira o "peso padrão" do projeto — calibration anchor.**

---

## 8. Commits desta sessão

| Commit | Descrição | Branch | PR |
|--------|-----------|--------|-----|
| 0314e2c | MVP harness convergência multi-IA (story 7.6) | feat/7.6-harness-7.7-ground-truth | #10 (MERGED) |
| 886b7f0 | Infra ground truth humano Gui Reginatto (story 7.7) | feat/7.6-harness-7.7-ground-truth | #10 (MERGED) |
| 8c570f5 | CodeRabbit feedback — 7 bugs harness + ground truth | feat/7.6-harness-7.7-ground-truth | #10 (MERGED) |
| 4689016 | Artefatos suporte execução 7.7 com Gui | docs/7.7-gui-support-artifacts | #14 (MERGED) |
| b8286f0 | Calibração MediaPipe — 5 bugs gesture + posture + archetype | feat/epic-8-scoring-workers | LOCAL (não pushado) |

---

## 9. Supabase Project Novo

| | |
|---|---|
| Nome | Oratoria APP |
| Ref | hkwjjbsjhpdpyypyubnu |
| URL | https://hkwjjbsjhpdpyypyubnu.supabase.co |
| Migrations | 001-011 aplicadas |
| ⚠️ Rotacionar | service_role + DB password (expostos em chat) |

---

## 10. Próximos passos (ordem de prioridade)

### Bloqueante — Vídeo de referência do mentor
- [ ] Bruno pede pro mentor gravar vídeo 100% (spec acima)
- [ ] Pipeline roda no vídeo → baseline
- [ ] 3 LLMs rodam → cross-check
- [ ] Fix bugs pendentes (MP-4b, MP-6, MP-7) usando vídeo como âncora

### Após calibração
- [ ] Push commit b8286f0 (5 fixes MediaPipe) — @devops
- [ ] Montar Google Sheet pra Gui (IMPORT-INSTRUCTIONS.md pronto)
- [ ] Call briefing com Gui (30min, script pronto)
- [ ] Calibração zero Fase 1A/1B com vídeo do mentor
- [ ] Selecionar 10 vídeos (Gui ~7 + Bruno ~3 NET)
- [ ] Rodar harness batch nos 10
- [ ] Gui avalia blind (3-4 sessões)
- [ ] Consolidação (compare-ground-truth.py)

### Tech debt documentado
- [ ] Harness modo texto (prompt do pipeline → 3 LLMs) — mais fiel que frames
- [ ] Dashboard /dev/convergence (Next.js) — deferido da Story 7.6
- [ ] Sentence-transformers pra top-3 concordance (Jaccard insuficiente)
- [ ] Opening analyzer: adicionar patterns "imagina", "pensa comigo", etc.
- [ ] Rotacionar credenciais Supabase (service_role + DB password)
- [ ] Archetype score filosofia: consistência vs diversidade (gap estrutural)

---

## 11. Métricas da sessão

| Métrica | Valor |
|---------|-------|
| PRs abertos | 2 (#10, #14) |
| PRs mergeados | 2 (#10, #14) |
| Commits | 5 (4 pushados + 1 local) |
| Arquivos criados/modificados | ~40 |
| LLM calls (smoke test) | 24 (6 vídeos × 3 modelos + 3 extras insta-5) |
| Custo estimado LLM | ~$5-7 |
| Bugs encontrados | 12 (7 CodeRabbit + 5 MediaPipe) |
| Bugs corrigidos | 12/12 |
| Migrations aplicadas | 11 (projeto novo do zero) |

---

— Sessão documentada por @dev Dex + @oalanicolas + @devops Gage + @qa Quinn
