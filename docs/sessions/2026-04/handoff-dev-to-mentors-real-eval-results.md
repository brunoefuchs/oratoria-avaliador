# Handoff: Resultados de Avaliacao Real → @gui-reginatto + @vinh-giang

**Data:** 2026-04-09
**De:** @dev (Dex)
**Para:** @gui-reginatto (avaliador de produto) + @vinh-giang (workflow de oratoria)
**Contexto:** Primeiro teste end-to-end completo do produto Oratoria Avaliador apos Epic 4 + Epic 5

---

## Para que serve este handoff

Este documento contem **dados reais de uma avaliacao end-to-end** do produto. O objetivo e:

1. **@gui-reginatto:** Avaliar o que mais podemos colocar no produto. O que esta faltando? Que dimensao adicional de avaliacao traria mais valor? Quais features de UX precisam de polish?

2. **@vinh-giang (modo workflow):** Rodar o workflow de oratoria nestes resultados — o orador tem dimensoes para mais avaliacoes? Como podemos melhorar a metodologia para extrair mais insights deste mesmo video?

---

## Estado do Produto

### Stack Tecnico
- **Frontend:** Next.js 14 + Tailwind (port 3000)
- **API:** FastAPI (port 8002)
- **ML Worker:** FastAPI + MediaPipe + Whisper + Parselmouth (port 7860)
- **Database:** Supabase (DB + Storage)
- **LLM:** Gemini 2.5 Flash

### Pipeline ML (10 steps)
1. Splitting → audio + video
2. Postura (MediaPipe Pose)
3. Gestos + olhar (MediaPipe Hand + Face)
4. Voz (Whisper + Parselmouth)
5. Vicios de linguagem (regex + classificacao contextual)
6. Variedade (meta-analise temporal de janelas 15s)
7. Arquetipos vocais (extra)
8. Buscar contexto do orador (questionario)
9. Aggregator (pesos contextuais por tipo de apresentacao)
9.5. Congruencia (cruzamento entre canais)
9.6. Analise temporal (3 tercos)
10. Report LLM (Gemini com contexto, congruencia, temporal, guard rails)

### 5 Dimensoes Avaliadas (+ 1 extra)
| Dimensao | Peso default | O que mede |
|----------|--------------|------------|
| Variedade Vocal | 29% | CV temporal de volume, tom, velocidade, gesticulacao |
| Voz e Diccao | 24% | WPM, tom, volume, pausas, anti-monotonia |
| Presenca Visual | 18% | Contato visual, gesticulacao, duas maos, zona, distribuicao olhar |
| Postura | 18% | Alinhamento, postura aberta, estabilidade, movimento |
| Clareza Verbal | 11% | Vicios de linguagem, hesitacoes, problemas de fluencia |
| Arquetipos (extra) | — | 4 arquetipos: Educador, Coach, Motivador, Amigo |

### Analises Avancadas (Epic 5)
- **Congruencia:** Detecta contradicoes entre canais (4 regras)
- **Arco Temporal:** Performance por terco (abertura/meio/fechamento)
- **Pesos Contextuais:** 7 perfis (palco, podcast, vendas, etc)

---

## Resultados da Avaliacao Real

**Video:** 53.85 segundos, 168 palavras, contexto generico (sem questionario preenchido)

### Score Geral: **56/100**

### Scores por Dimensao
| Dimensao | Score | Diagnostico |
|----------|-------|-------------|
| **Postura** | 77 | Boa — alinhamento 91, postura aberta 100%, ombros 98% |
| **Presenca Visual** | 76 | Boa — contato visual 100%, duas maos 82% |
| **Clareza Verbal** | 76 | Boa — 5 vicios em 53s, sem clusters |
| **Voz e Diccao** | 51 | Mediano — WPM 187 (acima do ideal 130-170), pausas 38 |
| **Variedade Vocal** | 14 | **Critico** — 83.6% tempo monotono |
| **Arquetipos** (extra) | 19 | Lock-in no "amigo" |

### Sub-scores Voice (Voz e Diccao = 51)
| Componente | Score |
|------------|-------|
| Pitch Score | 100 (range 21.6 semitons — excelente!) |
| Velocidade Score | 51 |
| WPM Score | 46 (187 wpm — acima do ideal 130-170) |
| Pausa Score | 38 (so 17.6% das pausas sao estrategicas) |
| **Volume Score** | **20** (CV de volume = 0.0031 — quase zero variacao!) |

