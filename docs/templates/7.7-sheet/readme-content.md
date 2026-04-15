# Ground Truth Humano — Avaliação de Oratória (Story 7.7)

## Contexto

Este sheet é parte do projeto **oratoria-avaliador** (IA de avaliação de oratória em vídeo).

**Seu papel:** avaliar manualmente 10 vídeos de oratória contra uma rubric estruturada, para calibrar a acurácia do modelo de ML.

**Mentor avaliador:** Guilherme Reginatto
**Formato:** offline, blind test (sem ver o que o app gerou antes)
**Sessões:** 3-4 sessões de ~45min, máx 3 vídeos por sessão

---

## Como preencher

### Escala 0-100 (incrementos de 10)

Use APENAS múltiplos de 10: 0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100.

| Banda | Nível | O que significa |
|-------|-------|-----------------|
| 0-20 | Crítico | Compromete a mensagem; precisa refazer |
| 21-40 | Fraco | Visível pro público; atrapalha |
| 41-60 | Mediano | Passa, mas não marca |
| 61-80 | Bom | Soma pra mensagem |
| 81-100 | Excelente | Profissional; gera conexão |

### Protocolo blind

- NÃO peça pro Bruno ver o que o modelo gerou antes de você pontuar.
- Preencha cada vídeo SOZINHO, sem consultar scores do app.
- Após completar um vídeo, faça 5min de pausa antes do próximo.

---

## Dimensões (10 + overall)

1. **Posture** — postura corporal: estabilidade, abertura, peso, tensão/relaxamento
2. **Gesture** — gesticulação: amplitude, intenção, naturalidade, sincronia com fala
3. **Voice** — voz: projeção, articulação, dicção, ritmo, respiração
4. **Fillers** — muletas ("né", "tipo", "aaahh", "então"): frequência, impacto
5. **Variety** — variedade: pausas estratégicas, variação de velocidade/volume
6. **Archetypes** — arquétipos: qual persona domina? (guerreiro/sábio/bobo/herói/cuidador/criador/rebelde/mago/inocente/amante/explorador/governante)
7. **Identity** — identidade: linguagem de autoridade vs vítima
   - VÍTIMA: "deixaram", "não pude", "sempre acontece comigo", "não é justo"
   - AUTORIDADE: "eu escolhi", "fiz", "decidi", "aqui está"
8. **Opening** — abertura (primeiros 20% da fala): técnica usada (impacto/pergunta/dado/história/quebra-gelo/provocação/nenhuma)
9. **Congruence** — congruência palavra vs corpo vs voz
10. **Temporal** — arco temporal (abertura/meio/fechamento). Vídeos <30s: marcar N/A
11. **Overall** — nota final INDEPENDENTE + 3 campos (força principal, fraqueza principal, impressão geral)

---

## Overall — 3 campos estruturados

Para cada vídeo, preencher 3 campos (mín 30 caracteres cada):

- **overall_forca_principal** — o que mais puxou a nota pra cima?
- **overall_fraqueza_principal** — o que mais puxou a nota pra baixo?
- **overall_impressao_geral** — em 1 frase, que tipo de orador é esse?

---

## Fluxo completo

1. **Passo 0 — Briefing (30min, 1x):** Bruno explica contexto, você esclarece dúvidas. Sem ver relatório do app.
2. **Passo 1A — Calibração solo:** Você assiste 1 vídeo de treino e preenche a aba `Calibração` SOZINHO. Sem Bruno.
3. **Passo 1B — Calibração revisão:** Bruno compara seus scores com os do app. Se divergência ≤20 em todas dimensões → PASS. Se >20 em alguma dimensão, Bruno dá feedback qualitativo (sem revelar scores do app) e você revisa.
4. **Passo 2 — Ground truth (3-4 sessões):** Ordem randomizada, máx 3 vídeos/sessão, 5min intervalo, preenche aba `Ground Truth`.
5. **Passo 3 — Consolidação:** Bruno roda script automatizado pra preencher aba `Comparação`.

---

## Enums aceitos (dropdown)

**archetypes_arquetipo_principal:** guerreiro / sábio / bobo / herói / cuidador / criador / rebelde / mago / inocente / amante / explorador / governante

**identity_vicios_observados (multi-select):** vitimização / comparação / rejeição / culpa / injustiça

**opening_tecnica_usada:** impacto / pergunta / dado / história / quebra-gelo / provocação / nenhuma

---

## Dúvidas frequentes

**P: E se eu não souber pontuar uma dimensão?**
R: Use a escala. 41-60 é "mediano/neutro" — use quando não há sinal forte pra cima nem pra baixo.

**P: Vídeo muito curto (<30s) — como avaliar temporal?**
R: Marcar `temporal_score = N/A`. Arco não se forma em fala curta.

**P: Arquétipo múltiplo?**
R: Escolha o DOMINANTE em `archetypes_arquetipo_principal`. Se quiser, cite secundário em `archetypes_notas`.

**P: Vídeo impressiona mas não se encaixa na escala?**
R: Preencha as 10 dimensões com os descritores. Use `overall_score` + 3 campos de texto pra capturar o que a rubric não pegou.
