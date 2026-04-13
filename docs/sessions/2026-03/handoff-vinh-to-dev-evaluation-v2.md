# Handoff: Vinh Giang → @dev (Dex)

**Data:** 2026-03-31
**De:** Vinh Giang (Communication Coach / Arquitetura de avaliação)
**Para:** @dev (Dex) — Implementação
**Contexto:** Sistema de avaliação de oratória reescrito de 4 para 6 dimensões

---

## O que foi feito (ml-worker — 100% pronto)

### Arquivos NOVOS criados
| Arquivo | O que faz |
|---------|-----------|
| `ml-worker/workers/variety_analyzer.py` | Meta-analyzer de variação temporal (velocidade, volume, pitch, gestos em janelas de 15s) |
| `ml-worker/workers/archetype_classifier.py` | Classifica trechos de 10s em 4 arquétipos vocais (Educador, Coach, Motivador, Amigo) via Parselmouth |
| `ml-worker/workers/coaching_plan.py` | Gera plano de 12 semanas personalizado com banco de 16 exercícios |

### Arquivos REESCRITOS
| Arquivo | O que mudou |
|---------|------------|
| `ml-worker/workers/voice_analyzer.py` | Análise em janelas de 15s, CV de velocidade/volume/pitch, classificação de pausas (estratégica/hesitação/respiração), WPM por janela, score de monotonia, 5 sub-scores |
| `ml-worker/workers/gesture_analyzer.py` | 5 direções de olhar (camera/baixo/esquerda/direita/cima), vocabulário de gestos (grid 3x3), duas mãos %, distribuição do olhar (entropia), gesto repetitivo, 5 sub-scores |
| `ml-worker/workers/posture_analyzer.py` | Classificação de movimento (plantado/rígido/proposital/ansioso/misto), grounding score, movimento proposital, ombros nivelados %, 4 sub-scores |
| `ml-worker/workers/filler_detector.py` | 3 categorias (hesitação/muleta_retórica/muleta_conexão), clusters de fillers (3+ em <10s), peso por gravidade (hesitação 2x), bonus diversidade lexical |
| `ml-worker/workers/report_generator.py` | Prompt com frameworks de coaching (88 Teclas, Peaks & Troughs, 80/20, Forças Primeiro). Output: resumo + forças + melhorias_80_20 + dimensões + plano_12_semanas + mensagem_final |
| `ml-worker/workers/aggregator.py` | 6 dimensões, score ponderado (variety 25%, voice 20%, gesture 15%, posture 15%, archetypes 15%, fillers 10%), dimensões fortes/fracas |
| `ml-worker/app.py` | Pipeline com 10 steps (adicionou analyzing_variety e analyzing_archetypes), salva 6 dimensões, salva campos novos no report |

---

## O que falta implementar (@dev)

### 1. Migração do banco de dados (Supabase)

**Tabela `analysis_results`** — já aceita qualquer `dimension` (text), então as novas dimensões `variety` e `archetypes` vão entrar sem alteração de schema. **Verificar se é o caso.**

**Tabela `reports`** — precisa de colunas novas:

```sql
ALTER TABLE reports ADD COLUMN IF NOT EXISTS forcas jsonb DEFAULT '[]'::jsonb;
ALTER TABLE reports ADD COLUMN IF NOT EXISTS melhorias jsonb DEFAULT '[]'::jsonb;
ALTER TABLE reports ADD COLUMN IF NOT EXISTS plano_12_semanas jsonb DEFAULT '[]'::jsonb;
ALTER TABLE reports ADD COLUMN IF NOT EXISTS mensagem_final text DEFAULT '';
```

O `app.py` já faz o insert com esses campos (linhas 179-189). Se as colunas não existirem, o insert vai falhar.

### 2. API — Endpoint de report atualizado

**Arquivo:** `apps/api/app/routes/evaluations.py`

O endpoint `GET /evaluations/{id}/report` precisa retornar a estrutura nova:

```json
{
  "evaluation": { "id": "...", "status": "completed" },
  "overall_score": 72,
  "dimension_scores": {
    "variety": 65,
    "voice": 78,
    "gesture": 60,
    "posture": 85,
    "fillers": 70,
    "archetypes": 55
  },
  "detailed_metrics": { ... },
  "report": {
    "resumo": "...",
    "forcas": [
      { "titulo": "...", "descricao": "...", "impacto": "..." }
    ],
    "melhorias_80_20": [
      { "titulo": "...", "descricao": "...", "exercicio": "...", "prioridade": 1 }
    ],
    "dimensoes": {
      "variedade": { "label": "...", "feedback": "...", "dica": "..." },
      "voz": { ... },
      "presenca_visual": { ... },
      "postura": { ... },
      "clareza_verbal": { ... },
      "arquetipos": { ... }
    },
    "plano_12_semanas": [
      { "semana": "1-2", "foco": "...", "exercicio": "...", "meta": "..." }
    ],
    "mensagem_final": "..."
  }
}
```

O endpoint `GET /evaluations/{id}/report/{dimension}` precisa aceitar as novas dimensões: `variety`, `archetypes`.

### 3. API — Status steps atualizados

O pipeline agora notifica 2 substatus novos:
- `analyzing_variety` (após analyzing_fillers)
- `analyzing_archetypes` (após analyzing_variety)

O endpoint de status e o frontend que mostra progresso precisam saber que agora são **10 steps** (antes eram 8):

```
splitting → analyzing_posture → analyzing_gesture → analyzing_voice → analyzing_fillers → analyzing_variety → analyzing_archetypes → generating_report
```

