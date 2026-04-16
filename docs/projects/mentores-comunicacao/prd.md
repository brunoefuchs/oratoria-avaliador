# Mentores Comunicação — Product Requirements Document

## PRD Metadata

```yaml
prd_id: PRD-MENTORES-COMUNICACAO-001
title: "Mentores Comunicação — Squad Consultivo de Oratória Humana"
status: draft
priority: high
owner: squad-chief
created: 2026-04-15
updated: 2026-04-15
planning_mode: deep
source_of_truth: "docs/projects/mentores-comunicacao/prd.md"
reference_depth_source: null
```

---

## 1. Strategic Context

### 1.1 Problem

O ml-worker do Oratória Avaliador processa vídeos e gera relatório consolidado com 13 dimensões algorítmicas (posture, gesture, voice, fillers, variety, archetypes, facial, tonality, opening, identity + storytelling, temporal, congruence). Esse relatório mede o QUÊ — métricas computacionais — mas não interpreta o COMO oratório: presença, energia, intenção, autenticidade, musicalidade da fala.

O resultado é um "dashboard sem leitura": números sem tradução humana. O usuário recebe scores mas não sabe o que fazer com eles. Hoje, a camada de insight humano depende exclusivamente do mentor externo Guilherme Reginatto — throughput limitado, custo alto, não escalável.

### 1.2 Why Now

- Epic 8 (Truth Contract) está estabilizando o schema WorkerResult — contrato de I/O confiável pra consumir
- Story 7.7 (Ground Truth) está criando rubric humana calibrada pelo Gui — baseline de comparação
- Bruno já tem mind clones de Vinh Giang e Gui Reginatto no ecosystem — mas faltam lentes complementares (presença estrutural + técnica vocal)

### 1.3 Desired Outcomes

- Após relatório ml-worker, squad produz artefato consultivo com insights humanos complementares
- Cada insight rastreável a princípio documentado de oratória (não opinião solta)
- Squad flagra "pontos cegos" do ml-worker — o que algoritmo não pegou mas elite mind pegaria
- Bruno aprende oratória via squad (não só recebe nota)

### 1.4 Success from Not Building vs Building

| Scenario | Impact |
|----------|--------|
| If we do nothing | Oratória Avaliador vira "dashboard sem leitura" — scores sem ação. Dependência do mentor humano permanece. Feedback Raio-X do Mentor (10 fragilidades) sem resposta. |
| If we build this squad | Insight humano internalizado. Triangulação de 4 perspectivas (Vinh + Gui + Rodenburg + Roger Love). Quick wins acionáveis por vídeo. Bruno evolui como comunicador. |

---

## 2. Squad Thesis

### 2.1 Core Thesis

Complementar o pipeline ml-worker com uma camada consultiva baseada em princípios humanos de oratória — presença (Rodenburg) + técnica vocal (Roger Love) — produzindo insight qualitativo que scores numéricos não capturam. O squad NÃO substitui o ml-worker: consome seu relatório como input e agrega o que ele não vê.

### 2.2 What This Squad Is

- Camada consultiva pós-processamento (recebe relatório pronto, não processa vídeo)
- 2 mind clones de elite minds com frameworks documentados (Patsy Rodenburg + Roger Love)
- Orchestrator que sintetiza perspectivas e prioriza quick wins
- Ferramenta pedagógica (ensina o princípio por trás do feedback)

### 2.3 What This Squad Is Not

- NÃO é substituto do ml-worker (complementar)
- NÃO produz score numérico (insight qualitativo)
- NÃO analisa vídeo diretamente (analisa o RELATÓRIO do vídeo)
- NÃO cobre storytelling/narrativa (já coberto por Vinh Giang + Gui Reginatto existentes)
- NÃO é automação integrada (MVP manual via prompt)

### 2.4 Operating Modes

| Mode | Trigger | What happens | Human checkpoint |
|------|---------|--------------|------------------|
| Single-Shot Insight | Bruno paste relatório + pede análise | Chief dispatcha pros 2 mentores, sintetiza output | Bruno review final |
| Deep Dive Dimensional | Bruno pede foco em 1 dimensão (ex.: "só tonalidade") | 1 mentor especialista faz análise focada | Bruno review |
| Calibração Ground Truth | Comparar output squad vs output Gui (Story 7.7) | Diff e ajustes | Bruno + Gui review |

