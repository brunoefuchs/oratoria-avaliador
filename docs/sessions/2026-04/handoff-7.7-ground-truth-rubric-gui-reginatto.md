# Handoff 7.7 — Ground Truth Humano (Guilherme Reginatto) | Rubric + Protocolo

**Data:** 2026-04-15 (v2 — pós-QA refinements)
**Autor:** @oalanicolas (Alan Nicolas)
**Revisor:** @qa Quinn (CONCERNS → refinamentos R1-R4 aplicados)
**Story:** 7.7 (parte da tríade 7.6/7.7/7.8 — Harness de Convergência Multi-IA)
**Mentor avaliador:** Guilherme Reginatto
**Vídeos:** 10 (ground truth baseline do Epic 7)
**Formato:** Google Sheets offline
**Protocolo:** Blind test (Gui não vê scores do modelo antes)

**Change Log v2 (2026-04-15):**
- R1: descritores intermediários (21-40 e 61-80) adicionados em todas 10 dimensões
- R2: escala mudou de múltiplos de 5 → múltiplos de 10 (reduz fadiga decisória)
- R3: calibração em 2 fases (Gui solo → Bruno revisa depois sem revelar scores)
- R4: `overall_justificativa` substituído por 3 campos estruturados (força/fraqueza/impressão)

---

## 1. Propósito

Estabelecer a **verdade externa** contra a qual medir a acurácia do pipeline de ML.

- Harness (7.6) mede **consistência** entre 3 IAs (convergência ≥85%)
- Ground truth (7.7) mede **acurácia** contra humano expert
- Distância `|app_score - gui_score|` por dimensão = erro do modelo

**Sem rubric estruturada, ground truth vira opinião. Com rubric = 10 medidas.**

---

## 2. Decisões de protocolo

| Decisão | Valor | Razão |
|---------|-------|-------|
| Formato | Google Sheets | Estrutura + cálculo de distância + validação de range |
| Blind | Gui NÃO vê scores do modelo antes | Evita anchoring bias (AN013) |
| Ordem | Randomizada (shuffle dos 10 vídeos) | Evita ordering effect |
| Overall | Gui pontua separado das 10 dim + 3 campos estruturados (força/fraqueza/impressão) | Compara app-overall vs gui-overall com rationale auditável |
| Vídeos/sessão | Máx 3 por sessão (30-45min de trabalho) | Evita fadiga do avaliador |
| Calibração | 1 vídeo em 2 fases (Gui solo → Bruno revisa SEM revelar scores) | Evita leak de scores do app durante calibração |
| Intervalo | Mín 5min entre vídeos | Reset cognitivo |
| Escala | Múltiplos de 10 (0,10,20…100) | Reduz ~50% das decisões vs múltiplos de 5, mantém sinal |

---

## 3. Escala de pontuação — ancoragem comum

Todas as dimensões usam a **mesma escala 0-100** com descritores ancorados em **5 bandas**:

| Banda | Descritor geral | Interpretação |
|-------|-----------------|---------------|
| 0-20 | Crítico | Compromete a mensagem; precisa refazer |
| 21-40 | Fraco | Visível pro público; atrapalha |
| 41-60 | Mediano | Passa, mas não marca |
| 61-80 | Bom | Soma pra mensagem |
| 81-100 | Excelente | Profissional; gera conexão |

**Gui pontua em incrementos de 10** (0, 10, 20, 30… 90, 100). 11 níveis possíveis.

---

## 4. Rubric por dimensão — 10 dimensões (5 bandas cada)

### 4.1 Posture (postura corporal)
**O que avaliar:** estabilidade, abertura, peso distribuído, tensão/relaxamento.

| Banda | Descritor específico |
|-------|---------------------|
| 0-20 | Corpo fechado, encolhido, balança muito ou trava |
| 21-40 | Postura oscilante ou travada; tensão visível |
| 41-60 | Postura neutra, sem marca positiva nem negativa |
| 61-80 | Postura estável com abertura razoável |
| 81-100 | Postura firme, aberta, ocupa o espaço com segurança |

### 4.2 Gesture (gesticulação)
**O que avaliar:** amplitude, intenção, naturalidade, sincronia com fala.

| Banda | Descritor específico |
|-------|---------------------|
| 0-20 | Gestos travados, repetitivos ou ausentes |
| 21-40 | Gestos mecânicos ou limitados; pouca intenção |
| 41-60 | Gesticula sem intenção clara, mecânico |
| 61-80 | Gesticula com intenção; às vezes ilustra, às vezes não |
| 81-100 | Gestos ilustrativos, variados, reforçam a mensagem |

### 4.3 Voice (voz — projeção, articulação, velocidade)
**O que avaliar:** clareza da dicção, volume, ritmo, respiração.

