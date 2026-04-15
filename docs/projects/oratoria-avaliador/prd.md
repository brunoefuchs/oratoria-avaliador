# Oratória Avaliador — Product Requirements Document

## PRD Metadata

```yaml
prd_id: PRD-ORATORIA-AVALIADOR-001
title: "Oratória Avaliador — Meta-Squad de Governança do Produto"
status: draft
priority: P0
owner: squad-chief
created: 2026-04-14
updated: 2026-04-14
planning_mode: deep
source_of_truth: "docs/projects/oratoria-avaliador/prd.md"
reference_depth_source: "docs/architecture/epic-6-architectural-spec.md"
```

---

## 1. Strategic Context

### 1.1 Problem

Oratória Avaliador já tem **espinha dorsal técnica** (ml-worker, scoring, relatório por dimensão) e **mentores clonados** (vinh-giang, gui-reginatto). Mas os pedaços operam como ilhas: os dados ML são gerados sem que a camada de interpretação humana seja garantida; o relatório sai sem quality gate de coerência; o produto tem duas teses de negócio (B2C individual + B2B empresa) que exigem narrativas distintas e ninguém orquestra isso.

O resultado: relatórios tecnicamente corretos que falham em **entregar o insight que o mentor entregaria** — e que é exatamente o que justifica o preço.

### 1.2 Why Now

- Epic 6 está **spec-complete** e introduz 5 features novas (6.Q, 6.1, 6.2, 6.8, 6.10) que cruzam ML + LLM + UX. Sem governança, cada feature vira um silo.
- **Feedback dos mentores (2026-04-09):** "dados já existem, falta inteligência + camada humana". O gap é orquestração, não captura.
- Epic 7 em execução (report UI, storytelling analyzer, facial, tonality VAD prosody) aumenta a superfície de dimensões — e o custo de inconsistência entre elas.
- Tese B2B (+10% comunicação → +10% lucro) exige **relatórios agregados por equipe**, que só existem se as dimensões individuais forem confiáveis primeiro.

### 1.3 Desired Outcomes

- **Pipeline governado:** cada avaliação passa por quality gates determinísticos antes de chegar ao usuário (coerência, completude, não-contradição entre dimensões).
- **Narrativa calibrada:** o relatório soa como um mentor (vinh/gui) falaria — não como output de modelo estatístico.
- **Escala dual:** o mesmo pipeline serve o usuário B2C (relatório pessoal) e B2B (dashboard de equipe) com ajuste mínimo de apresentação.

### 1.4 Success from Not Building vs Building

| Scenario | Impact |
|----------|--------|
| Se não construímos | Dimensões continuam se contradizendo (ex: voz = "monótona", storytelling = "emocionalmente rico"); mentor humano vira gargalo obrigatório; B2B é impossível de escalar |
| Se construímos | Pipeline end-to-end sem intervenção humana para 80% dos casos; mentor só entra nos 20% que exigem nuance; produto SaaS viabilizado |

---

## 2. Squad Thesis

### 2.1 Core Thesis

**Oratória Avaliador é um meta-squad de governança.** Ele não executa ML nem escreve narrativa do zero — ele **orquestra especialistas técnicos + mentores clonados + workers ML existentes** e **bloqueia** outputs que violam regras de coerência, completude ou fidelidade à metodologia dos mentores. A inteligência do produto está na orquestração, não na captura.

### 2.2 What This Squad Is

- Um **governador** que decide quando cada capability entra em cena e quando um output é aceitável.
- Um **bridge** entre o mundo ML (quantitativo, ml-worker Python) e o mundo mentor (qualitativo, DNA de vinh/gui).
- O **dono do quality gate** antes do usuário final receber o relatório.

### 2.3 What This Squad Is Not

- Não é um squad de ML workers (quem extrai features é `ml-worker/`, não este squad).
- Não é um mentor novo (os mentores vinh-giang/gui-reginatto já existem e continuam sendo fonte primária).
- Não é um squad de UI (o `apps/web/` já tem esqueleto de cards por dimensão).
- Não é um squad de data engineering (schema do Supabase é owned pelo @data-engineer).

### 2.4 Operating Modes

| Mode | Trigger | What happens | Human checkpoint |
|------|---------|--------------|------------------|
| **Evaluate** | Vídeo novo enviado, features ML extraídas | Orquestra scoring → congruência → narrativa → quality gate → entrega | Opcional (só em baixa confiança) |
| **Calibrate** | Mentor humano dá feedback divergente do relatório | Ajusta pesos contextuais, registra precedente, reprograma scoring | Obrigatório (mentor valida) |
| **Audit** | Solicitação B2B (relatório de equipe) ou investigação de outlier | Cruza N avaliações, detecta padrões, emite relatório agregado | Obrigatório (valida antes de exportar) |
| **Evolve** | Nova feature Epic (ex: 6.8 identity_analyzer) | Planeja integração, atualiza mapa de dimensões, revalida coerência | Obrigatório (@architect + Bruno) |

---

## 3. Users, Decisions, and Deliverables

### 3.1 Primary Users

| User | Job to be done | Pain today | Desired outcome |
|------|----------------|------------|-----------------|
| **Bruno (dev/founder)** | Governar a qualidade do produto sem virar gargalo manual | Revisa relatórios um-a-um para garantir coerência | Pipeline auto-governado; Bruno só revisa casos flagados |
| **Speaker B2C** | Receber feedback acionável sobre sua oratória | Relatórios técnicos sem "o que fazer" nem prioridade clara | Relatório narrativo com top-3 problemas em ordem de impacto + exercícios prescritos |
| **Coach/Empresa B2B** | Entender gaps de comunicação da equipe | Sem visão agregada; cada avaliação é ilha | Dashboard de equipe com ranking de dimensões + ROI estimado |
| **Mentor humano (opcional)** | Revisar apenas os casos onde o automatizado errou | Hoje revisa tudo ou nada | Fila priorizada por baixa confiança |

