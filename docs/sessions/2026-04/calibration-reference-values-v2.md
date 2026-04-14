# Valores de Referencia V2 — Apos Refinamento Maximo

**Data:** 2026-04-13
**Video:** 53.85s, 168 palavras
**Evaluation ID:** 6f69288f-b41f-4756-9d68-8fe86de840c0
**Status:** VALIDADO — todas as subcamadas auditadas

---

## Scores Finais

| Dimensao | Score | Status |
|----------|-------|--------|
| **Overall** | **57** | Validado (pesos contextuais) |
| Voice | **52** | Validado (5 sub-scores identicos) |
| Fillers | **76** | Validado |
| Gesture | **82** | Validado (gesticulation refinada: movimento ativo 69.4%) |
| Posture | **77** | Validado (misto, grounding 60, proposital 50) |
| Variety | **14** | Validado (pct_monotono 83.6%) |
| Archetypes | **19** | Validado (lock-in amigo 100%) |
| Identity | **60** | Validado (dados_insuficientes — threshold minimo 3 marcadores) |
| Opening | **40** | Validado (pergunta casual, nao reflexiva) |
| Congruencia | **100** | Validado (0 contradicoes) |
| Temporal | **Disponivel** | Validado (pico: 61→80→74) |

---

## Voice — 52/100

| Sub-score | Valor | Validado |
|-----------|-------|----------|
| wpm_score | 46 | ✅ |
| pitch_score | 100 | ✅ |
| velocidade_score | 51 | ✅ |
| volume_score | 20 | ✅ |
| pausa_score | 44 | ✅ |

| Metrica | Valor |
|---------|-------|
| WPM | 187 |
| cv_pitch | 0.0422 |
| cv_volume | 0.0025 |
| cv_velocidade | 0.0523 |
| pitch_range_semitones | 21.6 |
| volume_base_1_10 | 6.8 |
| monotonia_score | 20 |
| Pausas | 4 estr / 0 hes / 13 resp |
| ratio_estrategicas | 0.235 |
| WPM/janela | [188, 180, 204] |
| Pitch/janela | [110.7, 120.7, 110.3] |
| Volume/janela | [66.6, 67.0, 66.9] |

## Gesture — 82/100

| Sub-score | Peso | Valor |
|-----------|------|-------|
| contato_visual | 35% | 100 |
| gesticulacao | 30% | 89 |
| duas_maos | 15% | 100 |
| zona | 10% | 2 |
| distribuicao_olhar | 10% | 50 |

| Metrica | Valor | Nota |
|---------|-------|------|
| gesticulation_pct | **69.4%** | REFINADO — mede movimento ativo, nao presenca |
| hand_visible_pct | 100.0% | NOVO — maos visiveis em todos os frames |
| eye_contact_pct | 100.0% | Video frontal camera unica |
| duas_maos_pct | 82.4% | |
| zona_ideal_pct | 1.5% | Gestos fora da zona peito-cintura |
| vocabulario_gestos | 5 | |
| gesto_repetitivo | True | |

## Posture — 77/100

| Sub-score | Peso | Valor |
|-----------|------|-------|
| alinhamento | 35% | 91 |
| postura_aberta | 20% | 100 |
| grounding | 25% | 60 |
| movimento_proposital | 20% | 50 |

| Metrica | Valor |
|---------|-------|
| padrao_movimento | misto |
| is_bust_video | False |
| ombros_nivelados_pct | 98.1% |
| ratio_parado | 0.234 |
| threshold_deslocamento | 0.005 |

## Fillers — 76/100

| Metrica | Valor |
|---------|-------|
| total_fillers | 5 |
| fillers_per_minute | 5.6 |
| hesitacoes | 0 |
| muletas_conexao | 4 |
| muletas_retorica | 1 |
| clusters | 0 |
| type_token_ratio | 0.673 |

## Variety — 14/100

| Sub-score | Valor |
|-----------|-------|
| variacao_volume | 10 |
| variacao_entonacao | 44 |
| variacao_velocidade | 36 |
| variacao_gesticulacao | 49 |

| Metrica | Valor |
|---------|-------|
| pct_tempo_monotono | 83.6% |
| diagnostico | muito_monotono |
| defaults | velocidade, volume, entonacao |

## Identity — 60/100

| Metrica | Valor | Nota |
|---------|-------|------|
| score | 60 | NEUTRO (dados insuficientes) |
| diagnostico | dados_insuficientes | < 3 marcadores totais |
| autoridade_count | 1 | |
| vitima_count | 0 | |
| total_vicios | 0 | |

## Opening — 40/100

| Metrica | Valor | Nota |
|---------|-------|------|
| score | 40 | Pergunta casual, nao reflexiva |
| diagnostico | abertura_fraca | |
| tecnica | Pergunta Casual (fraca) | "voce sabe como funciona a internet?" |
| sugestoes | 3 alternativas | Reflexiva, frase impacto, historia |

## Temporal

| Terco | Score | Fillers | Monotonos |
|-------|-------|---------|-----------|
| Abertura | 61 | 3 | 1 |
| Meio | **80** | 0 | 0 |
| Fechamento | 74 | 2 | 0 |

Padrao: **PICO** no meio

## Congruencia — 100/100

0 contradicoes detectadas.

---

## 5 Refinamentos Aplicados nesta Sessao

1. **gesticulation_pct**: presenca→movimento ativo (100%→69.4%)
2. **open_posture_pct**: deteccao de video busto (flag is_bust_video)
3. **identity score**: threshold minimo 3 marcadores (100→60)
4. **opening**: casual vs reflexiva (60→40)
5. **temporal**: duration fix (indisponivel→disponivel)

## Commits desta sessao de calibracao

```
e8771b5 fix: calibrar pausas + posture threshold
9a17139 feat: commit arquivos criticos nunca commitados (Epic 3)
f7bb3c0 fix: replay 3-lanes + video-player + shared page
0680254 fix: salvar identity/opening/temporal/congruence no detailed_metrics
dc5f029 fix: refinamento maximo — 5 metricas corrigidas
f7ce4ab fix: reconstruir voice_analyzer e posture_analyzer
6aed1ef fix: CV por janela, pausas sem pontuacao, variety nested
2119412 fix: calibrar pausas 0.5s + posture 0.005
```
