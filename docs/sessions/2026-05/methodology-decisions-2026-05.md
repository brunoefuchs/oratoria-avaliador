# Decisões Metodológicas — Sprint Calibração 2026-04 a 2026-05

Documento sintetizando todas as decisões de calibração aplicadas, **com fundamentação**, e as decisões que **escolhemos NÃO aplicar** em favor de confiabilidade.

**Escopo temporal**: 2026-04-29 (família scores) → 2026-05-05 (calibração 9 dims).
**Validação ground truth**: Gui Reginatto (mentor TEDx-tier) vs aluna iniciante (vídeo tutorial). N=2.
**Premissa do sistema**: cliente usa **smartphone em selfie/talking-head** (vídeo curto rede social). Não palco com câmera profissional.

---

## Princípios metodológicos cristalizados

Os princípios abaixo foram aplicados como filtro de TODA decisão. Cada calibração ou rejeição foi avaliada contra estes critérios.

### 1. Calibração honesta antes de scoring honesto

> Quando mentor TEDx-tier é punido pelo sistema, o threshold está errado, não o mentor.

Aplicado quando: gesticulação 70%+ era marcada "exagerada", brow_raises 8/min idem, pitch_range 34.5 era "neutro" em vez de "expressivo". Threshold ampliado em todos os casos.

### 2. N=2 é overfit

> Calibrar usando apenas 2 speakers é arriscado. Quando uma métrica não discrimina com N=2, mantemos como **passiva** (no JSON, fora do score) até ter ≥10 vídeos diversos.

Aplicado em: articulation, shoulder_relax_score, pitch_accent_quality.

### 3. Selfie ≠ Palco

> Premissas opostas em formatos diferentes. Threshold que faz sentido em palco pode ser INVERTIDO em selfie.

Casos:
- Eye contact >90% em palco = "fixação robótica" (problema). Em selfie = "engajamento ideal" (premiar).
- Distribuição de olhar em palco = entropia alta (varrer audiência). Em selfie = entropia BAIXA é o ideal (foco na câmera).
- Dinamismo postural em palco = movimento intencional (premiar). Em selfie = câmera fixa, métrica perde sentido.

### 4. Mesma feature, lentes diferentes ≠ duplicação

> Jitter/shimmer/HNR podem virar `tonality` (interpretação emocional) E `articulation` (interpretação técnica). Isso não é duplicação — é diferentes dimensões interpretando os mesmos features brutos.

Aplicado em: articulation_analyzer reusa features de tonality_analyzer com framing diferente.

### 5. Duration-aware scoring

> Vídeo de 60s ≠ 5min ≠ 10min. Storytelling/tonality/cycling expectations devem escalar com duração disponível.

Aplicado em: storytelling (Reel/médio/palestra), tonality (cycling esperado por duração).

### 6. Ground truth real-world > thresholds da literatura

> Literatura prosódica calibra em mic studio. Mobile + AGC introduz bias estrutural. Recalibrar thresholds com vídeo real do cliente.

Aplicado em: cv_volume floor 0.03→0.015, cv_pitch range 0.05-0.20, valence offset +0.4 mobile.

### 7. Melhor não medir do que medir errado

> Quando uma métrica é **ruidosa em mobile** (não discrimina), exibi-la confunde o cliente. Mantemos coletando no JSON (passive) mas escondemos do UI até calibrar com áudio/vídeo studio-grade.

Aplicado em: spectral clarity (articulation), shoulder tension, formant analysis (não implementado).

### 8. Discriminação validada externamente, não internamente

> Não basta o sistema discriminar Gui de aluna. A discriminação tem que estar dentro de **distribuição esperada por literatura**: Hincks 2005 (PVQ), Tsai 2015 (TED). Validamos para garantir que não inflamos artificialmente os scores.

Hincks PVQ: estudante 0.146 / expert 0.230 (gap 57% relativo). Nosso gap voice 22pts (24% relativo) = abaixo da literatura, conservador.

---

## Calibrações APLICADAS (por dimensão)

### Família Técnica