### 3.2 Key Decisions the Squad Must Support

| Decision | Inputs needed | Output produced | Risk if wrong |
|----------|---------------|-----------------|---------------|
| "Esse relatório pode ir para o usuário?" | Features ML + scores + narrativa + quality gate report | `PASS` / `FAIL` + razão | Produto entrega relatório inconsistente; usuário perde confiança |
| "Qual dimensão atacar primeiro?" | Scores por dimensão + contexto (questionário 6.Q) + hierarquia de problemas (6.2) | Top-3 ranqueado por impacto | Recomenda algo cosmético enquanto ignora root cause |
| "Qual voz de mentor usar?" | Perfil do usuário (desejo_transmitir, desejo_melhorar), language (pt-BR vs en) | `gui-reginatto` ou `vinh-giang` (ou híbrido) | Narrativa soa genérica; quebra o diferencial do produto |
| "Esse caso exige revisão humana?" | Confidence score do pipeline + outliers + contradições entre dimensões | Flag de escalation | Mentor vira gargalo ou usuário recebe relatório ruim |
| "Essa avaliação B2B agrega no relatório de equipe?" | Permissão, consistência temporal, scoring calibrado | Include/exclude | Dashboard B2B corrompido por outliers individuais |

### 3.3 Canonical Deliverables

| Artifact | Purpose | Format | Source of truth |
|----------|---------|--------|-----------------|
| `evaluation_report.json` | Relatório por dimensão entregue ao usuário | JSON estruturado por dimensão | `report_generator.py` output persistido em Supabase |
| `quality_gate_decision.json` | Log determinístico do gate que aprovou/bloqueou o relatório | JSON com evidências + rules disparadas | `oratoria-auditor` output |
| `problem_hierarchy.json` | Top-N problemas ranqueados com impacto estimado | JSON ordenado | `hierarchy-ranker` agent |
| `mentor_narrative.md` | Narrativa por dimensão na voz do mentor | Markdown com Voice DNA aplicado | `mentor-narrator` agent (consome `gui-reginatto` ou `vinh-giang`) |
| `team_report.json` (B2B) | Agregação de N avaliações para dashboard de equipe | JSON com médias, variâncias, outliers | `team-aggregator` agent |
| `evaluation_context.json` | Respostas do questionário 6.Q + pesos contextuais derivados | JSON | Supabase `evaluation_context` table |

---

## 4. Capability and Workflow Map

### 4.1 Capability Map

| Capability | Why it exists | Primary outputs | Dependencies |
|------------|---------------|-----------------|--------------|
| **C1. Feature Ingestion** | Receber outputs dos ML workers existentes (voz, corpo, face, storytelling) e consolidar em um contract estável | `features_canonical.json` | `ml-worker/workers/*` (already exists) |
| **C2. Contextual Scoring** | Aplicar pesos contextuais do questionário 6.Q a features brutas para produzir scores por dimensão | `scores_by_dimension.json` | C1, `evaluation_context` table |
| **C3. Cross-Dimension Congruence** | Detectar contradições entre dimensões (ex: voz monótona + storytelling rico) e resolver ou flagar | `congruence_report.json` | C2, Epic 5.7 congruence dimension |
| **C4. Problem Hierarchy** | Ranquear problemas por impacto usando 6.2 + hierarquia mentor | `problem_hierarchy.json` | C2, C3 |
| **C5. Mentor Narrative Generation** | Gerar narrativa na voz de vinh ou gui, respeitando Voice DNA | `mentor_narrative.md` | C4, minds/vinh_giang + minds/gui_reginatto |
| **C6. Quality Governance** | Aplicar quality gates determinísticos antes de release | `quality_gate_decision.json` | C1-C5 |
| **C7. Team Aggregation (B2B)** | Agregar N avaliações para relatório de equipe | `team_report.json` | C2, C6 |
| **C8. Calibration Loop** | Incorporar feedback de mentor humano em calibração contínua | Updated weights + precedents | C2, C6 |

### 4.2 Workflow Inventory

| # | Workflow | Category | Complexity | Automation Potential | Notes |
|---|----------|----------|------------|----------------------|-------|
| 1 | `wf-evaluate-pipeline` | Core | High | 95% | End-to-end de vídeo a relatório. Worker-heavy |
| 2 | `wf-quality-gate` | Core | Medium | 100% | Determinístico, rules-based |
| 3 | `wf-mentor-narrative` | Core | Medium | 80% | LLM com Voice DNA; revisão eventual |
| 4 | `wf-problem-hierarchy` | Core | Medium | 90% | Scoring + ranking |
| 5 | `wf-calibrate-weights` | Support | Low | 60% | Human-in-loop obrigatório |
| 6 | `wf-team-aggregate` | B2B | Medium | 85% | Requer múltiplas avaliações |
| 7 | `wf-audit-outlier` | Governance | High | 50% | Investiga inconsistências |
| 8 | `wf-evolve-dimension` | Meta | High | 40% | Integra nova feature Epic sem quebrar coerência |

### 4.3 Workflow Dependencies

