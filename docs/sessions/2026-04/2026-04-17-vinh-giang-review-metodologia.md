# Revisão Vinh Giang — Auditoria Metodológica dos Mentores

**Data:** 2026-04-17
**Agente:** Vinh Giang (squad-creator-pro)
**Contexto:** Bruno trouxe a auditoria Rodenburg+Love (2026-04-16) pro Vinh revisar, considerando que já existe uma nova proposta de pesos em construção em paralelo (state-of-the-art, Epic 9).
**Objetivo:** decidir se adota as sugestões dos mentores, ajusta ou rejeita — dentro das limitações de vídeos curtos.
**Eval-âncora:** `494693f0-785f-403c-8583-da172ef93570` (54s, 166 palavras)

---

## 1. O que Vinh MANTÉM da auditoria (3 acertos ouro)

### 1.1 `monotonia_score` descartado é o bug filosófico do sistema
Rodenburg/Love viram. Vinh reforça com reframe pedagógico:
- **Pitch range = CAPACIDADE** (quais teclas o piano tem)
- **Monotonia = USO** (quais teclas o orador de fato toca)

O código calcula ambos mas só usa capacidade. Esse é o elefante.

**Fix obrigatório:** `pitch_final = 0,5·range_score + 0,5·(100 − monotonia_score)`

### 1.2 Archetypes: `qualidade_dominante` 40% é autossabotagem
Mentores sugeriram 40% → 15%. Vinh concorda e endurece:
> "Anytime anything becomes default, it becomes non-functional."

A fórmula atual **premia** o lock-in que a pedagogia inteira **condena**. Eval 494693f0 tirou 45 com arquétipo travado em amigo 100% — deveria ser ~25.

### 1.3 Posture: buckets `plantado=90 > proposital=80` estão invertidos
Sintoma da mesma doença: sistema recompensa **forma correta parada** em vez de **forma correta em movimento consciente**.

---

## 2. Onde Vinh AJUSTA a proposta dos mentores

### 2.1 Volume 25% (Love) — agressivo demais pra vídeos de celular
**Problema:** `cv_volume` é ultra-sensível a condições técnicas — distância ao mic, compressão do celular, pós-processamento. Dar 25% pro cv_volume = dar 25% pra qualidade do microfone.

**Proposta Vinh:**
- Manter volume em **20%**
- **Normalizar pelo baseline do próprio vídeo** (variação relativa, não absoluta)
- Expor `cv_volume_note` quando detectar clipping/compressão ("confiança reduzida — áudio com compressão")

### 2.2 Pausa 25% (Love) sem separar estratégica vs respiratória
**Problema:** mentores identificaram o problema mas não resolveram. Aumentar peso de métrica confusa **amplifica ruído**.

**Proposta Vinh:**
- Manter pausa em **20%** até o pré-requisito técnico
- Split obrigatório em 2 sub-métricas:
  - `pausa_estrategica` (≥2s antes de ponto-chave)
  - `pausa_respiratoria` (involuntária, meio de frase)
- Só subir pra 25% DEPOIS do split

---

## 3. O que OS DOIS mentores não viram

### 3.1 Confidence Score por dimensão (vídeo curto)
**Observação Vinh:** este vídeo tem 54s. Archetypes rodou com 5 janelas de 10s. "Lock-in amigo 100%" com n=5 é falsa precisão. Identity corretamente retornou `dados_insuficientes` — mas outras dimensões não têm guard equivalente.

**Proposta Vinh — Tier de Confidence por duração:**

| Duração | Tier | Dimensões com confiança ALTA |
|---------|------|------------------------------|
| <60s | Smoke | posture, gesture básico, fillers |
| 60–180s | Standard | + voice, archetypes (baixa conf) |
| 180s+ | Full | + storytelling, identity |

Exibir score + confidence interval. Score sem confidence é falsa precisão — pior que score errado.

### 3.2 Storytelling ausente do eval
`ml-worker/workers/storytelling_analyzer.py` existe, mas **não aparece no eval 494693f0** (nem nos 7 rows de `analysis_results`). Status desconhecido — configuração? skip? falha silenciosa?

**Veredito Vinh:** storytelling + Bridge Structure + 4 Chemicals são **50% do impacto** em oratória real. Ignorar isso pra otimizar pesos de posture é **trocar pneu com motor desligado**.

**Ação:** investigar por que storytelling não rodou ANTES de re-balancear pesos existentes.

### 3.3 Princípio "Play vs Capacity" generalizado
Não é problema isolado do pitch. É **padrão sistêmico**:

| Dimensão | Métrica de capacidade | Métrica de uso | Status |
|----------|----------------------|----------------|--------|
| voice/pitch | `pitch_range_semitones` | `monotonia_score` | **descartado** |
| gesture | `vocabulario_gestos`, `gesticulation_pct` | uso de vocabulário, repetição | parcial (penalty −15) |
| archetypes | presença/ausência | cycling, anti_lockin | parcial (v3 autossabotada) |
| variety | — | — | **skipped** (ironia) |
| posture | `open_posture_pct`, `alignment` | `dinamismo`, `proposital` | parcial (buckets invertidos) |

**Proposta Vinh:** auditoria sistemática dos analyzers com a pergunta: *"Isso mede capacidade ou uso?"* Capacidade é baseline barato; uso é o que diferencia orador medíocre de magnético.

---

## 4. Decisão sobre a nova proposta de pesos

**Continuar com a nova proposta — com 3 correções:**

1. **Incorporar os 3 acertos dos mentores** (monotonia_score, rebalance archetypes, inverter buckets posture)
2. **NÃO adotar volume 25% nem pausa 25%** sem pré-requisitos técnicos (normalização; split de pausa)
3. **Adicionar ao roadmap** (Epic 9 ou novo):
   - Confidence score + tier por duração
   - Investigação do storytelling_analyzer
   - Auditoria "capacity vs use" em TODOS os analyzers

---

## 5. Limitação fundamental do vídeo 54s

**Veredito honesto Vinh:** 54s é **insuficiente pra avaliação completa de oratória**. Não é falha do sistema — é falha do input.

**Recomendações UX:**
- Vídeos <60s recebem análise parcial explícita
- Vídeos <120s recebem warning "análise completa requer 2+ min"
- Vídeos ≥180s recebem análise full
- Gerenciar expectativa via UI protege o sistema de falsa precisão

---

## 6. Próximos Passos

1. Confirmar com @architect quais das 3 correções entram no Epic 9 em andamento vs novo epic
2. Investigar `storytelling_analyzer.py` — por que não rodou no eval 494693f0?
3. Design do sistema de Confidence Score + tier por duração
4. Definir especificação técnica pra split `pausa_estrategica` / `pausa_respiratoria`
5. Rodar re-scoring nos 10 vídeos ground truth (Story 7.7) antes/depois das correções

---

**Relação com auditoria anterior:** complementar, não substituta. Rodenburg+Love fizeram análise PEDAGÓGICA das fórmulas. Vinh fez análise SISTÊMICA — o que falta, o que é prematuro adotar, onde estão os elefantes não-endereçados.

**Referências:**
- `docs/sessions/2026-04/2026-04-16-metodologia-audit-eval-494693f0.md` (auditoria Rodenburg+Love)
- `/home/bruno/.claude/projects/-mnt-c-Users-bruno-code-oratoria-avaliador/memory/epic9_approved_conditional_roadmap.md`
- `squads/squad-creator-pro/agents/vinh-giang.md`
- `ml-worker/workers/storytelling_analyzer.py` (pendente investigação)
