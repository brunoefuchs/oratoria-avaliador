# Handoff: Gaps Técnicos do Relatório → @dev

**Data:** 2026-04-14
**De:** @vinh-giang (análise técnica via squad-creator-pro)
**Para:** @dev (Dex)
**Contexto:** Análise técnica das 10 screenshots em `ajustes oratoria/` do último relatório gerado (score 45/100)
**Status:** PRONTO PARA IMPLEMENTAÇÃO

---

## Objetivo

Fechar 7 gaps críticos + 4 bugs + 3 problemas de método de avaliação identificados no relatório final. O app mede o instrumento bem — mas **não avalia a música** (storytelling ausente) e **não cruza canais** (congruência calculada mas não surface).

**Descoberta importante:** `ml-worker/workers/congruence_analyzer.py` e `opening_analyzer.py` **JÁ EXISTEM** mas não aparecem no relatório UI. Implementação pode ser parcial — verificar integração primeiro antes de assumir dev zero.

---

## Prioridade de implementação (80/20)

| # | Prioridade | Item | Status esperado | Esforço |
|---|------------|------|-----------------|---------|
| 1 | P0 BUG | Diversidade arquétipos calcula 25 com 1 arquétipo (deveria ser 0) | Bug fix | S |
| 2 | P0 BUG | Fillers/min e Muletas/min duplicados (mesmo valor 5.6) | Dedup | S |
| 3 | P0 BUG | Contato visual 100 = max-is-best (deveria ser banda ideal 75-90) | Reescalar | S |
| 4 | P0 BUG | Gesticulação score 49 ambíguo (pouco ou demais?) | Bidirectional scale | M |
| 5 | P1 | Surface **Congruence Score** (worker já existe) | Integração + UI | M |
| 6 | P1 | Surface **Opening / Primeira Impressão** (worker já existe) | Integração + UI | M |
| 7 | P1 | Transparência pesos do score geral | Expor breakdown | S |
| 8 | P2 | Storytelling Structure (Bridge + 4 Chemicals) | Novo worker | L |
| 9 | P2 | Peaks/Troughs temporal mapping (curva emocional) | Enriquecer variety | M |
| 10 | P2 | Expressão facial (smile/brow/micro) | MediaPipe Face Mesh | L |
| 11 | P2 | Tonalidade emocional (VAD prosody) | Novo analyzer | L |
| 12 | P3 | Scale-to-room (contexto ajusta pesos) | Questionário + aggregator | M |

**Sugestão:** P0+P1 como primeira sprint (fix bugs + integrar workers já existentes). P2 como segunda sprint (novas dimensões). P3 quando contextos múltiplos aparecerem em uso real.

---

## Detalhamento por item

### 🐛 P0 BUG #1 — Diversidade de arquétipos

**Sintoma:** Tela 8.png — "Arquétipos usados: 1" (100% Amigo), mas sub-score "Diversidade: 25". Matematicamente deveria ser 0 (1 de 4 = 25% teórico apenas se usasse cada um 25%, mas o user usou 1 em 100%).

**Arquivo provável:** `ml-worker/workers/archetype_classifier.py`

**Fix esperado:**
```python
# Diversity score = (archetypes_used / total_archetypes) × distribution_evenness
# Se usou só 1 → evenness = 0 → score = 0
archetypes_used = len([a for a in distribution.values() if a > 0.05])
evenness = 1 - max(distribution.values()) if archetypes_used == 1 else shannon_entropy(distribution)
diversity_score = (archetypes_used / 4) * evenness * 100
```

**AC:**
- Se usuário usa 1 arquétipo em 100% → Diversidade = 0
- Se usa 4 igualmente (25% cada) → Diversidade = 100
- Se usa 2 em 50%/50% → Diversidade = ~50

---

### 🐛 P0 BUG #2 — Fillers/min vs Muletas/min duplicados

**Sintoma:** Tela 7.png mostra ambas métricas em 5.6. User anotou: *"são a mesma coisa, podem ser substituídos por um único item chamado VÍCIOS DE LINGUAGEM POR MINUTO"*.