```yaml
workflow_dependencies:
  wf-evaluate-pipeline:
    depends_on: [ml-worker/* output contract]
    enables: [wf-quality-gate, wf-mentor-narrative, wf-problem-hierarchy]
  wf-quality-gate:
    depends_on: [wf-evaluate-pipeline outputs]
    enables: [release to user]
  wf-mentor-narrative:
    depends_on: [wf-problem-hierarchy, minds/gui_reginatto, minds/vinh_giang]
    enables: [wf-quality-gate]
  wf-problem-hierarchy:
    depends_on: [wf-evaluate-pipeline, evaluation_context]
    enables: [wf-mentor-narrative]
  wf-calibrate-weights:
    depends_on: [mentor feedback input]
    enables: [wf-evaluate-pipeline (next run)]
  wf-team-aggregate:
    depends_on: [wf-quality-gate PASSED for N evaluations]
    enables: [B2B dashboard]
  wf-audit-outlier:
    depends_on: [wf-quality-gate FAIL or flagged]
    enables: [wf-calibrate-weights]
  wf-evolve-dimension:
    depends_on: [new Epic feature spec]
    enables: [updated wf-evaluate-pipeline]
```

### 4.4 Capability Gaps and Non-Goals

| Gap or Non-Goal | Why it remains out | Mitigation |
|-----------------|--------------------|------------|
| Training ML models from scratch | Squad `ml-worker/` já possui pipeline; foco aqui é governança | Consome outputs via contract |
| Authoring Voice DNA de novos mentores | `squad-creator-pro` já cuida de mind cloning | Reusa outputs existentes |
| UI/frontend dos cards | `apps/web/` já tem esqueleto; squad só define contrato JSON | Handoff para @ux-design-expert |
| Database migration | `@data-engineer` owns DDL | Define request → @data-engineer executa |
| Model hosting / inference | Infra de ml-worker | Consome endpoints existentes |

---

## 5. Knowledge Model and Canonical Artifacts

### 5.1 Core Concepts or Entities

| Concept | Definition | Why it matters | Canonical artifact |
|---------|------------|----------------|--------------------|
| **Avaliação (Evaluation)** | Uma análise completa de um vídeo enviado | Unidade atômica do produto | `evaluations` table (Supabase) |
| **Dimensão** | Eixo de análise (voz, corpo, face, storytelling, identidade, abertura, etc.) | Estrutura do relatório | `dimensions` enum + config |
| **Feature** | Métrica bruta extraída por um ML worker (ex: `filler_count`, `gaze_variance`) | Input determinístico para scoring | `ml-worker/*` outputs |
| **Score** | Feature + contexto → valor 0-100 por dimensão | O que o usuário vê | `scores_by_dimension.json` |
| **Evidence** | Trecho do vídeo + feature que justifica um score | Necessário para credibilidade | Timestamp + feature ref |
| **Congruence** | Grau de alinhamento entre dimensões | Detecta relatórios contraditórios | `congruence_report.json` |
| **Problem** | Item ranqueado na hierarquia do usuário | O que atacar primeiro | `problem_hierarchy.json` |
| **Exercise** | Prescrição acionável vinculada a um problema | Entrega de valor (não só diagnóstico) | Linked to problem + mentor DNA |
| **Mentor Voice** | DNA linguístico aplicado à narrativa | Diferencial competitivo | `minds/{vinh,gui}/voice_dna.yaml` |
| **Quality Gate Decision** | PASS/FAIL determinístico | O que decide release | `quality_gate_decision.json` |

### 5.2 Evidence and Assumption Model

```yaml
evidence_model:
  canonical_fact: "Schema Supabase definido em migration. Features ML extraídas por workers versionados."
  verified_fact: "Voice DNA de vinh/gui extraído com citation coverage ≥90% — smoke tests PASS."
  supported_inference: "Ranking de problemas via 6.2 reflete impacto real (a validar com mentor humano em calibração)."
  assumption: "+10% de comunicação → +10% lucro (tese B2B; precisa estudo próprio OU referência externa para defender)."
```

### 5.3 Canonical Artifacts

| Artifact | Owner | Lifecycle stage | Schema-first? | Required for execution? |
|----------|-------|-----------------|---------------|-------------------------|
| `features_canonical.json` | `oratoria-avaliador-chief` | Stable (contract) | YES | YES |
| `scores_by_dimension.json` | `scoring-engine` agent | Stable | YES | YES |
| `congruence_report.json` | `congruence-auditor` agent | Evolving | YES | YES |
| `problem_hierarchy.json` | `hierarchy-ranker` agent | Evolving | YES | YES |
| `mentor_narrative.md` | `mentor-narrator` agent | Evolving | NO (markdown) | YES |
| `quality_gate_decision.json` | `quality-gate-keeper` agent | Stable | YES | YES |
| `team_report.json` | `team-aggregator` agent | Evolving (B2B) | YES | B2B only |
| `calibration_precedents.yaml` | `calibration-keeper` agent | Append-only | YES | For evolve |

---

## 6. Agent Architecture

### 6.1 Orchestrator

```yaml
orchestrator:
  id: "oratoria-avaliador-chief"
  purpose: "Governar o pipeline end-to-end. Recebe evento 'vídeo pronto para avaliação', orquestra fases C1-C6, aplica quality gate, entrega ou escala para humano."
  routes:
    - "evaluate_video → wf-evaluate-pipeline"
    - "calibrate_feedback → wf-calibrate-weights"
    - "b2b_team_report → wf-team-aggregate"
    - "audit_outlier → wf-audit-outlier"
    - "evolve_dimension → wf-evolve-dimension"
```

### 6.2 Agents by Tier or Function