---

## 3. Users, Decisions, and Deliverables

### 3.1 Primary Users

| User | Job to be done | Pain today | Desired outcome |
|------|----------------|------------|-----------------|
| Bruno (dev solo / avaliador) | Após envio do vídeo e relatório ml-worker, pedir leitura consultiva + próximos passos | Números sem tradução, dependência de mentor externo | Insight humano estruturado com quick wins acionáveis |

### 3.2 Secondary Users

| User | Job to be done | Context |
|------|----------------|---------|
| Futuro usuário final (v1+) | Consumir insight humano como parte da UX | [assumption] Fora do MVP |
| Mentor Gui Reginatto | Calibrar squad via ground truth | Story 7.7, Google Sheets |

### 3.3 Key Decisions the Squad Must Support

| Decision | Inputs needed | Output produced | Risk if wrong |
|----------|---------------|-----------------|---------------|
| "Que círculo de presença este orador está?" | posture + gesture + facial + opening scores | Diagnóstico 1st/2nd/3rd Circle com evidência | Feedback de presença genérico/inútil |
| "Que ajuste vocal traz mais ROI?" | voice + tonality + variety + fillers scores + metrics | Top 1-3 exercícios de Roger Love priorizados | Lista genérica de 20 dicas sem prioridade |
| "O que os números não veem?" | Relatório completo 13 dimensões | Seção "pontos cegos" com insights qualitativos | Repetir o que ml-worker já disse (zero valor) |

### 3.4 Canonical Deliverables

| Artifact | Purpose | Format |
|----------|---------|--------|
| Artefato consultivo | Output principal do squad | Markdown com 6 seções estruturadas |
| Diagnóstico de presença | Perspectiva Rodenburg | Seção dentro do artefato |
| Análise vocal técnica | Perspectiva Roger Love | Seção dentro do artefato |
| Quick wins | Ações priorizadas | Lista ordenada com princípio pedagógico |

---

## 4. Squad Architecture

### 4.1 Agent Roster

| Agent ID | Type | Tier | Source Mind | Lente |
|----------|------|------|------------|-------|
| `mentores-comunicacao-chief` | Orchestrator | Orchestrator | — | Síntese + priorização |
| `patsy-rodenburg` | Mind Clone | Tier 1 | Patsy Rodenburg | Presença, energia, 3 Circles |
| `roger-love` | Mind Clone | Tier 1 | Roger Love | Técnica vocal, melodia, tom |

### 4.2 Agent Detail

#### mentores-comunicacao-chief (Orchestrator)

- **Role:** Receber relatório ml-worker, dispatchar pros mentores, sintetizar output final
- **Capabilities:** CAP-01 (interpretação), CAP-03 (priorização), CAP-05 (multi-perspectiva)
- **Input:** Relatório consolidado do ml-worker (13 dimensões + overall_score)
- **Output:** Artefato consultivo markdown com 6 seções
- **Handoff to:** patsy-rodenburg, roger-love

#### patsy-rodenburg (Mind Clone — Presença)

- **Role:** Diagnosticar presença e energia via 3 Circles of Presence
- **Capabilities:** CAP-02 (pontos cegos), CAP-04 (framing pedagógico)
- **ml-worker dimensions consumed:** posture, gesture, facial, opening, identity
- **Output:** Diagnóstico de circle + recomendações de presença
- **Framework:** Three Circles of Presence — First Circle (self-absorption), Second Circle (presence/connection), Third Circle (bluff/force)
- **Sources:** "Presence", "The Second Circle", "The Right to Speak", "The Actor Speaks", "Speaking Shakespeare"
- **Handoff to:** mentores-comunicacao-chief

#### roger-love (Mind Clone — Voz)