#### Voice (calibrada 04-29)
- **Janelas adaptativas** (5-12s, alvo 12 janelas) — antes era fixo 15s
- **3 sub-scores**: WPM (35%) + Pitch range absoluto (30%) + Pausa (35%)
- **Removidos cv_volume, cv_velocidade** — eram double counting com Variety
- **Plateau apertado em velocidade** (CV ≥0.20 = 100, antes ≥0.12)
- **Pitch accent metric (passivo)**: count, mean_prominence_st — discrimina qualidade vs quantidade

#### Variety (calibrada 04-29)
- **Removido gesto** — era double counting com dimensão Gestos
- **União de intervalos** no pct_tempo_monotono (era soma com double-counting)
- **Skip detecção trecho monótono** quando CV global > 1.5× piso ideal (mentor TEDx que varia globalmente tem direito a platôs locais)
- **Penalidade local por dimensão** (trecho monótono vol/vel/pitch reduz sub-score só dessa dim, mostra ONDE)

#### Fillers (já estável)

### Família Presença Física

#### Posture
- **Tier `plantado`** por variancia<0.001 (selfie/talking-head awareness)
- **Tier `plantado_passivo`** quando alignment<92 (mentor real vs iniciante encolhido)
- **Dinamismo neutralizado em selfie** (75 fixo) — câmera fixa não tem o que medir

#### Gesture
- **Iris-based gaze detection** (478 landmarks Face Landmarker) substitui inclinação de cabeça — Gui passou de 49% "olhar baixo" (falso positivo) para 3.4% real
- **Thresholds Y assimétricos**: UP 0.55 (selfie olha levemente pra cima — preview), DOWN 0.30 (olhar real pra baixo)
- **Removida penalty >90% eye contact** (selfie premia fixação na câmera)
- **Diversidade composta** = min(zonas, bigramas) — captura ciclos repetitivos (A-B-A-B = entropia zonas alta mas bigramas baixa)
- **Threshold gesticulação ampliado** 40-70 → 40-85 (mentor TEDx engajado fica naturalmente em 70-90%)
- **Distribuição olhar como bell curve**: 85-95% câmera = 100, 100% = 70 (robotico), <70% = decay

#### Facial
- **Tier `muito_expressivo`** (6-14 brow/min) entre `equilibrada` e `expressao_exagerada`. Mentor TEDx faz 8.2/min naturalmente.
- **2 tiers brow detection**: claros (delta>0.005) + sutis (>0.003). brow_combined = claros + sutis*0.5
- **Penalty -15 pra "smile congelado"** (smile<10% + variability<0.01)

### Família Narrativa

#### Tonality
- **VAD offset +0.4 valence pra mobile** (AGC + jitter/HNR derrubam ~0.4pt)
- **Discriminação via AROUSAL** (mais estável em mobile que valence)
- **Score restruturado por TEXTURA dominante**: confiante/entusiasmado=75, neutro=55, tenso/apatico=35
- **Duration-aware**: Reel <90s baseline 90 (textura positiva única é OK), médio 80, palestra 75 + bonus diversidade
- **Penalty lock-in modulado**: lock-in em textura positiva = -5; em negativa = -25

#### Storytelling — 24 famílias de hooks
- **6 hooks via regex novos**: rhetorical_question, hypothetical, paradox, metaphor, everyday_observation, direct_challenge
- **9 famílias do Conrado Adolpho 108 ganchos**: mystery_secret, fear_urgency, fomo_desire, authority_proof, unlikely_hero, numbered_list, diagnostic_quiz, targeting, belief_break (~50 patterns regex)
- **SPECIFICITY_WEIGHTS**: hooks específicos peso 2.0, genéricos 0.5
- **Acentos normalizados** via unicodedata (regex sem acento casa texto com)
- **Loss aversion patterns** (cortisol "suave" — pitch de venda)
- **Duration-aware scoring**: <90s baseline 35 + hook 25 + cta 20; 90-180s médio; >180s palestra com bridge essencial
- **Type map opening_analyzer→storytelling expandido** (declaracao_axiomatica, identity_led, frase_impacto)

#### Archetypes (já estável)

