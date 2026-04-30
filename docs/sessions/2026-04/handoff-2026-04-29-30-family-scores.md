# Handoff Sessão 2026-04-29/30 — Family Scores + Refinamento Técnica/Variety

## Duração

~14h ao longo de 2 dias (29/04 noite + 30/04 manhã).

## Objetivo da sessão

Calibrar técnica vocal pós-Epic 9 (continuação do sprint 18/04) e desenhar
estrutura pedagógica que separa Técnica de Narrativa, validada com Vinh Giang.

## Commits

| Commit | Descrição |
|---|---|
| `26d8608` | Remove gesto de Variedade Vocal (mistura conceitual + double counting) |
| `4140c1a` | Janelas adaptativas + monotonia honesta + plato velocidade apertado |
| `v0.6.0-honest-prosody` | Tag de checkpoint pós-calibração |
| `22a6c19` | Separa Voice (técnica) de Variety (expressividade) |
| `9dd5f91` | Family scores Técnica/Presença/Narrativa + articulation passivo + pitch_accent |

## Decisões arquiteturais

### Família 1: Técnica Vocal (calibrada)
- **voice** (cadência/range/pausa) — 30% peso família
- **variety** (variação temporal CV) — 30% peso família
- **fillers** (vícios linguagem) — 15% peso família
- *articulation* — passivo, fora do scoring

### Família 2: Presença Física (não calibrada)
- **gesture** — 35% peso família
- **posture** — 30% peso família
- **facial** — 35% peso família

### Família 3: Narrativa (não calibrada)
- **storytelling** — 35% peso família (bridge/hook/chemicals)
- **archetypes** — 25% peso família (cycling 4 personas)
- **tonality** — 25% peso família (VAD emocional)
- **identity** — 15% peso família (coerência persona)

## Validação real-world (Gui mentor vs aluna iniciante)

| Família | Gui | Aluna | Gap |
|---|---|---|---|
| Técnica Vocal | 96 | 60 | 36 |
| Presença Física | 77 | 66 | 11 |
| Narrativa | 57 | 38 | 19 |

Cross-validation externa:
- Hincks 2005 PVQ: estudante 0.146 / expert 0.230. Gui em 0.10 com AGC mobile
  ≈ tier expert. Sistema honesto (não inflado).
- Tsai 2015: TED speakers >20 semitons. Gui 34.5 alinhado.

## Calibrações finalizadas (Técnica)

### voice_analyzer (3 sub-scores)
1. WPM (cadência) — peso 35%
2. Pitch range em semitons (amplitude melódica) — peso 30%
3. Pausas (estrutura rítmica) — peso 35%

Removidos sub-scores cv_volume/cv_velocidade — eram double counting com Variety.

### variety_analyzer
- Janelas adaptativas: clamp(5, dur/12, 12) — alvo 12 janelas
- Detecção de trecho monótono via união de intervalos (não soma)
- Skip detecção quando CV global > 1.5× piso ideal (speaker que varia
  globalmente tem direito a platôs locais)
- Plato velocidade apertado (CV ≥0.20)
- **Penalidade local por dimensão**: trecho monótono numa dim reduz seu
  sub-score + diagnóstico vira "atenção"

### Refinamentos de UI
- "Voz e Dicção" → "Técnica Vocal"
- Sub-score labels: "Tom/Volume/Velocidade" → "Variação de Tom/Volume/Velocidade"
- 3 cards família com feedback textual (signature phrases do Vinh em scores baixos)
- Sub-dimensões nested clickáveis dentro de cada card de família

## Métricas passivas adicionadas (em SECONDARY, fora do score)

### pitch_accent_quality (voice_analyzer)
- count, per_minute, strong_per_minute, mean_prominence_st, max_prominence_st
- Discrimina QUALIDADE prosódica (Gui 10.8st vs aluna 7.6st) vs quantidade
- Smoke confirma: aluna oscila frequente mas pequeno (ansiedade), Gui modula
  menos vezes mas dramaticamente (ênfase intencional)

### articulation_analyzer.py (NOVO)
- Foundation 5 do Vinh (clareza técnica)
- Reusa jitter/shimmer/HNR + spectral_clarity (4-8kHz consoantes)
- Smoke mobile: Gui 23 / aluna 23 — NÃO discrimina (codec corta high-freq)
- Mantido em SECONDARY até validação com áudio studio-grade

## Pendências para próxima sessão

1. **Validar Técnica em vídeo >2min** (pendência herdada 18/04, ainda aberta)
2. **Coletar 5-10 vídeos diversos** pra calibrar pitch_accent + articulation
3. **Calibrar Família Narrativa** com mesmo rigor da Técnica
   - Storytelling: bridge sentence detection já existe (suggestions OK)
   - Archetypes: cycling/lock-in já mede
   - Tonality: VAD funcionando
   - Identity: revisar
4. **Callback_failed intermitente** — workaround manual via curl. Resilience
   na chamada ml-worker → API merece investigação
5. **Hot-reload do uvicorn** falhou múltiplas vezes nesta sessão — restart
   manual necessário. Investigar StatReload behavior

## Princípios cristalizados

> "Não calibre 9 dimensões num único score — separa em famílias com calibração
> independente. Foundation primeiro, prédio depois."

> "Mesma feature, duas lentes pedagogicamente distintas — não é duplicação."
> (Caso jitter/shimmer/HNR: tonality interpreta emocional, articulation
> interpreta técnica)

> "Penalidade local mostra ONDE, penalidade global mostra IMPACTO no overall."

> "Spectral em mobile é ruidoso — melhor não medir do que medir errado."

## Validação Vinh Giang

Sessão teve 2 rounds com agente Vinh:
1. Validar arquitetura family scores → aprovou + sugeriu 3 famílias (não 2)
   espelhando Look-Feel-Sound Triangle
2. Validar UI hierárquica → aprovou + recomendou explicação textual embaixo
   de cada score, signature phrases em scores baixos

## Estado final

main em `9dd5f91`. Tag `v0.6.0-honest-prosody` em `4140c1a`.
ml-worker, web e api rodando local. Stack pronta pra teste real.

UI mostra:
- Hero com overall_score + ScoreBreakdown
- **3 cards família hierárquicos** (Técnica/Presença/Narrativa) com sub-dims
- OpeningCard (Story 7.2)
- Pontos Fortes
- Dimensões analisadas (legacy view, mantida)
