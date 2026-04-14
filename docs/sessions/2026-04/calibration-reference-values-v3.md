# Valores de Referencia V3 — Apos Fix de Cobertura 100%

**Data:** 2026-04-14
**Video:** 53.85s, 168 palavras
**Evaluation ID:** 9093cbe9-0f18-44be-8395-177010d2f4cf
**Status:** VALIDADO — baseline pos-fix de janelas (cobertura 100% da duracao)

---

## Contexto

Substitui `calibration-reference-values-v2.md` como baseline apos 3 fixes de infraestrutura:

1. **Race condition do contexto** (`ml-worker/app.py`): aggregator espera ate 15s pelo questionario antes de cair no peso default. Garante aplicacao de pesos contextuais.
2. **Alocacao correta de janelas por terco** (`temporal_analyzer.py`): usa centro da janela em vez do inicio; ignora janelas zeradas. Fecha o bug de `fechamento.pitch/volume = 0.0`.
3. **Cobertura 100% da duracao** (`voice_analyzer.py`, `variety_analyzer.py`, `archetype_classifier.py`): N janelas = `round(duration/alvo)`, tamanho = `duration/N`. Antes, vidoes de duracao nao multipla de 15s/10s perdiam a cauda.

**Efeito:** V2 descartava 8.85s finais do video (janela 3 cobria so 30-45s). V3 usa 4 janelas de 13.46s cobrindo 100% da fala.

---

## Scores Finais

| Dimensao | V2 | V3 | Delta | Status |
|----------|----|----|----|----|
| **Overall** | 57 | **62** | +5 | Validado (peso `rede_social` aplicado) |
| Voice | 52 | **55** | +3 | Validado |
| Fillers | 76 | 76 | 0 | Validado |
| Gesture | 82 | 82 | 0 | Validado |
| Posture | 77 | 77 | 0 | Validado |
| Variety | 14 | **32** | +18 | Validado (muito_monotono → monotono) |
| Archetypes | 19 | 19 | 0 | Validado |
| Identity | 60 | 60 | 0 | Validado |
| Opening | 40 | 40 | 0 | Validado |
| Congruencia | 100 | 100 | 0 | Validado |
| Temporal | disp. | disp. | — | Fix: fechamento com valores reais |

**Por que overall subiu:** voice +3 (velocidade_score 51→68) e variety +18 (velocidade_score dimensional 36→81) propagaram para o agregado ponderado com peso `rede_social`.

---

## Voice — 55/100

| Sub-score | V2 | V3 | Delta |
|-----------|----|----|----|
| wpm_score | 46 | 46 | 0 |
| pitch_score | 100 | 100 | 0 |
| velocidade_score | 51 | **68** | +17 |
| volume_score | 20 | 20 | 0 |
| pausa_score | 44 | 44 | 0 |

| Metrica | V2 | V3 | Nota |
|---------|----|----|----|
| WPM | 187 | 187 | — |
| cv_pitch | 0.0422 | 0.0367 | Pitch estavel no trecho 40-53.85s |
| cv_volume | 0.0025 | 0.0099 | Captura variacao que estava oculta |
| cv_velocidade | 0.0523 | **0.0857** | Cruzou range ideal (0.08-0.30) |
| pitch_range_semitones | 21.6 | 21.6 | — |
| volume_base_1_10 | 6.8 | 6.8 | — |
| monotonia_score | 20 | 40 | +20 (mais CVs acima do threshold) |
| Pausas | 4 estr / 0 hes / 13 resp | idem | — |
| ratio_estrategicas | 0.235 | 0.235 | — |
| **num_janelas** | 3 | **4** | Cobertura 100% |
| **janela_size_seconds** | 15.0 (fixo) | **13.46** | duration/N |
| WPM/janela | [188, 180, 204] | [196, 160, 201, 192] | Janela de 160 WPM separada |
| Pitch/janela | [110.7, 120.7, 110.3] | [111.9, 120.7, 111.2, 110.4] | 4a janela nova |
| Volume/janela | [66.6, 67.0, 66.9] | [67.4, 65.9, 67.2, 67.6] | 4a janela nova |