| Banda | Descritor específico |
|-------|---------------------|
| 0-20 | Voz baixa, arrastada ou acelerada, dicção ruim |
| 21-40 | Voz irregular (ora baixa, ora alta); dicção inconsistente |
| 41-60 | Voz audível mas sem presença, ritmo monocórdio |
| 61-80 | Voz clara e audível; ritmo adequado mas sem grande dinâmica |
| 81-100 | Voz projetada, articulada, ritmo vivo |

### 4.4 Fillers (muletas — "né", "tipo", "aaahh", "então")
**O que avaliar:** frequência, tipo, impacto na mensagem.

| Banda | Descritor específico |
|-------|---------------------|
| 0-20 | Muitas muletas por minuto; frase travada por elas |
| 21-40 | Muletas frequentes mas mensagem ainda passa |
| 41-60 | Muletas ocasionais, não atrapalha entendimento |
| 61-80 | Muletas raras; quase não notam |
| 81-100 | Praticamente sem muletas; fala limpa |

### 4.5 Variety (variedade — ritmo, pausas, dinâmica)
**O que avaliar:** uso de pausas estratégicas, variação de velocidade/volume.

| Banda | Descritor específico |
|-------|---------------------|
| 0-20 | Monocórdio, sem pausa, sem variação |
| 21-40 | Variação ocasional mas sem intenção |
| 41-60 | Alguma variação, mas previsível |
| 61-80 | Variação consciente em algumas passagens |
| 81-100 | Ritmo dramático, pausas potentes, dinâmica alta |

### 4.6 Archetypes (arquétipos comunicacionais)
**O que avaliar:** qual persona domina? (guerreiro, sábio, bobo, herói, etc.) — há consistência ou troca errática?

| Banda | Descritor específico |
|-------|---------------------|
| 0-20 | Sem persona definida; parece performance vazia |
| 21-40 | Persona inconsistente; vacila entre arquétipos |
| 41-60 | Persona aparece mas sem compromisso |
| 61-80 | Arquétipo identificável mas com momentos de dissonância |
| 81-100 | Arquétipo claro, consistente, autêntico |

### 4.7 Identity (identidade — linguagem de autoridade vs vítima)
**O que avaliar:** a pessoa se POSICIONA? usa linguagem própria ou de vítima/culpa?

**Marcadores de VÍTIMA:** "deixaram", "não pude", "sempre acontece comigo", "não é justo"
**Marcadores de AUTORIDADE:** "eu escolhi", "fiz", "decidi", "aqui está"

| Banda | Descritor específico |
|-------|---------------------|
| 0-20 | Linguagem de vítima dominante; culpa externa |
| 21-40 | Autoridade aparece em alguns momentos; vitimização ainda domina |
| 41-60 | Mix — ora autoridade, ora vitimização |
| 61-80 | Autoridade dominante; vitimização ocasional |
| 81-100 | Linguagem de autoridade dominante; dono da própria história |

### 4.8 Opening (abertura — primeiros 20% da fala)
**O que avaliar:** usou técnica profissional? (frase de impacto, pergunta reflexiva, dado chocante, gancho com história, quebra-gelo, provocação).

| Banda | Descritor específico |
|-------|---------------------|
| 0-20 | Entrou "cru"; começou sem conectar |
| 21-40 | Tentou técnica mas executou fraco (hook fraco) |
| 41-60 | Tentou abrir mas sem força |
| 61-80 | Abertura competente; gera interesse |
| 81-100 | Hook forte; gerou atenção imediata |

### 4.9 Congruence (congruência — palavra vs corpo vs voz)
**O que avaliar:** o que diz BATE com como diz? tem coerência entre verbal, corporal, vocal?

| Banda | Descritor específico |
|-------|---------------------|
| 0-20 | Incongruente (ex: diz "estou confiante" mas corpo fechado) |
| 21-40 | Dissonâncias visíveis em momentos-chave |
| 41-60 | Parcialmente congruente |
| 61-80 | Majoritariamente congruente com dissonâncias pontuais |
| 81-100 | Alta congruência; corpo/voz/palavra em sintonia |

### 4.10 Temporal (arco temporal — abertura / meio / fechamento)
**O que avaliar:** a fala tem arco? abertura puxa, meio sustenta, fechamento fecha?

**Nota:** vídeos <30s podem ter `temporal_score = N/A` (campo nullable — arco não se forma em fala curta).

| Banda | Descritor específico |
|-------|---------------------|
| 0-20 | Sem arco; entra e sai sem estrutura |
| 21-40 | Arco parcial; faltou estrutura em 1-2 partes |
| 41-60 | Tem abertura OK mas fechamento fraco (ou vice-versa) |
| 61-80 | Arco presente mas alguma parte poderia ser mais forte |
| 81-100 | Arco completo; abre, desenvolve, fecha |