```yaml
agents:
  tier_0_governance:
    - id: "quality-gate-keeper"
      purpose: "Aplica rules determinísticas. Único que decide PASS/FAIL para release."
      workflows: [wf-quality-gate]
    - id: "congruence-auditor"
      purpose: "Detecta contradições entre dimensões. Bloqueia release se contradição crítica."
      workflows: [wf-quality-gate]

  tier_1_technical_state_of_art:
    - id: "speech-prosody-expert"
      purpose: "Interpreta features de voz (VAD, prosódia, filler) com base em estado da arte (Praat, pyAudioAnalysis, OpenSMILE)."
      workflows: [wf-evaluate-pipeline]
    - id: "face-gesture-expert"
      purpose: "Interpreta features faciais (FACS/AU) e de gesto (MediaPipe pose) com literatura atual."
      workflows: [wf-evaluate-pipeline]
    - id: "narrative-structure-expert"
      purpose: "Aplica estado da arte em storytelling computacional (Dan Harmon circle, Freytag pyramid, emotional arcs Reagan et al)."
      workflows: [wf-evaluate-pipeline]
    - id: "psychometry-calibrator"
      purpose: "Calibração estatística dos scores (IRT, Cronbach's alpha) + detecção de viés."
      workflows: [wf-evaluate-pipeline, wf-calibrate-weights]
    - id: "scoring-engine"
      purpose: "Agrega features com pesos contextuais (questionário 6.Q) para gerar scores por dimensão."
      workflows: [wf-evaluate-pipeline]

  tier_1_mentor_layer:
    - id: "mentor-router"
      purpose: "Decide qual mentor (gui/vinh/híbrido) narra, baseado em perfil do usuário e language."
      workflows: [wf-mentor-narrative]
    - id: "mentor-narrator"
      purpose: "Gera narrativa por dimensão aplicando Voice DNA do mentor escolhido. Consome DNA existente."
      workflows: [wf-mentor-narrative]

  tier_2_derivative:
    - id: "hierarchy-ranker"
      purpose: "Ranqueia problemas por impacto estimado (Epic 6.2)."
      workflows: [wf-problem-hierarchy]
    - id: "exercise-prescriber"
      purpose: "Mapeia problema ranqueado → exercício prescrito do mentor."
      workflows: [wf-mentor-narrative]
    - id: "team-aggregator"
      purpose: "Agrega N avaliações em relatório B2B. Só entra se quality-gate PASS em todas."
      workflows: [wf-team-aggregate]
    - id: "calibration-keeper"
      purpose: "Registra precedentes de calibração em append-only log. Garante reprodutibilidade."
      workflows: [wf-calibrate-weights]
```

### 6.3 Handoff Map

| From | To | Trigger | Context passed | Exit condition |
|------|----|---------|----------------|----------------|
| `ml-worker/*` (external) | `oratoria-avaliador-chief` | Evento "features ready" | `features_canonical.json` | Contract validation PASS |
| `chief` | `speech-prosody-expert` | Fase C1→C2 iniciada | voice features + context | Scores de voz emitidos |
| `chief` | `face-gesture-expert` | Paralelo com speech | face/pose features + context | Scores visuais emitidos |
| `chief` | `narrative-structure-expert` | Após transcrição | transcript + timestamps | Score narrativo |
| Experts técnicos | `scoring-engine` | Todos emitiram | scores brutos | Scores ponderados |
| `scoring-engine` | `congruence-auditor` | Scores ponderados | scores + features | Congruence report |
| `congruence-auditor` | `hierarchy-ranker` | Congruência OK ou flagada | scores + congruence | Ranking de problemas |
| `hierarchy-ranker` | `mentor-router` | Ranking pronto | ranking + user profile | Mentor escolhido |
| `mentor-router` | `mentor-narrator` | Decisão tomada | mentor + ranking | Narrativa gerada |
| `mentor-narrator` | `exercise-prescriber` | Narrativa pronta | narrative + ranking | Exercícios linkados |
| Todos | `quality-gate-keeper` | Artefatos completos | Todos os JSON | PASS → release, FAIL → audit |
| `quality-gate-keeper` | `audit-outlier` (skill do chief) | FAIL | decision + evidences | Audit report |

### 6.4 Workflow Coverage Matrix

| Workflow | Primary agent | Support agent | Quality gate |
|----------|---------------|---------------|--------------|
| wf-evaluate-pipeline | `oratoria-avaliador-chief` | speech/face/narrative experts + scoring-engine | quality-gate-keeper |
| wf-quality-gate | `quality-gate-keeper` | congruence-auditor | N/A (é o próprio gate) |
| wf-mentor-narrative | `mentor-narrator` | mentor-router, exercise-prescriber | Voice DNA fidelity check |
| wf-problem-hierarchy | `hierarchy-ranker` | congruence-auditor | Top-N validity check |
| wf-calibrate-weights | `calibration-keeper` | psychometry-calibrator | Human-in-loop signoff |
| wf-team-aggregate | `team-aggregator` | quality-gate-keeper | Aggregation integrity |
| wf-audit-outlier | `oratoria-avaliador-chief` | congruence-auditor, psychometry-calibrator | Root cause assignment |
| wf-evolve-dimension | `oratoria-avaliador-chief` | @architect (external) | Backward compat PASS |

---

## 7. Tooling, Automation, and Boundaries

### 7.1 Tooling Strategy

| Need | Tool or pattern | Why selected | Human fallback |
|------|------------------|--------------|----------------|
| Feature extraction (speech) | Existing `ml-worker/workers/*.py` (Praat/pyAudioAnalysis/OpenSMILE) | Já implementado, estado da arte | N/A (sempre roda) |
| Feature extraction (face/pose) | MediaPipe + FACS Action Units | Padrão em HCI research | N/A |
| LLM narrativa | OpenAI / Claude com prompt + Voice DNA injection | Já usado em report_generator.py | Revisão mentor |
| Data persistence | Supabase (Postgres + RLS) | Stack atual; schema já definido | N/A |
| Orchestration runtime | Python async (ml-worker) + Next.js API routes | Stack atual | N/A |
| Scoring calibration | Python (scipy/sklearn para IRT/Cronbach) | Padrão psicometria | Mentor calibration |
| Quality gate rules engine | Pure Python rules (deterministic) | Auditável, testável, versionável | Bruno revisa no dashboard |