- **Role:** Analisar técnica vocal e recomendar exercícios concretos
- **Capabilities:** CAP-02 (pontos cegos), CAP-03 (quick wins), CAP-04 (framing pedagógico)
- **ml-worker dimensions consumed:** voice, tonality, variety, fillers
- **Output:** Análise vocal técnica + exercícios step-by-step
- **Framework:** 5 Ingredients of Vocal Power (melodia, tom, range/registro, respiração, emoção)
- **Sources:** "Set Your Voice Free", "Love Your Voice", "The Perfect Voice" course
- **Handoff to:** mentores-comunicacao-chief

### 4.3 Handoff Diagram

```
Bruno paste relatório
       │
       ▼
  [chief] ─── extrai dimensões relevantes
   │    │
   │    ├── posture/gesture/facial/opening/identity ──▶ [patsy-rodenburg]
   │    │                                                      │
   │    ├── voice/tonality/variety/fillers ────────────▶ [roger-love]
   │    │                                                      │
   │    ◀──────────── diagnóstico presença ────────────────────┘
   │    ◀──────────── análise vocal técnica ───────────────────┘
   │
   ▼
  [chief] sintetiza:
   1. Leitura consolidada em prosa
   2. Perspectiva Rodenburg (presença)
   3. Perspectiva Roger Love (voz)
   4. "O que os números não veem"
   5. Top 3 Quick Wins
   6. Princípios Pedagógicos
       │
       ▼
  Artefato consultivo → Bruno
```

---

## 5. Capabilities

| ID | Capability | Output | Why |
|----|-----------|--------|-----|
| CAP-01 | Interpretação Humana do Relatório ML | Leitura consolidada em prosa | ml-worker entrega números; humanos pensam em narrativa |
| CAP-02 | Identificação de Pontos Cegos | Seção "O que os números não veem" | Valor real: squad > ml-worker sozinho |
| CAP-03 | Priorização de Ganho Rápido | Top 3 quick wins acionáveis | Usuário precisa saber O QUE FAZER |
| CAP-04 | Framing Pedagógico | Princípio por trás de cada feedback | Bruno quer aprender, não só receber nota |
| CAP-05 | Multi-Perspectiva Complementar | N opiniões + síntese | Discordância entre mentores é sinal, não ruído |

---

## 6. I/O Contract

### 6.1 Input

```yaml
input:
  source: "ml-worker report_generator output"
  format: "Texto consolidado com 13 dimensões"
  schema: "WorkerResult (WorkerSuccess | WorkerFailure) por dimensão"
  dimensions_available:
    scoring: [posture, gesture, voice, fillers, variety, archetypes, facial, tonality, opening, identity]
    augmentation: [storytelling, temporal, congruence]
  injection: "Manual paste no prompt pelo Bruno"
```

### 6.2 Output

```yaml
output:
  format: "Markdown estruturado"
  sections:
    - "## Leitura Geral"
    - "## Presença & Energia (Patsy Rodenburg)"
    - "## Técnica Vocal (Roger Love)"
    - "## Pontos Cegos — O que os números não veem"
    - "## Top 3 Quick Wins"
    - "## Princípios Pedagógicos"
```

---

## 7. Non-Goals

- NÃO substituir ml-worker (complementar, não competir)
- NÃO produzir score numérico (insight qualitativo apenas)
- NÃO automatizar injeção do relatório (MVP é paste manual)
- NÃO cobrir storytelling/narrativa (Vinh Giang + Gui Reginatto existentes)
- NÃO analisar vídeo diretamente (analisa o RELATÓRIO do vídeo)
- NÃO treinar voice clones com material privado do Bruno (fontes públicas only)
- NÃO integrar com UI do produto (squad é prompt-based)

---

## 8. Risks

| Risk | Severity | Probability | Mitigation |
|------|----------|-------------|------------|
| Mentores alucinam feedback não rastreável a framework | High | Medium | immune_system no voice_dna + anti_patterns específicos |
| Squad só vê relatório texto, não vídeo — ponto cego real | Medium | High | 13 dimensões com metrics são ricos; v2 pode injectar vídeo |
| Overlap com Vinh/Gui nos clones existentes | Low | Low | Non-goals explícitos + lentes complementares |
| Relatório ml-worker muda schema (Epic 8 em andamento) | Medium | Medium | I/O contract ancorado em WorkerResult estável |
| Feedback genérico se voice_dna não capturar essência | High | Medium | Quality gates: 3 smoke tests + voice score 8/10 |