### 4.11 Overall (impressão geral — **independente**)
**O que avaliar:** SE Gui tivesse que dar UMA nota final de oratória, qual seria? (sem derivar das 10).

Pontuação `overall_score` (0-100, múltiplo de 10) + **3 campos de justificativa estruturada** (mín 30 chars cada):

- `overall_forca_principal` — o que mais puxou a nota pra cima?
- `overall_fraqueza_principal` — o que mais puxou pra baixo?
- `overall_impressao_geral` — em 1 frase, que tipo de orador é esse?

Serve pra medir se o **peso** que o app aplica está calibrado com a percepção humana + dá rationale auditável pós-hoc.

---

## 5. Template Google Sheets — estrutura de abas

### Aba 1: `README`
- Contexto do projeto
- Como preencher
- Escala 0-100 ancorada (5 bandas × descritores por dimensão)
- Protocolo (blind, ordem, intervalo, calibração 2 fases)
- Rubric de referência deve ficar visível (frozen row) durante preenchimento

### Aba 2: `Calibração`
- 1 vídeo de treino, preenchido em 2 fases:
  - **Fase 1A:** Gui sozinho (sem Bruno)
  - **Fase 1B:** Bruno revisa DEPOIS, dá feedback qualitativo, NÃO revela scores do app
- NÃO vai pro ground truth final

### Aba 3: `Ground Truth` (principal)

| Coluna | Tipo | Validação |
|--------|------|-----------|
| video_id | UUID | — |
| ordem_apresentacao | 1-10 (random) | — |
| posture_score | 0-100 | múltiplo de 10 |
| posture_notas | texto | opcional |
| gesture_score | 0-100 | múltiplo de 10 |
| gesture_notas | texto | opcional |
| voice_score | 0-100 | múltiplo de 10 |
| voice_notas | texto | opcional |
| fillers_score | 0-100 | múltiplo de 10 |
| fillers_notas | texto | opcional |
| variety_score | 0-100 | múltiplo de 10 |
| variety_notas | texto | opcional |
| archetypes_score | 0-100 | múltiplo de 10 |
| archetypes_arquetipo_principal | enum (guerreiro/sábio/bobo/herói/cuidador/criador/rebelde/mago/inocente/amante/explorador/governante) | — |
| archetypes_notas | texto | opcional |
| identity_score | 0-100 | múltiplo de 10 |
| identity_vicios_observados | multi-select (vitimização/comparação/rejeição/culpa/injustiça) | — |
| identity_notas | texto | opcional |
| opening_score | 0-100 | múltiplo de 10 |
| opening_tecnica_usada | enum (impacto/pergunta/dado/história/quebra-gelo/provocação/nenhuma) | — |
| opening_notas | texto | opcional |
| congruence_score | 0-100 | múltiplo de 10 |
| congruence_notas | texto | opcional |
| temporal_score | 0-100 ou N/A | múltiplo de 10, nullable se vídeo <30s |
| temporal_notas | texto | opcional |
| overall_score | 0-100 | múltiplo de 10 |
| overall_forca_principal | texto | **obrigatório, min 30 chars** |
| overall_fraqueza_principal | texto | **obrigatório, min 30 chars** |
| overall_impressao_geral | texto | **obrigatório, min 30 chars** |
| duracao_avaliacao_min | número | — |
| data_avaliacao | data | — |

### Aba 4: `Comparação` (preenchida DEPOIS pelo app via `scripts/compare-ground-truth.py`)
- Scores do app por dimensão
- Scores do Gui
- Distância absoluta `|app - gui|`
- Distância média por dimensão
- Flag vermelho se distância >20 em qualquer dimensão

---

## 6. Protocolo de execução com Gui

### Passo 0 — Briefing (30min, 1x só)
- Bruno explica contexto do projeto
- Mostra a rubric + as 10 dimensões
- **NÃO mostra** nenhum relatório do app
- Responde dúvidas

### Passo 1 — Calibração (em 2 fases — R3)

**Fase 1A:** Gui assiste vídeo de calibração SOZINHO e preenche aba `Calibração`. Bruno não participa.

**Fase 1B:** Bruno revisa DEPOIS:
- Compara scores do Gui com scores do app (só Bruno vê)
- Se divergência ≤20 em todas dimensões → PASS, segue pro passo 2
- Se divergência >20 em alguma dimensão:
  - Bruno dá feedback **qualitativo** pro Gui (ex: "na dimensão X, reli sua nota e acho que você foi muito severo — pode revisar?")
  - Bruno **NUNCA** revela o score exato do app
  - Gui revisa com base no feedback qualitativo
  - Se ainda >20 após revisão → recalibra do zero com OUTRO vídeo de calibração
