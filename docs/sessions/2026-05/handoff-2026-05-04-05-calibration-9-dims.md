# Handoff Sessão 2026-05-04/05 — Calibração 9 dimensões 1-a-1

## Duração

~12h em 2 dias (04/05 manhã + 05/05 manhã/tarde).

## Objetivo

Após calibração da Família Técnica em 04-29/30, validar **1-a-1 cada uma das 9 dimensões restantes** (posture, gesture, facial, tonality, archetypes, identity, storytelling, congruence + fillers já OK), comparando Gui (mentor TEDx) vs aluna (iniciante tutorial).

## Commits

- `9fb8d1b` fix(ml-worker): calibracao 9 dims + 24 hooks + congruence pedagogica

## Estado final

**Discriminação saudável em todas as 3 famílias:**

| | Gui (mentor) | Aluna (iniciante) | Gap |
|---|---|---|---|
| Overall | 93 | 66 | 27 |
| Técnica | 96 | 60 | 36 |
| Presença | 89 | 71 | 18 |
| Narrativa | 88 | 50 | 38 |

## Calibrações aplicadas por dimensão

### Posture
- Tier `plantado` por `variancia<0.001` (selfie/talking-head awareness)
- Tier `plantado_passivo` quando `alignment<92` (mentor real vs iniciante encolhido)
- `shoulder_relax_score` body-relative coletado mas **fora do score** (mobile noisy)

### Gesture
- **Iris-based gaze detection** (478 landmarks Face Landmarker) substitui inclinação de cabeça — Gui passou de 49% "olhar baixo" (falso positivo) para 3.4% real
- Thresholds Y assimétricos (selfie olha levemente pra cima pelo preview)
- Removida penalty >90% eye contact (selfie premia fixação)
- **Diversidade composta** = min(zonas, bigramas) — captura ciclos repetitivos
- Threshold gesticulação 40-70 → 40-85 (mentor engajado natural)

### Facial
- Tier `muito_expressivo` (6-14 brow/min) entre `equilibrada` e `exagerada`
- 2 tiers brow: claros (>0.005) + sutis (>0.003), `combined = claros + sutis×0.5`
- Penalty -15 pra "smile congelado" (smile<10% + var<0.01)

### Tonality
- VAD **offset +0.4 valence** pra mobile (AGC bias)
- Discriminação via **arousal** (mais estável que valence)
- Score por **textura dominante**: confiante/entusiasmado=75, neutro=55, tenso/apatico=35

### Storytelling — 24 famílias de hooks
- 6 hooks via regex novos: rhetorical_question, hypothetical, paradox, metaphor, everyday_observation, direct_challenge
- 9 famílias do **guia Conrado Adolpho 108 ganchos**: mystery_secret, fear_urgency, fomo_desire, authority_proof, unlikely_hero, numbered_list, diagnostic_quiz, targeting, belief_break
- SPECIFICITY_WEIGHTS (genéricos 0.5 vs específicos 2.0)
- Acentos normalizados (unicodedata)
- **Duration-aware scoring** (<90s/90-180s/>180s)
- Loss aversion patterns

### Identity
- LINGUAGEM_AUTORIDADE expandida com ~20 patterns adicionais
- Cobre: apresentação, verbos de ação, imperativos, **estilo didático/professor** (veja bem, olha só, na verdade), história pessoal
- Gui passa de 1→8 marcadores. Aluna tutorial também 8 (ambos identidade_firme = correto)

### Congruence — 9 regras
- 5 regras novas: sorriso_vs_tom_tenso, fala_rapida_vs_voz_plana, postura_forte_vs_voz_fraca, expressao_facial_vs_voz_apatica, coach_vs_rosto_estatico
- Suporte dot notation + operador "=="
- **Card sempre visível** no UI (antes só com contradições)
- **Explicação pedagógica** por contradição
- **Badge no hero** com 3 tiers visuais

## UI fixes
- METRIC_LABELS adicionados (facial, tonality, archetypes, storytelling, identity, opening, congruence) — eram "Dimensão não encontrada"
- VALID_DIMENSIONS expandido 6→13
- ScoreBreakdown popup → modal (escapa `overflow:hidden`)
- SUB_SCORE_DESC + DIMENSION_DESC com signature phrases Vinh

## Princípios reforçados
- "Calibrar com N=2 é overfit risk" — articulation e shoulder_relax mantidos passivos quando não discriminam
- "Mesma feature, lentes diferentes ≠ duplicação" (jitter→tonality emocional + articulation técnico)
- "Selfie ≠ palco" — thresholds e penalties precisam adaptar (eye contact >90 invertido)
- "Quando mentor é punido, threshold tá errado" — gesticulação 70+, brow 8+/min, etc

## Pendências futuras
1. Calibrar pitch_accent_quality + articulation com N≥10 vídeos studio-grade
2. Validar técnica em vídeo >2min (pendência herdada de 18/04, ainda aberta)
3. Reprocessar evals antigos com novos analyzers (atualmente mostram dados de versão antiga)
4. Callback_failed intermitente — investigar resilience
5. Considerar 4ª família "Coerência" se congruence amadurecer (hoje é badge transversal)

## Validações cross
- **Vinh Giang** validou arquitetura family + sugestões de tensão de ombros, cabeça, ocupação espacial (1ª implementada+revertida, 2 e 3 marcadas pra studio)
- **Conrado Adolpho** material aplicado integralmente nas 9 famílias de hooks

## Estado

main em `9fb8d1b`. Stack rodando local. Sistema discrimina mentor TEDx de iniciante tutorial em todas as famílias com gaps 18-38pts. UI honesta, pedagógica, com signature phrases.