**Arquivo provável:** `ml-worker/workers/filler_detector.py` + `apps/web/src/app/report/[id]/[dimension]/page.tsx`

**Fix esperado:**
- Consolidar em único campo `vicios_linguagem_por_minuto`
- Remover campo duplicado do schema + UI
- Renomear labels conforme user pediu (ver seção Renomeação abaixo)

**AC:**
- Dashboard de Clareza Verbal tem 1 métrica ao invés de 2
- Nenhum campo mostra mesmo valor em posições diferentes

---

### 🐛 P0 BUG #3 — Contato visual 100 = máximo

**Sintoma:** Tela 5.png — "% contato visual: 100" tratado como ideal. Mas 100% de eye contact contínuo é agressivo / anormal. Banda ideal ≈ 70-90%.

**Arquivo provável:** `ml-worker/workers/gesture_analyzer.py` (ou subseção visual)

**Fix esperado:**
```python
def eye_contact_score(percent):
    # Curva em sino: pico entre 70-90, cai fora
    if 70 <= percent <= 90: return 100
    elif percent < 70: return (percent / 70) * 100
    else: return max(0, 100 - (percent - 90) * 5)  # 100% → 50
```

**AC:**
- 100% contato visual → score ~50 (penalizado como "staring")
- 85% → score 100
- 40% → score ~57
- Label ajustada para "Zona ideal: 70-90%"

---

### 🐛 P0 BUG #4 — Gesticulação score bidirecional

**Sintoma:** Tela 3 e 6 — "Variação Gesticulação: 49" e "Movimento propostial: 50" com escala ambígua. Pouco gesto é ruim (monótono). Muito gesto é ruim (distrai). Escala atual unidirecional não captura.

**Fix esperado:** escala bidirecional com banda ideal no meio.

**AC:**
- Score 100 quando gesticulação está na banda ideal (a definir via calibração — sugestão inicial: 60-80 gestos variados/min)
- Score degrada para ambos lados
- Label diferencia "Pouca variação" vs "Excesso / Distrai"

---

### 🟡 P1 #5 — Surface Congruence Score

**Contexto:** `ml-worker/workers/congruence_analyzer.py` JÁ EXISTE. Relatório atual **não mostra** score de congruência verbal-vocal-visual. É o red flag #1 do método Vinh ("palavras tristes + voz irritada = o cérebro da audiência desconfia").

**Ação:**
1. Verificar se `congruence_analyzer` é executado no pipeline (step 9.5 mencionado no handoff anterior)
2. Verificar se output é armazenado em `detailed_metrics`
3. Expor no `ScoreCard` como 7ª dimensão OU como badge especial no topo do relatório
4. Adicionar descrição: "Seu corpo, voz e palavras estão dizendo a mesma coisa?"

**Arquivo UI:** `apps/web/src/app/report/[id]/page.tsx`

**AC:**
- Score de congruência visível no relatório principal
- Drill-down mostra: momentos de incongruência detectados com timestamp
- Replay destaca esses momentos

---

### 🟡 P1 #6 — Surface Primeira Impressão (7s iniciais)

**Contexto:** `ml-worker/workers/opening_analyzer.py` JÁ EXISTE. Não surface no relatório atual.

**Justificativa Vinh:** "You are only as good as you can communicate. A primeira impressão se dá em 7 segundos. Se o opening é fraco, o resto não importa."

**Ação:**
1. Confirmar execução no pipeline
2. Expor como card destacado no topo do relatório ou como sub-score em Variedade Vocal / Presença
3. Replay tem marker visual nos primeiros 7s

**AC:**
- Relatório mostra "Opening Score: X/100" com feedback
- Card ou badge antes das 6 dimensões principais
- Link pra replay nos 7s iniciais

---

### 🟡 P1 #7 — Transparência do cálculo do score geral

**Sintoma:** 45/100 com 6 dimensões (14, 51, 62, 76, 82, 19). Média simples = 50.6. Resultado 45 → pesos não-uniformes não documentados.

**Ação:** expor pesos na UI com tooltip/accordion.

**Arquivo:** `apps/web/src/components/score-card.tsx` + `ml-worker/workers/aggregator.py`