#### Identity
- **LINGUAGEM_AUTORIDADE expandida** (~20 patterns adicionais):
  - Apresentação ("meu nome é")
  - Verbos de ação 1ª pessoa (destravo, ensino, mostro, transformo)
  - Imperativos (use, evite, contrate, faça, pare de)
  - **Estilo didático/professor** (veja bem, olha só, na verdade, perceba)
  - História pessoal ("aprendi que", "vi mais de N", "tenho N anos")

#### Congruence — 9 regras
Originais 4: entusiasmo_vs_postura, confianca_vs_olhar, abertura_vs_volume, urgencia_vs_parado.
Novas 5: sorriso_vs_tom_tenso, fala_rapida_vs_voz_plana, postura_forte_vs_voz_fraca, expressao_facial_vs_voz_apatica, coach_vs_rosto_estatico.
- **Suporte dot notation** (vad_medio.arousal)
- **Operador `==`** pra textura_dominante
- **Card sempre visível** no UI (antes só com contradições)
- **Bloco educacional** explicando 3 canais (verbal/vocal/visual)
- **Explicação pedagógica** por contradição
- **Badge no hero** sempre visível com 3 tiers

---

## Decisões NÃO aplicadas (por confiabilidade)

### Articulation completa em mobile

**O que tentamos**: implementar Foundation 5 (articulation) usando jitter/shimmer/HNR + spectral_clarity (energia 4-8kHz banda de consoantes).

**Resultado**: Gui 23/100, Aluna 23/100. **Não discrimina**.
- HNR baixo em ambos (8.3, 7.9) — room noise em mobile
- Jitter/shimmer no noise floor de AGC
- Spectral clarity 0.003 nos dois — codec mp4/m4a corta agressivamente acima de 8kHz

**Decisão**: removida do scoring, mantida em SECONDARY (passive no JSON). **Reativar quando ≥10 vídeos studio-grade disponíveis.**

### Formant analysis (vogais)

**Por que não implementamos**: 45% confiabilidade em mobile (estimativa otimista). Praat to_formant_burg() exige áudio limpo + voiced segments contínuos. Mobile com AGC + reverb + fala rápida quebra detecção.

**Decisão**: marcada como Story futura para áudio studio.

### Shoulder tension (tensão de ombros)

**O que tentamos**: distance vertical orelha→ombro normalizada por largura dos ombros (body-relative). Ratio <0.7 = tenso, >1.0 = relaxado.

**Resultado**: Gui ratio 0.373 / Aluna 0.374. **Diferença 0.001 = ruído.**
- Em selfie/talking-head, ambos têm postura corporal similar
- MediaPipe Pose 2D não captura nuance de tensão muscular (microcontraction)
- Vinh-style "ombros encolhidos" exige observação visual ou EMG, não 2D pose

**Decisão**: removido do score. Mantido coletando no JSON. Removido do UI METRIC_LABELS pra não confundir cliente.

### Verticalidade da cabeça (head pitch)

**Por que não implementamos**: Pose 2D só infere via offset Y nariz×ombros = 50% confiável. Combinar com Face Landmarker (que tem z-axis em landmarks) elevaria para 75% — mas exige integração que não foi prioridade. Já temos eye_contact_pct que cobre o caso prático.

**Decisão**: deferred. Usar eye_contact + iris_gaze já cobre 80% do que importa.

### Ocupação espacial / body envelope

**Por que não implementamos**: 70% confiável em half-body+, 40% em bust crop. Em selfie crop (formato dominante), não dá pra medir mãos abertas/peito expandido com confiança porque mãos podem estar fora do frame.

**Decisão**: condicional — implementar se `is_bust_video=False`. Preferimos não implementar agora (caso minoritário).

### Pitch accent integrar no voice_score

**Status atual**: pitch_accent_count, mean_prominence_st coletados no JSON. Discriminam Gui (10.8st) vs aluna (7.6st).

**Por que não integramos**: N=2 = overfit risk. Não sabemos se mean_prominence é estável em populações diversas. Esperando ≥10 vídeos pra calibrar peso e baseline.

**Decisão**: passive até calibração com mais speakers.

### Micropostura em palavras-chave

