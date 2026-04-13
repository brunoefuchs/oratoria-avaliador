# Valores de Referencia — Calibracao dos Analyzers

**Data:** 2026-04-13
**Video de referencia:** 53.85s, 168 palavras (video do mentor)
**Contexto:** Apos reconstrucao do voice_analyzer e posture_analyzer, estes sao os valores de referencia validados.

## Scores de Referencia (video padrao)

| Dimensao | Score | Status |
|----------|-------|--------|
| Overall | **56** | Validado |
| Voice | **52** (+/-1 do original 51) | Validado |
| Fillers | **76** | Identico |
| Gesture | **76** | Identico |
| Posture | **77** | Identico |
| Variety | **14** | Identico |
| Archetypes | **19** | Identico |
| Identity (Epic 6) | **100** | Novo |
| Opening (Epic 6) | **60** | Novo |
| Congruencia | **100** | Validado |

## Metricas Detalhadas de Referencia

### Voice
- wpm: 187
- cv_pitch: ~0.042 (calculado por janela 15s)
- cv_volume: ~0.003 (calculado por janela 15s)
- cv_velocidade: 0.0523
- pitch_range: 21.6 semitons
- sub_scores: wpm 46, pitch 100, velocidade 51, volume 20, pausa ~44
- pausas: ~4 estrategicas, 0 hesitacao, ~13 respiracao
- ratio_estrategicas: ~0.23

### Posture
- padrao_movimento: **misto**
- grounding_score: **60**
- proposital_score: **50**
- alignment_score: 91
- open_posture_pct: 100%
- ombros_nivelados_pct: 98.1%
- ratio_parado: **0.234**
- threshold_deslocamento: **0.005**

### Variety
- pct_tempo_monotono: **83.6%**
- diagnostico: muito_monotono
- sub_scores: volume 10, entonacao 44, velocidade 36, gesticulacao 49

## Thresholds Calibrados

| Parametro | Valor | Justificativa |
|-----------|-------|---------------|
| voice: JANELA_SEGUNDOS | 15 | Janela temporal para CV |
| voice: pausa estrategica threshold | 0.5s | Gaps >= 0.5s sem hesitacao antes |
| voice: pausa respiracao threshold | 0.2-0.5s | Micro-pausas |
| voice: hesitacao_sounds | hum, eee, aaa, uhh | Apenas sons reais, nao muletas |
| posture: threshold_deslocamento | 0.005 | Calibrado para ratio_parado ~0.234 |
| posture: ansioso threshold | ratio_parado < 0.20 | Abaixo = movimento excessivo |

## Incidente — Perda de Codigo Nao Commitado

Em 2026-04-09, um `git checkout` acidental reverteu voice_analyzer.py e posture_analyzer.py para versoes basicas (Epic 2). As versoes ricas (Epic 3) nunca haviam sido commitadas.

**Reconstrucao:** Feita em 2026-04-13 com base em:
1. Handoff doc (docs/sessions/2026-03)
2. Output da avaliacao anterior (dados no Supabase)
3. Spec arquitetural da Aria

**Licao aprendida:** SEMPRE commitar codigo funcional, mesmo em branches de desenvolvimento. Codigo nao commitado = codigo perdido.