### 7.2 Worker vs Agent Boundaries

| Operation | Preferred executor | Reason |
|-----------|--------------------|--------|
| Feature extraction de vídeo | Worker (ml-worker Python) | Determinístico, custo, velocidade |
| Scoring com pesos contextuais | Worker (Python) | Rules determinísticas |
| Congruence check | Worker (Python) | Rules + thresholds |
| Quality gate rules | Worker (Python) | Deterministic; deve ser auditável |
| Problem hierarchy ranking | Worker (Python) com regras + LLM só para tie-break | Escalável |
| Mentor narrative generation | Agent (LLM com Voice DNA) | Exige nuance linguística |
| Mentor routing | Worker (rules simples) | Decisão binária/trinária; não precisa LLM |
| Calibration loop | Agent (human-in-loop) | Exige julgamento |
| Team aggregation | Worker (Python + SQL) | Estatística pura |
| Audit outlier | Agent (LLM + Python tools) | Exige investigação contextual |

### 7.3 External Integrations and Constraints

| Integration | Status | Constraint | Risk |
|-------------|--------|------------|------|
| Supabase | Active | RLS policies protegem dados por user_id | Vazamento cross-tenant se policy errada |
| OpenAI / Claude API | Active | Rate limit + custo por token | Custo cresce linear com volume; cache importante |
| ml-worker (internal) | Active | Contract de output precisa versionar | Breaking change derruba pipeline |
| MediaPipe | Active | CPU-bound; ~2x realtime | Gargalo em volume alto |
| Next.js frontend | Active | SSR + tsconfig compartilhado | Types dessincronizados entre web e worker |

---

## 8. Governance, Quality, and Failure Modes

### 8.1 Quality Gates

| Gate | Trigger | What must be true | Blocking? |
|------|---------|-------------------|-----------|
| **G1. Contract validity** | Entrada de features | JSON schema válido; campos obrigatórios presentes | YES |
| **G2. Completude** | Antes de scoring | Todas as dimensões esperadas têm features | YES |
| **G3. Congruence** | Após scoring | Sem contradições críticas entre dimensões | YES (FAIL → audit) |
| **G4. Voice DNA fidelity** | Narrativa gerada | Signature phrases + tom registers dentro do range | YES (re-generate se FAIL) |
| **G5. Hierarchy validity** | Ranking gerado | Top-N não contradiz scores; evidences linkadas | YES |
| **G6. Exercise linkage** | Exercícios prescritos | Cada top-3 problema tem ≥1 exercício | YES |
| **G7. Calibration audit trail** | Calibração | Cada mudança de peso tem precedent + mentor signoff | YES |
| **G8. B2B aggregation integrity** | Team report | Todas as N avaliações são G1-G7 PASS | YES |

### 8.2 Human Checkpoints

| Checkpoint | When | Decision required |
|------------|------|-------------------|
| HC1. Low-confidence flag | Pipeline detecta baixa confiança em ≥1 dimensão | Release, escalate mentor, ou re-analyze |
| HC2. Calibration signoff | Mentor propõe ajuste de peso | Aceitar? rejeitar? (Bruno ou mentor) |
| HC3. B2B export approval | Antes de enviar team report a cliente B2B | Bruno valida agregação |
| HC4. Evolve dimension approval | Nova feature Epic integrada | @architect + Bruno validam |

### 8.3 Anti-Patterns and Veto Conditions

| Anti-Pattern | Why blocked | Detection |
|--------------|-------------|-----------|
| Entregar relatório com contradição entre dimensões | Quebra confiança; mentor nunca faria isso | G3 congruence FAIL |
| Gerar narrativa sem Voice DNA do mentor escolhido | Perde diferencial competitivo | G4 fidelity FAIL |
| Ranquear problemas sem evidence | Vira opinião, não diagnóstico | G5 evidence check |
| Prescrever exercício sem link a problema | Exercício desconectado não gera adesão | G6 linkage check |
| Agregar B2B com avaliação que não passou gate | Corrompe dashboard | G8 aggregation |
| Calibrar peso sem precedent log | Quebra auditabilidade | G7 audit trail |
| Pular camada mentor (só dados crus) | Produto vira ML report genérico | Orchestrator enforcement |
| Usar ml-worker como owner de lógica de negócio | Viola separação; ml-worker é capture-only | Architecture review |

### 8.4 Failure Modes

| Failure mode | Signal | Mitigation | Rollback |
|--------------|--------|------------|----------|
| ml-worker output schema breaks | G1 FAIL | Versionar contract; feature flag | Roll back worker version |
| LLM provider outage | Narrativa timeout | Fallback para template + flag "narrativa limitada" | User retry |
| Voice DNA drift | G4 repeated FAILs | Re-run smoke tests em vinh/gui | Revert mind files |
| Scoring calibration viés | Mentor feedback divergente sistemático | wf-calibrate-weights + mentor signoff | Restore previous weights |
| Cross-tenant B2B leak | RLS policy falha | Fail-closed em agregação | Block export, audit RLS |
| Congruence false positive (bloqueia avaliações boas) | Taxa de FAIL > threshold | Ajustar thresholds via calibration | Lower threshold emergencialmente |
| Custo LLM explode | Gasto diário acima de orçamento | Cache por user + downsample narrativa | Throttle + alert |

---

## 9. Challenge, Alternatives, and Sequencing

### 9.1 Alternatives Considered