### Detalhes do Audio
- WPM: 187 (acima do ideal 130-170)
- WPM por janela: [188, 180, 204] — acelerou no final
- Pitch medio: 113.5 Hz
- Range de pitch: 21.6 semitons (faixa rica, **mas pouco usada**)
- CV pitch: 0.0419 (baixo)
- CV volume: **0.0031** (quase zero — voz muito uniforme em volume)
- Volume medio: 67 dB
- Pausas: 3 estrategicas, 1 hesitacao, 13 respiracao

### Vicios de Linguagem (5 em 53s = 5.6/min)
| Vicio | Quantidade | Categoria |
|-------|-----------|-----------|
| `aí` | 2x | muleta_conexao |
| `sabe` | 1x | muleta_retorica |
| `então,` | 1x | muleta_conexao |

### Gesticulacao
- Gesticulation pct: **100%** (gesticulando o tempo todo — pode ser excesso)
- Duas maos: 82%
- Vocabulario de gestos: 5 (ideal: 6+)
- Gesto repetitivo: detectado
- Zona ideal pct: **1.5%** (gestos quase sempre fora da zona peito-cintura — apos correcao Epic 4!)

### Olhar
- Eye contact: 100%
- Olhar baixo: 0%
- Distribuicao olhar: provavelmente baixa (camera unica)

### Postura
- Alignment score: 91
- Open posture: 100%
- Ombros nivelados: 98.1%
- Grounding (estabilidade corporal): 60
- Movimento proposital: 50
- Padrao: misto

### Variedade Vocal — A Maior Fragilidade
- pct_tempo_monotono: **83.6%**
- Diagnostico: muito_monotono
- Defaults detectados: velocidade, volume, entonacao

### Arquetipos
- Dominante: amigo (100%)
- Lock-in: True
- Trocas por minuto: 0
- Ausentes: educador, coach, motivador

### Congruencia
- Score: 100/100
- Diagnostico: alta_congruencia
- Contradicoes detectadas: 0

### Arco Temporal (3 tercos)
| Terco | Score | Insight |
|-------|-------|---------|
| Abertura | 61 | Comecou mediano |
| Meio | **80** | Pico (zero monotonia, zero vicios) |
| Fechamento | 74 | Caiu um pouco |

**Padrao detectado:** PICO no meio. Bom para argumentacao, ruim para abertura/fechamento.

---

## Feedback do LLM (Gemini)

### Resumo Gerado
"Olá! Que bom que você deu esse primeiro passo. É um prazer guiá-lo nesta jornada para destravar sua comunicação. Sua capacidade de manter o contato visual e a postura aberta são pontos de partida incríveis, mostrando seu potencial para se conectar genuinamente. A maior oportunidade agora é explorar a vasta gama de possibilidades de sua voz para que sua mensagem ressoe com ainda mais impacto e evite a previsibilidade."

### Top 3 Forcas Identificadas pelo LLM
1. **Conexao Visual Impecavel** (100% contato visual)
2. **Postura Confiante e Aberta** (alignment 91, postura aberta 100%)
3. **Vasta Faixa de Tom Vocal** (pitch range 21.6 semitons — instrumento rico)

### Top 5 Melhorias (Regra 80/20) Geradas
1. **Desbloquear Variedade Vocal** — fala 83.6% previsivel
2. **Pausas Estrategicas Conscientes** — apenas 17.6% das pausas sao estrategicas
3. **Gesticulacao Proposital e Controlada** — gesto repetitivo, fora da zona ideal
4. **Aprimorar Estabilidade Corporal** — grounding 60, movimento proposital 50
5. **Reduzir Vicios de Linguagem** — 5.6/min, principalmente "aí", "sabe", "então"

---

## Replay (Story 5.6)

### Eventos detectados na timeline
- 0 Clusters de vicios
- 5 Vicios isolados (em pontos especificos do video)
- 0 Pausas estrategicas marcadas (apesar de 3 contadas no voice — possivel bug de mapeamento)
- 0 Hesitacoes marcadas (apesar de 1 contada — possivel bug de mapeamento)

### Limitacao Atual
A timeline tem 3 lanes (vicios, pausas estrategicas, hesitacoes) mas as pausas estrategicas e hesitacoes contadas no voice_analyzer NAO estao aparecendo como eventos. Provavel bug de chave/formato.

