# mentor-narrator

Hybrid agent: prompt-builder determinístico + LLM caller opcional. Delega para `tasks/mentor_narrator.py`.

```yaml
agent:
  name: "Mentor Narrator"
  id: mentor-narrator
  title: "Generate narrative in mentor voice (Voice DNA injected)"
  icon: "🎙️"
  tier: 1
  squad: oratoria-avaliador
  version: 0.1.0
  agent_type: "hybrid"  # prompt-build determinístico + LLM opcional
  implementation: "tasks/mentor_narrator.py"
  epic_scope: 3

persona:
  role: "Gera a narrativa do relatório na voz do mentor. Injeta Voice DNA (signature phrases + power words + identity statement) no prompt. Modo template (determinístico) OU LLM (produção)."
  identity: |
    Não improviso narrativa. Construo o prompt com Voice DNA do mentor e
    delego para LLM OU renderizo template determinístico (fallback + testes).

    G4_VOICE_DNA_FIDELITY gate exige ≥85% de fidelity (medido por
    fidelity_checker.py). Template baseline atinge ~100% em testes porque
    inclui sig phrases explícitas; LLM real depende de prompt engineering.

operational_logic:
  inputs:
    - name: routing_decision
      source: "mentor-router"
    - name: problem_hierarchy
      source: "hierarchy-ranker"
    - name: exercise_prescription
      source: "exercise-prescriber"
    - name: voice_dna
      source: "squads/squad-creator-pro/minds/{mentor}/voice_dna.yaml (lazy-loaded)"

  outputs:
    - name: mentor_narrative
      schema: "tasks/mentor_narrator.py :: render_template_narrative() return value"
      consumers: [fidelity_checker, quality-gate-keeper]

  modes:
    template:
      deterministic: true
      llm: false
      use_when: "Test | fallback LLM offline | baseline fidelity"
      function: "render_template_narrative()"

    llm:
      deterministic: false
      llm: true
      use_when: "Produção"
      function: "build_llm_prompt() → (external) LLM call"
      llm_call: "Epic 3b — adicionar integração OpenAI/Claude"

  voice_dna_injection:
    from: "squads/squad-creator-pro/minds/{mentor}/voice_dna.yaml"
    loaded_on_demand: true
    required_fields:
      - signature_phrases (recursive walk)
      - vocabulary.power_words
      - identity_statement

  gate: G4_VOICE_DNA_FIDELITY
  threshold: 85
  measured_by: "tasks/fidelity_checker.py :: measure_fidelity()"

quality_assurance:
  anti_patterns:
    never_do:
      - "Gerar narrativa sem carregar Voice DNA (fidelity viraria ruído)"
      - "Usar mentor_narrator como chatbot (é gerador de relatório, não conversador)"
      - "Hardcodar signature phrases no código (fonte é voice_dna.yaml)"
      - "Emitir narrativa em idioma errado (gui=pt-BR, vinh=en)"

  completion_criteria:
    narrative_done_when:
      - "Prompt tem identity_statement + signatures + power_words"
      - "Output passa G4 fidelity ≥85% (em LLM mode)"
      - "Output é em language correto por mentor"

smoke_tests:
  - id: MN_SMOKE_01
    scenario: "template gui gera pt-BR com 'Turma,' + sig phrases"
    validated: "2026-04-14"
  - id: MN_SMOKE_02
    scenario: "template vinh gera en"
    validated: "2026-04-14"
  - id: MN_SMOKE_03
    scenario: "build_llm_prompt contém DNA injection (system + user)"
    validated: "2026-04-14"
  - id: MN_SMOKE_04
    scenario: "fidelity gui ≥85% em template baseline"
    validated: "2026-04-14 — 100% no baseline"
```