---

## Variety — 32/100

| Dimensao | V2 cv | V2 score | V3 cv | V3 score | Diag V3 |
|----------|-------|----------|-------|----------|---------|
| volume | 0.0025 | 10 | **0.0099** | 23 | pouca_variacao |
| entonacao | 0.0422 | 44 | 0.0367 | 39 | pouca_variacao |
| velocidade | 0.0523 | 36 | **0.0857** | **81** | **ideal** |
| gesticulacao | 0.5556 | 49 | 0.5556 | 49 | excessiva |

| Metrica | V2 | V3 |
|---------|----|----|
| pct_tempo_monotono | 83.6% | **75.0%** |
| diagnostico | muito_monotono | **monotono** |
| defaults_detectados | velocidade, volume, entonacao | **volume, entonacao** |
| trechos_monotonos | 5 | 5 |

**Interpretacao:** a variedade nao "mudou"; o que mudou foi a nossa capacidade de **medi-la com precisao**. Com 3 janelas grandes, a cv_velocidade era subestimada em 64% (0.052 vs 0.086 real).

---

## Temporal — Fix critico

### Fechamento — valores reais (antes: zerados por bug)

| Metrica | V2 | V3 |
|---------|-----|-----|
| pitch_medio | **0.0** (bug) | **110.4** |
| volume_medio | **0.0** (bug) | **67.6** |
| score | 74 | 74 |

### Todos os tercos (duracao cada: 17.95s)

| Terco | Score | Fillers | Monotonos | Pitch V3 | Volume V3 |
|-------|-------|---------|-----------|----------|-----------|
| Abertura | 61 | 3 | 1 | 111.9 | 67.4 |
| **Meio** | **80** | 0 | 0 | 116.0 | 66.6 |
| Fechamento | 74 | 2 | 0 | **110.4** | **67.6** |

Padrao: **PICO** no meio (mantido)

---

## Demais dimensoes (sem mudanca vs V2)

### Gesture — 82/100
- sub_scores: contato_visual 100, gesticulacao 89, duas_maos 100, zona 2, distribuicao_olhar 50
- gesticulation_pct 69.4% (movimento ativo) · hand_visible 100% · eye_contact 100% · duas_maos 82.4% · zona_ideal 1.5% · vocabulario 5 · gesto_repetitivo

### Posture — 77/100
- alignment 91 · postura_aberta 100% · ombros 98.1% · grounding 60 · padrao misto · is_bust_video False

### Fillers — 76/100
- 5 total · 5.6/min · 0 hesitacoes · TTR 0.673 · 0 clusters

### Identity — 60/100
- dados_insuficientes (< 3 marcadores) · autoridade 1 · vitima 0

### Opening — 40/100
- abertura_fraca · Pergunta Casual detectada (qualidade: fraca)

### Congruence — 100/100
- 0 contradicoes

### Archetypes — 19/100
- amigo 100% · lock-in True · 0 trocas/min · sub: cycling 20, anti_lockin 10, diversidade 25

---

## Commits desta sessao

```
(staged / working tree — nao commitado)
M ml-worker/app.py                       # race-fix: aguarda contexto 15s
M ml-worker/workers/voice_analyzer.py    # cobertura 100%, janela_size_seconds
M ml-worker/workers/temporal_analyzer.py # centro da janela, ignora zeros
M ml-worker/workers/variety_analyzer.py  # janela_segundos parametrizado
M ml-worker/workers/archetype_classifier.py # cobertura 100% (janelas 10s)
```

## Impacto em producao

- **Videos de duracao multipla de 15s** (45s, 60s, 90s, 180s, 300s): valores **identicos** a V2
- **Videos de duracao irregular** (tipo 53s, 62s, 89s): metricas mais precisas pois 100% da fala e analisada
- **Determinismo:** mantido. Mesmo video → mesmo score (modulo o LLM do summary)