| Option | What changes | Upside | Downside | Verdict |
|--------|--------------|--------|----------|---------|
| **A. Expandir vinh/gui agents para cobrir tudo** | Sem meta-squad; agents existentes fazem governança inline | Menos estrutura nova | Bloat nos agents; perde separation of concerns; não escala para B2B; violação de single responsibility | REJECTED |
| **B. Squad puramente técnico (sem camada mentor)** | Só orquestra ML + scoring; relatório genérico | Mais simples; menor superfície | Perde diferencial; feedback mentor "falta camada humana" sinaliza que isso não vende | REJECTED |
| **C. Meta-squad de governança (ESCOLHIDA)** | Squad coordena ML (existente) + mentor DNA (existente) + gera narrativa governada + quality gate | Escalável; reusa investimento; alinhado com feedback mentor | Mais complexo para implementar v1; exige contract discipline | **CHOSEN** |
| **D. Terceirizar quality gate ao mentor humano** | Mentor humano revisa 100% | Máxima qualidade | Não escala; contradiz tese de produto B2C | REJECTED |
| **E. Pipeline serverless event-driven (architecture-first)** | Redesenhar stack; S3/Kinesis/Lambda | Escalabilidade teórica | Projeto em andamento; desperdiça stack atual | DEFER (fora de escopo v1) |

### 9.2 Dependency Stress Test

```yaml
dependency_stress_test:
  critical_path:
    - "ml-worker contract stability (G1)"
    - "scoring-engine (C2) com pesos contextuais 6.Q"
    - "congruence-auditor (C3)"
    - "mentor-narrator com Voice DNA injection (C5)"
    - "quality-gate-keeper (C6)"

  premature_items:
    - item: "team-aggregator (B2B)"
      why_premature: "Depende de G1-G7 estáveis em volume; não faz sentido antes do pipeline individual estar confiável"
      move_after: ["wf-evaluate-pipeline estável + 100+ avaliações com gate PASS"]
    - item: "psychometry-calibrator IRT completo"
      why_premature: "Exige dataset grande para IRT; em v1 rules-based + Cronbach já bastam"
      move_after: ["Dataset ≥ 500 avaliações calibradas"]

  blocked_items:
    - item: "wf-evolve-dimension (Epic 7 features)"
      blocked_by: ["wf-evaluate-pipeline v1 estável"]
      why_not_pull_blocker_forward: "Evoluir dimensão antes do pipeline estar estável = mover chão enquanto anda"

  not_before_conditions:
    - item: "Epic 1 (foundation contract)"
      requires: ["Inventário de features atuais ml-worker"]
    - item: "Epic 2 (scoring + congruence)"
      requires: ["Epic 1 + questionário 6.Q implementado (já em spec)"]
    - item: "Epic 3 (mentor narrative + exercise)"
      requires: ["Epic 2 + Voice DNA de vinh/gui validado (já PASS)"]
    - item: "Epic 4 (quality gate + calibration)"
      requires: ["Epic 3"]
    - item: "Epic 5 (B2B team aggregation)"
      requires: ["Epic 4 + 100+ avaliações PASS em produção"]
```

### 9.3 Why This Order

- **Contract primeiro** porque tudo a jusante depende dele. Quebrar contract é quebrar tudo.
- **Scoring + congruence antes de narrativa** porque sem scores confiáveis a narrativa fica bonita mas errada — o erro vira invisível ao usuário.
- **Narrativa antes do gate final** porque o gate precisa avaliar o artefato completo (inclui narrativa), não só os números.
- **Gate antes de B2B** porque B2B amplifica erros: 1 relatório ruim vira 10 relatórios ruins na média do time.
- **Calibração só depois do gate** porque calibração sem gate é feedback perdido (sem referência de "passou ou não").

### 9.4 Rejected Paths and Feedback Log

| Feedback or challenge | What reopened | Final decision | Why |
|-----------------------|---------------|----------------|-----|
| "Por que não expandir gui/vinh?" | Agent scope | Rejected opção A | Violaria single responsibility; gui/vinh são mentor DNA puros, não orquestradores |
| "Por que DEEP planning se já tem Epic 6 spec?" | Depth calibration | Mantido DEEP | Epic 6 é tática (5 features); este PRD é estratégico (meta-squad + roadmap 5 epics) |
| "Squad data foi referência — por que não incorporar agents dela?" | Reference application | Referência aplicada como inspiração técnica (Kaushik/Fader em scoring/psicometria), não como agents diretos | Agents de data squad são business analytics, não speech/HCI |
| "Por que não adotar pipeline event-driven (option E)?" | Architecture | Deferred | Rewrite do runtime é fora de escopo v1; incremental primeiro |

---

## 10. Roadmap

### 10.1 Epic Overview

| Epic | Goal | Agents delivered | Workflows enabled | Dependencies |
|------|------|------------------|-------------------|--------------|
| 1 | Foundation + Contract | `oratoria-avaliador-chief`, feature ingestion contract | `wf-evaluate-pipeline` (stub) | ml-worker inventory |
| 2 | Scoring + Congruence | `scoring-engine`, `congruence-auditor`, `speech-prosody-expert`, `face-gesture-expert`, `narrative-structure-expert`, `psychometry-calibrator` | `wf-evaluate-pipeline` (scoring), `wf-problem-hierarchy` | Epic 1 + questionário 6.Q live |
| 3 | Mentor Narrative | `mentor-router`, `mentor-narrator`, `exercise-prescriber`, `hierarchy-ranker` | `wf-mentor-narrative` | Epic 2 + DNA vinh/gui validado |
| 4 | Quality Gate + Calibration | `quality-gate-keeper`, `calibration-keeper` | `wf-quality-gate`, `wf-calibrate-weights`, `wf-audit-outlier` | Epic 3 |
| 5 | B2B Aggregation | `team-aggregator` | `wf-team-aggregate` | Epic 4 + 100+ avaliações PASS |
| 6 | Evolve Dimensions | (nenhum novo; upgrade de chief) | `wf-evolve-dimension` | Epic 4 |