**AC:**
- User clica no "45" e vê: "Variedade Vocal (peso 25%) + Prosódia (20%) + ..."
- Pesos ajustáveis via questionário de contexto (fase P3)
- Documentar matriz de pesos em `docs/scoring-weights.md`

---

### 🔵 P2 #8 — Storytelling Structure

**Gap:** Relatório avalia DELIVERY (como fala) mas não ARQUITETURA DA MENSAGEM (o que é dito). Zero cobertura de:
- Bridge sentence ("the reason I'm telling you this is because...")
- 4 Chemicals (Dopamine/Oxytocin/Endorphins/Cortisol)
- Estrutura narrativa (setup → build → climax → resolution)
- Opening hook + CTA (call to action) final

**Ação:** novo worker `storytelling_analyzer.py` usando LLM (Gemini 2.5 Flash já está no stack).

**Input:** transcript completo
**Output:**
```yaml
storytelling:
  has_opening_hook: bool
  opening_hook_type: "question|magic_trick|vulnerability|stat|story"
  has_bridge_sentence: bool
  bridge_timestamp: float
  chemicals_triggered: ["dopamine", "oxytocin"]
  structure_detected: "has_setup|has_climax|has_resolution"
  has_cta: bool
  cta_timestamp: float
  score: 0-100
```

**AC:**
- Nova dimensão "Narrativa" ou "Estrutura da Mensagem" no relatório
- Bridge sentence destacada no replay se encontrada
- Sugestões de bridge se ausente

**Observação de escopo:** pode ser faseado — primeiro só "has_bridge" + "has_cta" (regex + LLM simples), depois chemicals (mais complexo).

---

### 🔵 P2 #9 — Peaks/Troughs temporal (curva emocional)

**Gap:** "Variação de pitch: 21.6 semitons" é média. Inútil sem curva temporal.

**Ação:** enriquecer `variety_analyzer.py` para produzir série temporal + detectar picos e vales.

**Output:**
```yaml
emotional_curve:
  timestamps: [0, 15, 30, ...]
  emotional_intensity: [0.3, 0.8, 0.5, ...]
  peak_count: 5
  trough_count: 4
  distribution: "balanced|front_loaded|back_loaded|flat"
```

**AC:**
- Gráfico de linha no replay mostrando curva emocional
- Alerta se curva é "flat" (default do Vinh: "anytime anything becomes default, it becomes non-functional")

---

### 🔵 P2 #10 — Expressão facial

**Gap:** MediaPipe Face Mesh não está sendo usado. Smile/brow/micro-expressões são ~40% da percepção emocional.

**Ação:** novo worker `facial_analyzer.py` usando MediaPipe Face Landmarker.

**Métricas sugeridas:**
- Smile frequency (% do tempo)
- Smile variability (genuíno vs travado)
- Brow movement (engagement vs surpresa)
- Eye openness variation (atenção vs fadiga)

**AC:**
- 4 métricas no dashboard de Presença Visual
- Integradas ao Congruence Score

---

### 🔵 P2 #11 — Tonalidade emocional (5ª Vocal Foundation)

**Gap:** Cobrimos 4 das 5 foundations (rate, volume, pitch, pause). Falta **Tonality** — textura emocional do som.

**Ação:** adicionar análise VAD (valence/arousal/dominance) ao `voice_analyzer.py`. Biblioteca sugerida: `opensmile` ou `pyAudioAnalysis`.

**AC:**
- Sub-score "Tonalidade Emocional" em Voz e Prosódia
- Mapa emocional: "Sua voz soa: 70% neutra, 20% entusiasmada, 10% tensa"
- Feeds Congruence Score

---

### 🔵 P3 #12 — Scale-to-Room (contexto ajusta pesos)

**Gap:** Mesma régua para CEO em boardroom, vendedor em call, apresentador em palco.

**Ação:** questionário adiciona campo "tipo de apresentação" → aggregator aplica matriz de pesos contextual.

