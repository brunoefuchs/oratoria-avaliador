# mentor-router

Functional-deterministic agent. Delega para `tasks/mentor_router.py`. Decide qual mentor clone narra.

```yaml
agent:
  name: "Mentor Router"
  id: mentor-router
  title: "Route to correct mentor DNA (gui/vinh)"
  icon: "🔀"
  tier: 1
  squad: oratoria-avaliador
  version: 0.1.0
  agent_type: "functional-deterministic"
  implementation: "tasks/mentor_router.py :: route_mentor()"
  language: "pt-BR"
  epic_scope: 3

persona:
  role: "Decide qual mentor narra o relatório baseado em language + sinais do questionário 6.Q. Zero LLM. Rule-based puro."
  identity: |
    Sou o Mentor Router. Leio evaluation_context + user_profile e retorno:
    mentor escolhido, dna_paths, rationale, signals_analyzed.

    Regra canônica:
    - language en → vinh-giang
    - motivacao/desejo em GUI_KEYWORDS → gui-reginatto
    - default pt-BR → gui-reginatto (nativo)

operational_logic:
  rules:
    R1: "language=en → vinh-giang"
    R2: "motivacao hit em {vender_mais, redes_sociais, carreira, palestrar} OU desejo_melhorar hit em {autoridade} → gui"
    R3: "default pt-BR → gui"
  outputs_to: [mentor-narrator, exercise-prescriber]

quality_assurance:
  anti_patterns:
    never_do:
      - "Improvisar mentor novo sem adicionar em EXERCISES dict + DNA"
      - "Usar LLM para decidir mentor — é rule-based"

smoke_tests:
  - id: MR_SMOKE_01
    scenario: "default pt-BR → gui"
    validated: "2026-04-14"
  - id: MR_SMOKE_02
    scenario: "motivacao vender_mais → gui (2 hits)"
    validated: "2026-04-14"
  - id: MR_SMOKE_03
    scenario: "language=en → vinh"
    validated: "2026-04-14"
```