### 10.2 Epic Details

#### Epic 1: Foundation + Contract

**Goal:** Orchestrator mínimo + contract de features estável. Pipeline stub end-to-end.

**Not Before:** Inventário ml-worker completo.

**Stories:**

| Story | Purpose | Acceptance summary | Gate |
|-------|---------|--------------------|------|
| 1.1 | Criar agent `oratoria-avaliador-chief` | Agent passa smoke test; routes 5 workflows | G-agent-quality |
| 1.2 | Definir `features_canonical.json` schema | Schema JSON válido; cobre todos workers atuais | G1 |
| 1.3 | Implementar adapter ml-worker → chief | Roundtrip features OK | G1 |
| 1.4 | Stub `wf-evaluate-pipeline` | Workflow yaml valida em `validate-squad` | workflow-compliance |

**Definition of Done:**
- [ ] Squad `oratoria-avaliador` aparece em squad-registry
- [ ] Chief agent passa smoke tests
- [ ] Contract validado em 1 vídeo real
- [ ] Nenhum breaking change em ml-worker

#### Epic 2: Scoring + Congruence

**Goal:** Pipeline emite scores por dimensão + detecta contradições.

**Not Before:** Epic 1 done. Questionário 6.Q implementado.

**Stories:**

| Story | Purpose | Acceptance summary | Gate |
|-------|---------|--------------------|------|
| 2.1 | `scoring-engine` aplica pesos contextuais 6.Q | Score varia conforme questionário | G2 |
| 2.2 | Experts técnicos (speech, face, narrative) | Cada um interpreta features com citation de literatura | agent-quality |
| 2.3 | `congruence-auditor` detecta contradições | 5 casos teste: 3 contradição, 2 OK | G3 |
| 2.4 | `psychometry-calibrator` v1 (Cronbach) | Reporta alpha por dimensão | — |

**DoD:**
- [ ] Scores mudam de forma esperada conforme questionário
- [ ] Congruência bloqueia ≥3 casos sintéticos
- [ ] Alpha reportado em 10 avaliações

#### Epic 3: Mentor Narrative

**Goal:** Relatório narrativo na voz de gui ou vinh, com exercícios prescritos.

**Not Before:** Epic 2 done. DNA validado (já PASS hoje).

**Stories:**

| Story | Purpose | AC | Gate |
|-------|---------|----|----|
| 3.1 | `mentor-router` decide gui vs vinh | Regra: pt-BR + vendas/identidade → gui; en + vocal/palco → vinh | — |
| 3.2 | `mentor-narrator` gera narrativa | Voice DNA fidelity ≥85% | G4 |
| 3.3 | `hierarchy-ranker` top-3 problemas | Ranking com evidences | G5 |
| 3.4 | `exercise-prescriber` linka exercício | Top-3 tem ≥1 exercício cada | G6 |

**DoD:**
- [ ] Relatório em pt-BR (gui) e en (vinh) gerados em teste
- [ ] Voice DNA fidelity medido em ≥10 relatórios

#### Epic 4: Quality Gate + Calibration

**Goal:** Release governado. Feedback mentor incorporado sistematicamente.

**Not Before:** Epic 3 done.

**Stories:**

| Story | Purpose | AC | Gate |
|-------|---------|----|----|
| 4.1 | `quality-gate-keeper` aplica G1-G6 | PASS/FAIL determinístico; razão por regra | — |
| 4.2 | Dashboard de gate decisions | Bruno vê FAILs e motivos | — |
| 4.3 | `calibration-keeper` append-only log | Cada mudança de peso com precedent | G7 |
| 4.4 | `wf-audit-outlier` | Audit em FAIL gera action item | — |

**DoD:**
- [ ] 100% dos releases passam por gate
- [ ] Dashboard mostra taxa PASS/FAIL + razões top
- [ ] Mentor dá signoff em 3 calibrações reais

#### Epic 5: B2B Team Aggregation

**Goal:** Dashboard de equipe para cliente B2B.

**Not Before:** Epic 4 done + 100+ avaliações G-PASS.

**Stories:**

| Story | Purpose | AC | Gate |
|-------|---------|----|----|
| 5.1 | `team-aggregator` gera JSON | Médias, variâncias, outliers por dimensão | G8 |
| 5.2 | UI B2B dashboard | Visualização agregada (separado de B2C) | — |
| 5.3 | Export PDF relatório de equipe | Assinado + watermark | — |
| 5.4 | Tese ROI (+10% comunicação → +10% lucro) | Fonte citada ou estudo próprio | evidence check |

**DoD:**
- [ ] 1 cliente B2B piloto recebe relatório
- [ ] Tese de ROI defensível (não inventada)

#### Epic 6: Evolve Dimensions

**Goal:** Integrar novas dimensões (Epic 7 e além) sem quebrar pipeline.

**Not Before:** Epic 4 done.

**Stories:**

| Story | Purpose | AC | Gate |
|-------|---------|----|----|
| 6.1 | `wf-evolve-dimension` procedimento | Playbook para adicionar dimensão nova | — |
| 6.2 | Backward compat test | Novo relatório ainda passa G1-G6 | all gates |
| 6.3 | Integrar Epic 7 features (tonality VAD, facial, storytelling novos) | Cada uma passa por playbook | — |

**DoD:**
- [ ] ≥1 feature Epic 7 integrada via playbook sem breaking change

### 10.3 Story Slicing Rules

- Uma story entrega UM agent OU UM workflow novo, nunca os dois.
- Toda story que cria workflow precisa AC de `validate-squad` PASS.
- Toda story que cria agent precisa 3 smoke tests PASS.
- Stories de contract change (G1) exigem revisão @architect antes de merge.