---

## 9. Mind Research Summary

### 9.1 Research Methodology

3 iterações de mind-research-loop com devil's advocate:
- Iteração 1: Broad research — 6 candidatos mapeados
- Iteração 2: Devil's advocate — cortou 4 (Nancy Duarte, Chris Anderson, Julian Treasure, Carmine Gallo)
- Iteração 3: Validation + complementarity matrix — confirmou 2

### 9.2 Selected Minds

| Mind | Framework | Score | Lente | Complementa |
|------|-----------|-------|-------|-------------|
| **Patsy Rodenburg** | Three Circles of Presence | 15/15 | Presença/energia/conexão | posture + gesture + facial (ml-worker) |
| **Roger Love** | 5 Ingredients of Vocal Power | 13/15 | Técnica vocal/melodia/tom | voice + tonality + variety + fillers (ml-worker) |

### 9.3 Rejected Minds (with rationale)

| Mind | Reason | Overlap Risk |
|------|--------|--------------|
| Nancy Duarte | Foco em slides, não oratória pura | Alto com Gui (storytelling) |
| Chris Anderson | Curador, não praticante. Framework genérico | — |
| Julian Treasure | Vocal toolbox sobrepõe Roger Love. HAIL é filosófico | Alto com Roger Love |
| Carmine Gallo | TED-style sobrepõe storytelling do Gui | Alto com Gui |

---

## 10. Execution Roadmap

### Phase 0 — Source Collection (30-60 min)

- `*auto-acquire-sources "Patsy Rodenburg" --domain oratória`
- `*auto-acquire-sources "Roger Love" --domain oratória`
- Gate: min 5 fontes primárias por mentor

### Phase 1 — Mind Cloning (2-3h, parallelizable)

- `*clone-mind "Patsy Rodenburg" --domain oratória --focus both`
- `*clone-mind "Roger Love" --domain oratória --focus both`
- Gate: Voice DNA 8/10 + Thinking DNA 7/9 mínimo

### Phase 2 — Agent Creation (1-2h)

- Create patsy-rodenburg.md (com mind DNA)
- Create roger-love.md (com mind DNA)
- Create mentores-comunicacao-chief.md (orchestrator)
- Gate: 3/3 smoke tests PASS por agent

### Phase 3 — Squad Assembly (30-60 min)

- Generate config.yaml
- Generate README.md
- `*sync` (IDE skills)

### Phase 4 — Validation (30 min)

- `*validate-squad mentores-comunicacao`
- Gate: Overall score >= 7.0

---

## 11. Dependencies

| Dependency | Status | Impact |
|-----------|--------|--------|
| WorkerResult schema (Epic 8 Story 8.1) | In Progress | I/O contract do squad depende de schema estável |
| Ground Truth Gui (Story 7.7) | Draft | Calibração futura do squad (WF-03) |
| Mind clones Vinh Giang + Gui Reginatto | Existentes | Non-goal: squad NÃO sobrepõe, complementa |

---

## 12. Open Questions

| # | Question | Decision Required By | Default Assumption |
|---|----------|---------------------|-------------------|
| Q3 | Squad produz 1 relatório consolidado ou N perspectivas paralelas? | Bruno | Consolidado com perspectivas internas (Section 4.3) |
| Q4 | Como relatório ml-worker é injetado? | Bruno | Manual paste no prompt |
| Q5 | "Ir além" dos mentores é mensurável? | Bruno | Triangulação das perspectivas = novel insight (não medido formalmente) |

---

## Appendix A — Planning Summary

```yaml
planning_summary:
  prd_id: PRD-MENTORES-COMUNICACAO-001
  domain: mentores-comunicacao
  planning_depth: deep
  phases_completed: 7/7
  minds_researched: 6
  minds_selected: 2
  minds_rejected: 4
  agents_planned: 3
  mind_clones_planned: 2
  workflows_planned: 3 (WF-01 Single-Shot, WF-02 Deep Dive, WF-03 Calibração)
  estimated_execution: "4-8 horas"
  risks_identified: 5
  non_goals: 7
  open_questions: 3
  next_command: "*create-squad mentores-comunicacao"
```