Se o frontend calcula progresso como `steps_completed / steps_total`, atualizar `steps_total` de 8 para 10.

### 4. Frontend — Dashboard com 6 dimensões

O dashboard atual renderiza 4 cards de dimensão. Precisa renderizar **6**:

| Dimensão (backend key) | Label no frontend (PT-BR) | Ícone sugerido |
|------------------------|--------------------------|----------------|
| `variety` | Variedade Vocal | 🎹 |
| `voice` | Voz e Prosódia | 🎙️ |
| `gesture` | Presença Visual | 👁️ |
| `posture` | Postura e Presença | 🧍 |
| `fillers` | Clareza Verbal | 💬 |
| `archetypes` | Arquétipos Vocais | 🎭 |

### 5. Frontend — Novas seções no report

O report agora tem seções que antes não existiam:

1. **Forças** (array) — mostrar como cards positivos no topo
2. **Melhorias 80/20** (array com prioridade) — mostrar como lista ordenada com exercício expandível
3. **Plano de 12 semanas** (array) — mostrar como timeline/stepper
4. **Mensagem final** (string) — mostrar como quote/destaque no final
5. **Sub-scores por dimensão** — cada dimensão agora tem `sub_scores` detalhados que podem ser renderizados como barras ou radar chart

### 6. Frontend — Retrocompatibilidade

O report generator mantém `summary` e `dimension_feedback` como aliases para `resumo` e `dimensoes`. Avaliações antigas continuam funcionando.

---

## Interfaces entre módulos (contratos)

### variety_analyzer.analyze_variety(voice_result, gesture_result) → dict
- **Recebe:** output do `calculate_voice_metrics()` e output do `analyze_gestures()`
- **Retorna:** `{ score, confidence, metrics: { diagnostico_geral, defaults_detectados, dimensoes, trechos_monotonos, sub_scores } }`

### archetype_classifier.classify_archetypes(audio_path) → dict
- **Recebe:** caminho do arquivo de áudio (WAV)
- **Retorna:** `{ score, confidence, metrics: { arquetipo_dominante, distribuicao, acessiveis, ausentes, lock_in, mapa_temporal, sub_scores } }`

### aggregator.aggregate_metrics(eval_id, posture, gesture, voice, filler, variety, archetype, metadata) → dict
- **BREAKING CHANGE:** antes recebia 4 dimensões, agora recebe **6** (variety_result e archetype_result são parâmetros novos)
- **Retorna:** `{ overall_score, dimension_scores, detailed_metrics, dimensoes_fortes, dimensoes_fracas, pesos_utilizados }`

### report_generator.generate_report(aggregated) → dict
- **Retorna:** `{ resumo, forcas, melhorias_80_20, dimensoes, plano_12_semanas, mensagem_final, summary (alias), dimension_feedback (alias), llm_model, llm_cost_usd }`

### coaching_plan.generate_coaching_plan(aggregated) → list
- **Nota:** este módulo existe mas NÃO está sendo chamado no pipeline atual. O plano de 12 semanas está sendo gerado pelo LLM no report_generator. O coaching_plan.py serve como fallback ou para gerar o plano sem LLM. Integrar se necessário.

---

## Decisões de arquitetura tomadas

1. **Variedade como dimensão mais pesada (25%)** — baseado no princípio "default = não-funcional"
2. **Pausas estratégicas premiam, não penalizam** — silêncio intencional é poder, não fraqueza
3. **Fillers com peso por gravidade** — hesitação (2x) > muleta conexão (1x) > muleta retórica (0.5x)
4. **Movimento proposital vs ansioso** — não basta medir estabilidade, precisa classificar o PADRÃO
5. **Contato visual com 5 direções** — não é binário (olhando/não olhando), é direcional
6. **Arquétipos classificados via features acústicas** — staccato index, tendência de pitch, speech ratio, não via LLM
7. **Prompt do LLM é coach, não relatório** — forças primeiro, 80/20, exercícios práticos, tom encorajador

---

## Arquivos para referência rápida

```
ml-worker/
├── app.py                              ← Pipeline principal (10 steps)
├── workers/
│   ├── voice_analyzer.py               ← REESCRITO (janelas + pausas)
│   ├── gesture_analyzer.py             ← REESCRITO (vocabulário + olhar)
│   ├── posture_analyzer.py             ← REESCRITO (grounding + movimento)
│   ├── filler_detector.py              ← REESCRITO (3 categorias + clusters)
│   ├── variety_analyzer.py             ← NOVO (meta-analyzer)
│   ├── archetype_classifier.py         ← NOVO (4 arquétipos)
│   ├── coaching_plan.py                ← NOVO (12 semanas)
│   ├── aggregator.py                   ← REESCRITO (6 dims + pesos)
│   └── report_generator.py             ← REESCRITO (prompt coaching)

apps/api/app/
├── routes/evaluations.py               ← PRECISA ATUALIZAR (6 dims + report novo)
├── services/dispatcher.py              ← OK (sem mudanças necessárias)

supabase/migrations/
└── [NOVA MIGRAÇÃO NECESSÁRIA]          ← colunas novas em reports
```

---

## Prioridade de implementação sugerida

1. **Migração do banco** (bloqueante — sem isso o pipeline falha no insert do report)
2. **API endpoints** (necessário para frontend consumir)
3. **Frontend — 6 dimensões no dashboard** (impacto visual imediato)
4. **Frontend — forças + melhorias + plano 12 semanas** (diferencial do produto)
5. **Frontend — progress bar com 10 steps** (nice to have)
