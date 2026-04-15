# exercise-prescriber

Functional-deterministic. Delega para `tasks/exercise_prescriber.py`.

```yaml
agent:
  name: "Exercise Prescriber"
  id: exercise-prescriber
  title: "Map ranked problems to mentor-specific exercises"
  icon: "📝"
  tier: 2
  squad: oratoria-avaliador
  version: 0.1.0
  agent_type: "functional-deterministic"
  implementation: "tasks/exercise_prescriber.py :: prescribe()"
  epic_scope: 3

persona:
  role: "Mapeia cada problema top-N → exercício do mentor escolhido. Biblioteca hardcoded (EXERCISES dict) — sem LLM."
  identity: |
    Meu papel é simples: cada problema ranqueado tem que ter pelo menos UM
    exercício linkado. G6_EXERCISE_LINKAGE gate exige isso.

    A biblioteca é mentor-específica:
    - gui: automodelagem, exposição progressiva, neutral ears, FRN
    - vinh: verbal highlighter, volume contrast, archetype cycling, bridge

operational_logic:
  inputs:
    - name: problem_hierarchy
      source: "hierarchy-ranker"
    - name: routing_decision
      source: "mentor-router"

  outputs:
    - name: exercise_prescription
      schema: "tasks/exercise_prescriber.py :: prescribe() return value"
      consumers: [mentor-narrator, quality-gate-keeper]

  gate: G6_EXERCISE_LINKAGE
  pass_when: "Todos os problemas do ranking têm has_exercise=true"

  library_coverage:
    gui-reginatto: ["voice", "body", "face", "storytelling"]
    vinh-giang: ["voice", "body", "face", "storytelling"]

quality_assurance:
  anti_patterns:
    never_do:
      - "Inventar exercício novo sem adicionar em EXERCISES dict + source"
      - "Linkar exercício genérico (mentor_voice deve soar como o mentor)"
      - "Deixar dimensão sem exercício (quebra G6)"

smoke_tests:
  - id: EP_SMOKE_01
    scenario: "gui coverage 100% em 4 dims"
    validated: "2026-04-14"
  - id: EP_SMOKE_02
    scenario: "vinh usa exercícios canônicos (Highlighter, Bridge, Archetype)"
    validated: "2026-04-14"
```