**Contextos propostos:**
- `boardroom_1on1` → peso maior em Postura/Clareza, menor em Gesticulação
- `small_group` → balanceado
- `stage_keynote` → peso maior em Variedade/Energia
- `video_solo` → peso maior em Expressão Facial/Opening
- `sales_call` → peso maior em Persuasão/CTA

**AC:**
- Questionário tem campo (já existe `identity_analyzer.py` — estender?)
- Aggregator aceita `context_profile` e ajusta pesos
- Relatório mostra: "Avaliado como: Sales Call"

---

## Renomeações pedidas pelo user (low-hanging fruit)

Anotações feitas diretamente nas screenshots. Apenas strings, zero lógica:

| Atual | Trocar por |
|-------|------------|
| PROSÓDIA | DICÇÃO |
| DEFAULT | PADRÕES |
| DIMENSÕES TRAVADAS | PILARES TRAVADOS |
| PITCH | TOM |
| SCORE | PONTUAÇÃO |
| WPM | PALAVRAS POR MINUTO |
| GROUNDING | ESTABILIDADE CORPORAL |
| Fillers | Vícios de Linguagem |
| Cluster de Fillers | Problemas de Fluência |
| Diversidade Lexical | Riqueza de Vocabulário |
| Fillers por minuto + Muletas por minuto | Vícios de Linguagem por Minuto (consolidado) |

**Arquivos:** todos os `apps/web/src/app/report/` + possivelmente labels em `detailed_metrics`.

---

## Pedidos específicos nas screenshots (diversos)

1. **Tela 2:** "Excluir Arquétipos Vocais da avaliação — colocar como extra a ser desbloqueado" (feature gating futuro, não-bloqueante)
2. **Tela 5:** "Zona e Distribuição Olhar deveriam ter peso menor" (cai no item #7 transparência de pesos)
3. **Tela 7:** "Faltou identificar o uso do 'né'" (regex do filler_detector provavelmente não pega 'né' — verificar lista de vícios)
4. **Tela 8:** conjunto "Lock-in Detectado + Anti-lockin + Cycling" tem redundância — consolidar num único "Variação de Arquétipos" com breakdown

---

## Validação sugerida antes de shipar

Depois de P0+P1, rodar novo vídeo de teste e confirmar:

- [ ] Score geral com pesos visíveis
- [ ] Congruence Score no topo
- [ ] Opening Score destacado
- [ ] Bugs 1-4 fixados (usar mesmo vídeo da screenshot pra comparar antes/depois)
- [ ] Renomeações aplicadas consistentemente
- [ ] Replay tem markers de Opening + Bridge + picos emocionais (se P2 feito)

---

## Files prováveis de tocar (resumo)

### Backend (ml-worker/workers/)
- `archetype_classifier.py` — bug #1
- `filler_detector.py` — bug #2, item #3 do "diversos"
- `gesture_analyzer.py` — bugs #3 e #4
- `congruence_analyzer.py` — verificar integração (item #5)
- `opening_analyzer.py` — verificar integração (item #6)
- `aggregator.py` — transparência pesos (#7) + scale-to-room (#12)
- `variety_analyzer.py` — peaks/troughs (#9)
- `voice_analyzer.py` — tonalidade VAD (#11)
- **NOVO:** `storytelling_analyzer.py` (#8)
- **NOVO:** `facial_analyzer.py` (#10)

### Frontend (apps/web/src/app/)
- `report/[id]/page.tsx` — UI geral + congruence + opening
- `report/[id]/[dimension]/page.tsx` — dashboards de dimensão
- `components/score-card.tsx` — transparência pesos
- Todas as strings de renomeação

### Schema
- Verificar `detailed_metrics` no Supabase comporta novos campos
- Possível migration se schema for rígido

---

## Uma última coisa

O app está no caminho certo. Não é que "avalia errado" — é que avalia o instrumento (piano) sem avaliar a música (o que a pessoa toca). Os P0 são higiene. Os P1 são quick wins com código já escrito (só falta surface). Os P2 transformam o produto de "medidor técnico" para "coach de comunicação de verdade".

Don't be so attached to the current schema that you don't give the future version a chance.

— **@vinh-giang**

Clone minds > create bots.
Acquisition brings satisfaction. Aplicar brings fulfillment.