### 10.4 Workflow Compliance (Mandatory)

**Mandatory ACs para qualquer story que cria workflow:**

| AC | Reason |
|----|--------|
| Workflow usa `workflow.sequence[]` como contract | Dashboard rendering + CI validation |
| Workflow inclui `workflow.type` | Classificação automática |
| Agent names sem `@` prefix | Filenames consistentes |
| `handoff_prompts` definidos em transições | Contexto entre agents |
| `validate-squad` PASSES após criação | Integrity gate final |

---

## 11. Metrics and Readiness

### 11.1 Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Quality gate PASS rate | ≥85% em 3 meses | `quality_gate_decision` logs |
| Voice DNA fidelity médio | ≥85% | Automated fidelity check por relatório |
| Congruence FAIL rate | ≤10% | `congruence_report` logs |
| Mentor override rate (humano discorda) | ≤15% | Calibration log |
| Tempo vídeo → relatório (p95) | ≤10 min | Pipeline telemetry |
| Custo LLM por avaliação | ≤ $0.50 | API usage |
| NPS usuário B2C | ≥50 | Survey pós-relatório |
| B2B piloto: ROI estimado defensável | ≥1 estudo/referência citada | Appendix evidence |

### 11.2 Execution Readiness Checklist

- [x] Problem e outcomes explícitos
- [x] Workflow inventory completo para Epic 1-3
- [x] Agent architecture defensável (alternativas rejeitadas com motivo)
- [x] Governance e checkpoints definidos
- [x] ≥1 alternativa rejeitada com rationale (A, B, D, E)
- [x] Critical path e not-before stressed-tested
- [x] Epic 1 pronto para começar

---

## 12. Risks, Assumptions, and Open Questions

### 12.1 Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Voice DNA drift após Epic 6 mudanças em gui/vinh | High | Medium | Smoke test automatizado em cada mentor a cada merge |
| Contract ml-worker break em Epic 7 | High | Medium | Versionar contract; feature flag + test harness |
| Custo LLM explode com volume | Medium | Medium | Cache por user; downsample narrativa se token > budget |
| Bruno vira gargalo em calibração | Medium | Medium | Delegar primeiros casos via automação conservadora |
| Congruence com muito falso positivo | Medium | High | Thresholds ajustáveis; calibração semanal em v1 |
| B2B tese "+10% lucro" não defensável | High | Medium | Epic 5.4 exige evidence; se não encontrar, muda pitch |
| Cross-tenant leak (RLS) | Critical | Low | RLS tests automatizados + fail-closed em agregação |

### 12.2 Assumptions

- ml-worker continua sendo executor de captura (não vai migrar para outro runtime no horizonte v1).
- Voice DNA de gui/vinh continua válido (smoke tests PASS).
- Questionário 6.Q estará live antes do Epic 2.
- Supabase RLS policies estão corretas (responsabilidade @data-engineer).
- Stack Next.js + Python + Supabase não vai ser rewrite em 2026.

### 12.3 Open Questions

- [ ] Tese "+10% comunicação → +10% lucro" tem referência externa defensável, ou precisa estudo próprio em Epic 5?
- [ ] B2B é prioridade antes ou depois de fechar 100 avaliações B2C estáveis?
- [ ] Mentor humano no loop de calibração é Bruno, ou contratamos mentor externo?
- [ ] Voice DNA drift: qual periodicidade de smoke test em produção (semanal? por release)?
- [ ] Se novo mentor entrar no futuro (ex: inglês corporativo), squad suporta plug-and-play ou precisa Epic?

---

## 13. Handoff to Execution

### Next Command

```text
*create-squad oratoria-avaliador
```

### Required Context for Execution

- `docs/projects/oratoria-avaliador/prd.md` (este documento)
- Epic 1 scope e stories clarificadas (seção 10.2)
- `docs/architecture/epic-6-architectural-spec.md` (contexto técnico atual)
- `squads/squad-creator-pro/minds/{vinh_giang,gui_reginatto}/` (mentor DNA existente)
- `ml-worker/workers/` (inventário de features a contratualizar)

---

## Appendix A: Source Inventory

| Source | Type | Why used |
|--------|------|----------|
| `docs/architecture/epic-6-architectural-spec.md` | Internal spec | Define 5 features já decididas que o squad precisa orquestrar |
| `squads/squad-creator-pro/agents/vinh-giang.md` | Existing agent | Mentor clone (en, vocal/performance) — camada narrativa |
| `squads/squad-creator-pro/agents/gui-reginatto.md` | Existing agent | Mentor clone (pt-BR, identidade/vendas) — camada narrativa |
| `ml-worker/workers/*.py` | Existing code | Fonte de features brutas; contract base |
| `apps/web/src/app/report/*` | Existing UI | Consumer final do relatório JSON |
| `squads/data/agents/*` | Reference | Inspiração técnica (Fader psicometria, Kaushik métricas) — não agents diretos |
| Memory: "Feedback Vinh + Gui (2026-04-09)" | User memory | "Dados já existem, falta inteligência + camada humana" — base da tese meta-squad |
| State of the art literature | External reference | Praat/OpenSMILE/MediaPipe/FACS para technical experts |

## Appendix B: Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2026-04-14 | 1.0.0 | Initial deep PRD (modo DEEP) | @squad-chief |

## Appendix C: Planning Summary

```yaml
planning_summary:
  workflows_mapped: 8
  agents_estimated: 13
  epics_planned: 6
  alternatives_compared: 5
  alternatives_rejected: 4
  feedback_reopen_events: 1
  handoff_ready: yes
  depth_class: DEEP
  critical_path_length: 5
  blocking_not_before_conditions: 5
  open_questions: 5
```
