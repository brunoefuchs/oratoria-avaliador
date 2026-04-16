# Mentores Comunicação

Squad consultivo de oratória humana para o Oratória Avaliador.

## O que faz

Recebe o relatório consolidado do ml-worker (13 dimensões de análise de vídeo) e produz insight complementar via dois mind clones de elite:

| Mentor | Lente | Framework | Dimensões consumidas |
|--------|-------|-----------|---------------------|
| **Patsy Rodenburg** | Presença & Energia | Three Circles of Presence | posture, gesture, facial, opening, identity |
| **Roger Love** | Técnica Vocal | 5 Ingredients of Vocal Power | voice, tonality, variety, fillers |

O **orchestrator** (chief) sintetiza as perspectivas em um artefato consultivo com 6 seções.

## Ativação

```
@mentores-comunicacao          # Orchestrator (entry point)
@mentores-comunicacao:patsy-rodenburg   # Direto com Rodenburg
@mentores-comunicacao:roger-love        # Direto com Roger Love
```

## Comandos

| Comando | Descrição |
|---------|-----------|
| `*analyze` | Análise completa (presença + voz) |
| `*deep-dive presença` | Foco em presença (Rodenburg) |
| `*deep-dive voz` | Foco em técnica vocal (Roger Love) |
| `*quick-wins` | Top 3 melhorias acionáveis |
| `*compare` | Comparar 2 relatórios |
| `*help` | Todos os comandos |

## Como usar

1. Processe um vídeo no Oratória Avaliador (ml-worker gera relatório)
2. Ative `@mentores-comunicacao`
3. Cole o relatório e digite `*analyze`
4. Receba o artefato consultivo com perspectivas de presença + voz + quick wins

## Output

```
## Leitura Geral
## Presença & Energia (Patsy Rodenburg)
## Técnica Vocal (Roger Love)
## Pontos Cegos — O que os números não veem
## Top 3 Quick Wins
## Princípios Pedagógicos
```

## O que NÃO faz

- Não substitui o ml-worker (complementa)
- Não produz score numérico (insight qualitativo)
- Não analisa vídeo diretamente (analisa o RELATÓRIO)
- Não cobre storytelling/narrativa (use Vinh Giang ou Gui Reginatto)

## Arquitetura

```
Bruno paste relatório
       │
       ▼
  [chief] ── extrai dimensões
   │    │
   │    ├── posture/gesture/facial → [patsy-rodenburg]
   │    │                                    │
   │    ├── voice/tonality/variety → [roger-love]
   │    │                                    │
   │    ◀──── perspectivas ──────────────────┘
   │
   ▼
  Artefato consultivo (6 seções) → Bruno
```

## Referências

- **PRD:** `docs/projects/mentores-comunicacao/prd.md`
- **Patsy Rodenburg:** "Presence", "The Second Circle", "The Right to Speak"
- **Roger Love:** "Set Your Voice Free", "Love Your Voice"