- Se >5 dimensões fora em 1ª tentativa → recalibra do zero

### Passo 2 — Ground Truth (3-4 sessões de 45min)
- Por sessão: máx 3 vídeos
- Ordem randomizada (decidida antes)
- Gui preenche sozinho (sem Bruno junto)
- Mín 5min entre vídeos
- **BLIND:** sem acesso a relatórios do app

### Passo 3 — Consolidação
- Bruno roda o app nos 10 vídeos (ou puxa resultados do Supabase)
- Roda `scripts/compare-ground-truth.py` → aba `Comparação` preenchida
- Calcula distâncias
- Flag dimensões com distância >20 (threshold de erro)

---

## 7. Critérios de sucesso (7.7 DONE)

- [ ] Calibração zero PASS (divergência Gui↔app ≤20 em todas dimensões, conforme Bruno revisar)
- [ ] 10 vídeos avaliados com rubric preenchida
- [ ] Todas as 3 justificativas (força/fraqueza/impressão) preenchidas em todos os 10 vídeos (≥30 chars cada)
- [ ] Planilha consolidada com aba `Comparação` calculada via script
- [ ] Report final: distância média por dimensão + flags >20

---

## 8. Handoff — o que falta agora

### Para mim (@oalanicolas) — DONE
- [x] Rubric estruturada (10 dimensões + overall em 3 campos)
- [x] Protocolo anti-viés (blind, ordem, intervalo, calibração 2 fases)
- [x] Plano de calibração zero
- [x] Estrutura da planilha
- [x] R1-R4 aplicados pós-QA

### Para @dev Dex
- [x] CSV template (`docs/templates/7.7-ground-truth-rubric.csv`) — **precisa atualizar** pra refletir 31 colunas novas (3 campos de overall + temporal nullable)
- [x] Script consolidação (`scripts/compare-ground-truth.py`) — pronto
- [ ] Criar Google Sheet real a partir do CSV atualizado com data validation

### Para @qa Quinn
- [ ] Re-validar rubric v2 (R1-R4 aplicados) — gate retest
- [ ] Revisar fase 1A/1B da calibração antes de liberar passo 2

### Para @devops Gage
- [x] Cherry-pick 7.6 (Bruno resolveu em outro terminal)
- [ ] Rodar 10 vídeos no pipeline quando Bruno selecionar
- [ ] Rodar harness multi-IA (budget USD 5)

### Para Bruno
- [ ] Selecionar os 10 vídeos baseline (critério: variedade de contextos + durações)
- [ ] Selecionar vídeo de calibração (1 vídeo representativo, não incluído nos 10)
- [ ] Briefing com Gui (30min)
- [ ] Executar Passo 1 Fase 1A (Gui solo)
- [ ] Executar Passo 1 Fase 1B (Bruno revisa sem revelar scores)

---

## 9. Riscos monitorados (v2)

| Risco | Mitigação |
|-------|-----------|
| Gui pontua com anchoring do app | Protocolo blind obrigatório + calibração 2 fases + Bruno nunca revela scores |
| Fadiga degrada qualidade após vídeo 5+ | Máx 3/sessão + 5min intervalo + múltiplos de 10 (menos decisões) |
| Rubric ambígua → scores inconsistentes | Calibração zero + descritores 5 bandas + rubric visível frozen row |
| Gui esquece critérios da dimensão X | README da planilha + rubric no frozen header |
| Bruno influencia durante avaliação | Gui solo no passo 2 + Bruno só dá feedback qualitativo na fase 1B |
| Vídeos não representam o range real | Bruno curadoria consciente: curto/médio/longo, bom/ruim/médio |
| Vídeos muito curtos distorcem temporal | `temporal_score` nullable se <30s (R7 aplicado parcialmente) |

---

## 10. Referências

- Story 7.6 (Harness): cherry-picked pelo Bruno em outro terminal
- Calibração V3: `docs/sessions/2026-04/calibration-reference-values-v3.md`
- Memória da sessão anterior (oalanicolas): `epic7_convergence_harness.md`
- QA Gate v1: `docs/qa/7.7-rubric-validation.md` (verdict CONCERNS → refinamentos R1-R4)
- CSV template: `docs/templates/7.7-ground-truth-rubric.csv`
- Script consolidação: `scripts/compare-ground-truth.py`
- Analyzers atuais no pipeline: 10 dimensões validadas (posture/gesture/voice/fillers/variety/archetypes/identity/opening/congruence/temporal)
- Epic 7 stories adicionando 3 dimensões novas (storytelling/facial/tonality) — **ainda não em produção**. Ground truth desta rodada cobre só as 10 atuais. Próxima rodada expande.

---

— @oalanicolas · *Curadoria > Volume. Triangulação > fonte única. (AN014)*