**Por que não implementamos**: detectar "speaker encolhe na palavra mais importante = mentirômetro" exigiria timestamp das palavras-chave (transcript) cruzados com snapshots de postura naquele momento. Complexidade alta + N=2 não basta pra calibrar threshold. Vinh sugeriu como Story PROSO-3 futuro.

**Decisão**: deferred. Implementação custosa pra valor incerto sem mais data.

### Gemini Vision / LLM como default scorer

**Por que não usamos**: custo recorrente ($0.0013/eval pra Gemini Vision). Princípio do `gemini_vision_on_demand` (18/04): ML pago só em dimensões onde matemática é fraca, nunca como default. Hoje gemini é usado SOMENTE em Story 9.6 (gesto semântico) como sanity check, não como score primário.

**Decisão**: ML pago é multiplicador, não core.

---

## Limitações conhecidas remanescentes

1. **Distribuição olhar em selfie é simplificada** — bell curve baseada em eye_contact_pct, não captura ainda "olhar morto" (fixo na câmera mas sem vida) vs "olhar engajado" (microvariações naturais). Para detectar isso, precisaria pupil tracking + saccades — fora do escopo MediaPipe.

2. **Tonality offset valence é heurística** — +0.4 foi calibrado empiricamente com 2 speakers em smartphone. Pode estar over-correcting em alguns devices. Validação com gravações de outros celulares pendente.

3. **Storytelling regex em PT-BR só** — patterns assumem português brasileiro. Sotaque forte ou inglês quebra detecção. Multilíngue exige expansão.

4. **Articulation em SECONDARY** — não detecta quem mumbla mesmo com voz "limpa" no resto. Precisa áudio studio para discriminar.

5. **Vídeo >2min ainda não validado** — todos os tests com Gui+aluna foram ≤60s. Janelas adaptativas escalam mas o impacto em pct_tempo_monotono em vídeos longos não foi medido empiricamente. **Pendência herdada de 2026-04-18 ainda aberta.**

---

## Pendências críticas (próximas sprints)

| # | Item | Esforço | Prioridade |
|---|---|---|---|
| 1 | Validar técnica em vídeo >2min (herdada 18/04) | 1h | Alta |
| 2 | Coletar 10+ vídeos diversos pra calibrar pitch_accent + articulation | Coleta + 1 dia | Alta |
| 3 | Reprocessar evals antigos com novos analyzers | 2h | Média |
| 4 | Investigar callback_failed intermitente | 2h | Média |
| 5 | Considerar 4ª família "Coerência" se congruence amadurecer | 4h | Baixa |
| 6 | Adicionar Story PROSO-3 (micropostura em keywords) | 1-2 dias | Baixa |
| 7 | Tonality cross-device validation | Coleta | Baixa |

---

## Cross-validation externa

**Hincks 2005** (Pitch Dynamism Quotient — PDQ):
- Estudante baseline: PDQ 0.146
- Expert lecturer: PDQ 0.230 (p<0.001, gap 57% relativo)
- Gui em mobile (AGC compresso): PDQ 0.10 → equivale a expert tier studio
- Gap nosso (voice 22pts ≈ 24% relativo) **conservador** vs literatura

**Tsai 2015** (TED talks):
- TED speakers: pitch range >20 semitons
- Tier alto: 30+ semitons
- Gui 34.5 semitons → confirmado TED-tier

**Vinh Giang validações**:
- Arquitetura family scores aprovada (3 famílias espelhando Look-Feel-Sound Triangle)
- Sugestões: tensão ombros (implementada→revertida), verticalidade cabeça (deferred), ocupação espacial (deferred condicionada)
- Endorsement: "Vocês inventaram minha pedagogia em código"

**Conrado Adolpho** (108 Ganchos):
- 9 categorias mapeadas integralmente em hook patterns
- Cobertura de hooks de venda/marketing significativa (Reels/social)

---

## Estado final

main em `b19b532` + commits subsequentes da sessão 2026-05-05 noite.
Stack 100% local rodando. UI honesta com signature phrases Vinh.
Discriminação saudável Gui vs aluna em todas as 3 famílias (gap 18-38pts).

**Princípio síntese**: *"Calibrar é ajustar tudo até o sistema dizer o que mentor humano experiente diria — não o que parece convincente em PowerPoint."*