---

## Perguntas para o @gui-reginatto

1. **O que falta no produto?** Vendo essas dimensoes, scores e UX, o que deveria existir e nao existe?

2. **Onde tem oportunidade de adicionar valor?** Seguindo o feedback do mentor de oratoria, quais features ainda nao foram implementadas que poderiam virar diferencial?

3. **UX/UI:** O dashboard, replay, evolucao, questionario pre-avaliacao — algum esta confuso ou pode ser melhorado?

4. **Produto vs Servico:** Faz sentido o produto puro (self-service) ou precisamos de uma camada human-in-the-loop?

---

## Perguntas para o @vinh-giang (modo workflow)

**Voce e o mentor de oratoria. Olhe para esses resultados e responda:**

1. **Mais dimensoes possiveis:** Com os dados brutos que ja temos (audio, video, frames, transcricao com word-level timestamps), que outras dimensoes de avaliacao poderiamos extrair? Ja temos:
   - MediaPipe (pose, hand, face landmarks)
   - Whisper (transcricao com timestamps)
   - Parselmouth (analise de prosodia: pitch, formants, intensity)
   - FFmpeg (audio/video processing)

2. **Insights nao explorados:** Olhe os dados detalhados (ranges, CVs, arco temporal, congruencia). Tem algo importante que nao estamos extraindo ou comunicando ao orador?

3. **Metodologia:** O scoring atual e baseado em formulas heuristicas (sem ML real). Esta calibrado bem o suficiente? Algum threshold parece errado?

4. **Coaching:** O LLM gerou 5 melhorias prioritarias. Voce concorda com a priorizacao? Adicionaria/removeria algo?

5. **Replay/Visualizacao:** Como voce gostaria de ver os insights na timeline do video? O que falta visualmente para o orador "se ver"?

---

## Stories Implementadas (16 total)

### Epic 4 — Ajustes do Mentor (calibracao + terminologia)
- 4.1 Fix scoring bugs (zona, olhar, "ne")
- 4.2 Renomear terminologia (Prosodia→Diccao, Pitch→Tom, etc)
- 4.3 Remover Arquetipos do score principal
- 4.4 Ajustar pesos de zona/olhar
- 4.5 Exercicios sucintos no LLM
- 4.6 [Spike] Voice/Variety contradiction (pendente)

### Epic 5 — Raio-X do Mentor (camada humana)
- 5.1 Quick wins (icones, copy, guard rails LLM)
- 5.2 Questionario pre-avaliacao (5 perguntas)
- 5.3 Pesos contextuais (7 perfis)
- 5.4 Dashboard de evolucao
- 5.5 Analise temporal (3 tercos)
- 5.6 Replay com timeline anotada
- 5.7 Dimensao de Congruencia
- 5.8 Fillers contextuais
- 5.9 Onboarding + CTAs
- 5.10 Compartilhamento de relatorio

---

## O que NAO foi implementado (Backlog)

1. **Analise de expressao facial** (mentor pediu — fora de escopo Epic 5)
2. **ML real substituindo heuristicas** (todo o scoring e formula heuristica)
3. **Spike 4.6** — investigar contradicao voice 51 vs variety 14
4. **Deploy publico** — roda 100% local, com cloudflared tunnel para mostrar
5. **Sistema de auth completo** — usa user_token UUID no localStorage

---

## Codigo nao commitado (working tree)

```
M apps/api/app/routes/evaluations.py (replay endpoint refatorado, 5 tipos eventos)
M apps/web/src/components/video-player.tsx (3 lanes + getStyle defensivo)
M apps/web/src/app/report/[id]/replay/page.tsx (stats cards + olhar baixo warning)
?? apps/web/src/app/report/[id]/shared/page.tsx (pagina nova)
```

Estes arquivos ainda nao estao no remoto. Bruno solicitou esse handoff antes de commit.

---

## Como reproduzir o teste

```bash
./dev.sh           # sobe os 3 servicos
# acessa http://localhost:3000
# faz upload de um video (max 5min)
# preenche ou pula o questionario
# aguarda ~2min de processamento
# explora o relatorio: dashboard, dimensoes, replay, evolucao
```

Video real testado: `e4359918-9b31-4e6b-901d-390933cbfa39` (53s, 168 palavras)
