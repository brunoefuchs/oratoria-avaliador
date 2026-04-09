# Feedback Consolidado dos Mentores — Vinh Giang + Gui Reginatto

**Data:** 2026-04-09
**Contexto:** Apos teste end-to-end real do produto (video de 53s, overall_score=56), 2 mentores avaliaram os resultados em modo workflow para indicar o que adicionar.
**Status:** Backlog para Epic 6 — "Camada de Identidade e Resultado"

---

## Sumario Executivo

**Vinh Giang** (perspectiva tecnica/metodologica) → "Cruze as metricas que ja tem para gerar insights compostos. Voce tem o instrumento, falta tocar."

**Gui Reginatto** (perspectiva humana/identidade) → "Voce mede CAPACIDADE mas ignora IDENTIDADE. O produto e um avaliador de oratoria tecnica — precisa virar um destravador de comunicacao com autoridade."

**Big insight combinado:**
> Os 2 mentores concordam: o produto **ja tem dados suficientes**. O gap nao e mais ML ou mais features, e **camada de inteligencia sobre os dados existentes** + **link com identidade e resultado**.

---

## PARTE 1 — Vinh Giang (Workflow Mode)

### Forcas reconhecidas no produto

1. **Capturou o principio da variedade** — pct_tempo_monotono e o "default = non-functional" em codigo
2. **Divisao em arquetipos** — identifica lock-in (orador 100% Friend)
3. **Pausas classificadas em 3 tipos** (estrategicas/hesitacao/respiracao) — raro no mercado
4. **Arco temporal em 3 tercos** — ouro coaching (abre fraco, pico no meio, fecha medio)
5. **Congruencia entre canais** — cruza voz com postura (analise antes so humana)

### Defaults do produto identificados por Vinh

1. **Score por dimensao isolada** — sempre apresenta isolado, vira monotono
2. **Tudo passa por LLM no final** — texto generico se nao alimentar com insights especificos
3. **Foco em "o que esta ruim"** — forcas subdiagnosticadas

### Top 5 melhorias propostas (Vinh — 80/20)

#### 1. INSIGHTS CRUZADOS (a maior oportunidade)

**O ouro esta nos cruzamentos:**

| Cruzamento | Diagnostico Composto |
|-----------|---------------------|
| Pitch range alto (21.6) + CV pitch baixo (0.04) | "Voce tem o instrumento mas nao toca" |
| WPM 187 + CV velocidade 0.05 | "Voce fala rapido E sempre na mesma velocidade — dois problemas que se amplificam" |
| Gesticulation 100% + Zona ideal 1.5% | "Voce gesticula o tempo todo, mas fora da zona de poder" |
| Archetype Friend 100% + base volume 9.6/10 | "Voce e amigavel mas grita o tempo todo — Friend nao deveria estar nesse volume" |

**Acao:** Criar camada `insights_cruzados` que combina metricas de duas dimensoes para gerar diagnosticos compostos. LLM precisa receber esses cruzamentos ja prontos.

#### 2. EXTRAIR ENFASE — Onde estao os PEAKS de volume?

Cruzar **timestamps de palavras (Whisper)** com **intensidade por frame (Parselmouth)** para detectar quais palavras receberam volume alto. Resposta: **"Voce enfatizou as palavras certas?"**

**Exemplo:** "Voce enfatizou 'cliente' (boa escolha) e 'meio' (palavra de transicao — desperdicio)."

#### 3. OPENING IMPACT — Os primeiros 7 segundos

Refinar o arco temporal para distinguir:
- **Primeiros 7 segundos** (a primeira impressao real)
- **Resto do primeiro terco** (consolidacao)

Implementacao: Pega os primeiros 14 frames (7s a 2fps) e calcula um sub-score de "primeira impressao".

#### 4. VARIEDADE DE COMPRIMENTO DE FRASES

Voce mede WPM mas nao **variedade no tamanho das frases**. Detecta separacao por pontuacao no transcript:
- Tamanho medio de frase
- CV de tamanho de frase
- Frase mais curta / mais longa

**Insight chave:** Frase curta apos longa = enfase. *"E falhei."* curto disparado.

#### 5. WHISPER MOMENTS — Onde voce sussurrou?

Detectar momentos onde o orador BAIXOU o volume intencionalmente (>30% drop em relacao a media local). **Whisper moments = momentos de poder.** O orador esta criando intimidade.

### 5 dimensoes adicionais possiveis (Vinh)

| Dimensao Nova | Dados disponiveis | Esforco | Impacto |
|---------------|-------------------|---------|---------|
| **Sincronizacao gesto-palavra** | MediaPipe hands + Whisper timestamps | Medio | Alto |
| **Variedade de comprimento de frase** | Whisper transcript | Baixo | Alto |
| **Padroes de respiracao** | Pausas de respiracao + volume | Baixo | Medio |
| **Movimento de cabeca** | MediaPipe face landmarks | Baixo | Medio |
| **Whisper moments** (volume drops) | Parselmouth intensity | Baixo | **Alto** |

### Hierarquia de problemas (faltando no produto)

Vinh apontou que o produto apresenta scores como lista plana, mas precisa ter **ranking de problemas por impacto**. Para o video testado, a ordem correta seria:

1. **Volume completamente flat** (CV 0.0031) → causa raiz da monotonia
2. **Lock-in no Friend** (100%) → arquetipo unico
3. **WPM 187 + sem variacao** → fala rapido E uniforme
4. **Gesto fora da zona ideal** (1.5%) → distrai
5. **Vicios isolados** (5 em 53s) → menor impacto

Hoje sao apresentados como lista plana — falta a hierarquia.

### Mensagem final do Vinh

> "A diferenca entre um app util e um app transformador nao esta em adicionar mais metricas. Ja tem metrica suficiente. A diferenca esta em: cruzar as metricas para gerar insights compostos, hierarquizar os problemas (1, 2, 3 — nao lista plana), mostrar antes de explicar (replay com marcadores ja faz), trazer a camada humana (Epic 5 ja faz com o questionario)."

---

## PARTE 2 — Gui Reginatto (Workflow Mode)

### Diagnostico bruto

> "Voce construiu uma ferramenta que mede CAPACIDADE. Mas comunicacao nao se trava em capacidade — comunicacao se trava em IDENTIDADE. E voce ta ignorando isso completamente."

### Confronto

> "O seu produto, hoje, e um Vinh Giang automatizado. Excelente medidor tecnico. Mas falta a camada de identidade, crencas e merecimento. E mais: falta o link com resultado financeiro."

### Reframe central

**Nao e um avaliador de oratoria. E um destravador de comunicacao.**

| Como avaliador (atual) | Como destravador (proposto) |
|----------------------|------------------------|
| "Quao bom voce fala?" | "O que esta te impedindo de comunicar com autoridade?" |
| Mede tecnica | Diagnostica bloqueio |
| Da nota | Da caminho |
| Faz a pessoa se sentir avaliada | Faz a pessoa se sentir diagnosticada |
| Resultado: relatorio | Resultado: transformacao |

### Raio-X em 3 Niveis aplicado ao produto

#### Nivel 1 — EMOCIONAL/IDENTIDADE (onde o produto esta perdendo o jogo)

**1. O questionario nao toca em IDENTIDADE.**

Adicionar 3 perguntas-mae:
- *"Quem voce acredita ser quando esta falando em publico?"* (Identidade)
- *"Voce acredita que tem o direito de ser ouvido?"* (Merecimento)
- *"O que aconteceria com sua vida se voce falasse com 100% de autoridade?"* (Visualizacao da identidade futura)

**2. Vicios emocionais nao sao detectados na fala.** Os 5 vicios deixam marcadores linguisticos especificos no transcript:

| Vicio | Marcadores na fala |
|-------|-------------------|
| **Vitimizacao** | "nao consigo", "e muito dificil", "ninguem me ajuda", "sempre me acontece" |
| **Comparacao** | "diferente do fulano", "todo mundo tem", "menos que os outros" |
| **Rejeicao** | "vao me julgar", "nao vou conseguir", "ninguem vai acreditar" |
| **Culpa** | "desculpa", "nao sei se posso", "espero nao estar atrapalhando" |
| **Injustica** | "deveria ser diferente", "nao e justo", "errado isso" |

**Acao:** Criar `identity_analyzer.py` que faz match desses padroes no transcript do Whisper. Output: **Score de Identidade**.

**3. Linguagem de Autoridade vs Linguagem de Vitima:**

| Linguagem de Autoridade | Linguagem de Vitima |
|------------------------|---------------------|
| "Eu vou" | "Eu tento" |
| "A melhor forma e" | "Talvez funcione" |
| "Faca isso" | "Quem sabe voce poderia" |
| "Eu sei" | "Eu acho" |
| "Funciona assim" | "Pode ser que" |

Detectavel via regex + contagem. **Mais importante que vicios de linguagem.**

#### Nivel 2 — COMUNICACAO (onde esta forte mas pode aprofundar)

**4. 5 Canais de Autoridade — voce mede 4, falta 1.**

- ✅ Visual (postura, gestos)
- ✅ Fala (voz, dicao)
- ✅ Corporal (presenca)
- ✅ Emocional (parcial — congruencia)
- ❌ **Transferida** (FALTA — prova social, credenciais, contexto)

**Acao:** Adicionar campo no questionario:
- "Quem ja te recomendou publicamente?"
- "Que credenciais voce mencionaria sobre voce mesmo?"
- "Qual a sua maior prova social?"

LLM avalia: "Voce nao usou nenhuma prova social no video. Voce tem [X], por que nao mencionou?"

**5. Sincronia Limbica.** Voce mede contato visual em %, mas nao mede QUALIDADE. MediaPipe Face tem 478 landmarks — extrair:

- Frequencia de micro-sorriso
- Movimento de sobrancelhas (engajamento)
- Inclinacao de cabeca (interesse)
- Largura do olhar (relaxamento vs tensao)

Sincronia limbica e o "warmth" — mais critico que % de contato visual.

**6. Automodelagem em 3 Etapas.** Implementar player com 3 modos:

- **Modo Completo** (atual): video com audio
- **Modo Audio-Only:** so audio (forca focar na voz)
- **Modo Mute:** so imagem (forca focar no corpo)

Zero custo computacional. **25% de melhoria comprovada** segundo Gui.

#### Nivel 3 — PERSUASAO/RESULTADO (onde esta zerado)

**7. Link com RESULTADO FINANCEIRO.** O Big Idea do Gui:

> "Voce nao ganha pouco porque o mercado e ruim. Voce ganha pouco porque nao sabe se comunicar com autoridade."

Adicionar ao questionario:
- "Qual o objetivo financeiro com sua comunicacao?" (vender curso, fechar projeto, ser promovido)
- "Quanto voce quer ganhar nos proximos 12 meses?"
- "Quanto vale uma melhoria de 10% na sua taxa de conversao?"

**O relatorio muda completamente o tom.** Em vez de "voce esta monotono", vira:

> **"Sua monotonia esta custando R$ X mil por mes."**

Isso e o que faz o cara abrir a carteira. Ninguem paga por melhoria abstrata. Todo mundo paga por diminuir prejuizo.

**8. Maieutica Socratica.** Adicionar secao "**Perguntas para voce refletir**" no relatorio:
- "Por que voce escolheu esse tom?"
- "Que mensagem voce queria passar com esse gesto?"
- "Para quem voce ta falando? Quem ta do outro lado?"

Em vez de afirmar, perguntar. Descoberta gera mudanca real.

**9. Encantamento vs Persuasao.** Persuasao convence pelo argumento. Encantamento conquista pela emocao.

**Como capturar encantamento:**
- Pico emocional (intensidade vocal × tom × gesto sincronizado)
- Momentos de vulnerabilidade (palavras emocionais + drop de volume + pausa)
- Storytelling (estrutura narrativa via NLP basico)

**10. Plano de Exposicao Progressiva.** Substituir o plano de 12 semanas atual (orientado por habilidades) por um caminho de **risco crescente**:

| Semanas | Foco | Por que |
|---------|------|---------|
| 1-2 | Story do Instagram (24h, baixo risco) | Treina identidade segura |
| 3-4 | Reels curtos (permanente mas curto) | Aumenta exposicao |
| 5-6 | Lives ao vivo | Forca presenca em tempo real |
| 7-9 | Palco virtual (zoom com 5 pessoas) | Treina presenca social |
| 10-12 | Palco fisico (pequeno publico) | Consolidacao |

### Top 7 adicoes propostas (Gui — priorizadas)

| # | Adicao | Impacto | Esforco |
|---|--------|---------|---------|
| 1 | **Score de Identidade** (marcadores linguisticos vicios + autoridade) | ALTISSIMO | BAIXO |
| 2 | **3 perguntas-mae no questionario** (identidade, merecimento, futuro) | ALTISSIMO | BAIXO |
| 3 | **Calculo financeiro do impacto** (R$ perdido por mes) | ALTISSIMO | MEDIO |
| 4 | **Modo Automodelagem** (player com 3 visualizacoes) | ALTO | BAIXO |
| 5 | **Maieutica Socratica no relatorio** (perguntas) | ALTO | BAIXO |
| 6 | **Plano de Exposicao Progressiva** | MEDIO | MEDIO |
| 7 | **Sincronia Limbica** (qualidade do olhar) | MEDIO | MEDIO |

### Mensagem final do Gui

> "As pessoas nao compram melhoria de oratoria. As pessoas compram a identidade nova de 'alguem que merece ser ouvido'. Esse e o produto que voce precisa entregar. E isso nao e adicionar 10 features. E reposicionar o produto. Voce tem todos os dados que precisa. O que falta nao e mais ML, e mais CAMADA HUMANA."

---

## PARTE 3 — Backlog Consolidado (Epic 6: Camada de Identidade e Resultado)

### Stories propostas (priorizadas por ROI)

#### Wave 1 — Quick Wins de Identidade (impacto altissimo, esforco baixo)

| Story | Origem | Descricao |
|-------|--------|-----------|
| **6.1** | Gui | **Score de Identidade** — analyzer linguistico de vicios emocionais + linguagem de autoridade no transcript |
| **6.2** | Gui | **3 perguntas-mae no questionario** — identidade, merecimento, futuro |
| **6.3** | Vinh | **Insights cruzados** — combinar 2 metricas em 1 diagnostico composto (Pitch range × CV pitch, WPM × CV velocidade, etc) |
| **6.4** | Gui | **Maieutica Socratica** — secao "Perguntas para refletir" no prompt do LLM |
| **6.5** | Gui | **Modo Automodelagem** — player com 3 modos (completo / audio-only / mute) |

#### Wave 2 — Resultado Financeiro

| Story | Origem | Descricao |
|-------|--------|-----------|
| **6.6** | Gui | **Calculo financeiro do impacto** — pergunta objetivo financeiro + R$ perdido por mes no relatorio |
| **6.7** | Vinh | **Hierarquia de problemas** — ranking dos issues por impacto (1, 2, 3 — nao lista plana) |

#### Wave 3 — Profundidade da Analise (insights novos com dados existentes)

| Story | Origem | Descricao |
|-------|--------|-----------|
| **6.8** | Vinh | **Whisper moments** — detecta volume drops intencionais (momentos de poder) |
| **6.9** | Vinh | **Sincronizacao gesto-palavra** — alinhamento timestamps Whisper × MediaPipe |
| **6.10** | Vinh | **Variedade de comprimento de frase** — NLP basico no transcript |
| **6.11** | Vinh | **Opening Impact** — primeiros 7s como sub-score |

#### Wave 4 — Camada Humana Avancada

| Story | Origem | Descricao |
|-------|--------|-----------|
| **6.12** | Gui | **Autoridade Transferida** — campo de prova social no questionario |
| **6.13** | Gui | **Sincronia limbica** — micro-sorriso, sobrancelha, inclinacao via MediaPipe Face |
| **6.14** | Gui | **Plano de Exposicao Progressiva** — substituir plano atual por risco crescente |
| **6.15** | Vinh | **Movimento de cabeca** (variedade) via MediaPipe face landmarks |

### Stories que **NAO** devem ser implementadas agora

Vinh foi enfatico: **"Nao adiciona mais 6 dimensoes — vai matar voce. Adiciona inteligencia AS metricas que ja existem."**

Backlog para Epic 7 (futuro):
- Match palavra-emocao (NLP + tonalidade — alto esforco)
- ML real substituindo heuristicas
- Analise de expressao facial completa

---

## PARTE 4 — Insights Convergentes dos 2 Mentores

### Os 2 mentores concordam em:

1. **Os dados ja existem** — nao precisa mais ML, precisa mais inteligencia sobre os dados
2. **Cruzar e mais importante que adicionar** — Vinh fala em insights cruzados, Gui fala em camadas (identidade × capacidade × merecimento)
3. **A camada humana e o gap** — Vinh menciona "trazer a camada humana", Gui constroi todo argumento sobre identidade
4. **Hierarquizar problemas** — ambos criticam apresentar tudo como lista plana
5. **O LLM precisa de mais contexto** — ambos dizem que o output do LLM esta generico porque o input nao e suficiente
6. **Forcas estao subdiagnosticadas** — ambos apontam que "Pitch range 21.6" e tratado como mero numero quando deveria ser EXPLORADO

### Diferenca de enfase:

| Vinh | Gui |
|------|-----|
| Foca em **variedade tecnica** | Foca em **identidade emocional** |
| 88 keys, peaks and troughs | Piramide I→C→M, vicios emocionais |
| 12 semanas por habilidade | 12 semanas por exposicao progressiva |
| Metodologia de coaching | Resultado financeiro e identidade |

**Os 2 sao complementares.** Implementar so um deixa o produto manco. Implementar os 2 da o produto que o mercado precisa.

---

## PARTE 5 — Action Items Imediatos

### Para validar no proximo sprint (1 semana, conforme Gui sugeriu)

1. ✅ **Adicionar 3 perguntas-mae no questionario** (identidade, merecimento, futuro) — Story 6.2
2. ✅ **Detectar marcadores linguisticos de vicios emocionais no transcript** — Story 6.1
3. ✅ **Adicionar pergunta de objetivo financeiro** — base para Story 6.6
4. ✅ **Reescrever o prompt do LLM** para usar essas tres camadas

**Teste:** Reprocessar o mesmo video (e4359918-9b31-4e6b-901d-390933cbfa39) com essas mudancas e comparar relatorio antes/depois.

### Metricas de sucesso

- O score de identidade aparece no relatorio
- O LLM menciona o link financeiro pelo menos 1x
- O relatorio muda de tom conforme as respostas do questionario novo
- O orador "se ve" na avaliacao (qualitativo, via feedback do mentor)

---

## Apendice — Dados do Video Testado

**Video ID:** e4359918-9b31-4e6b-901d-390933cbfa39
**Duracao:** 53.85s
**Palavras:** 168

### Scores
- Overall: 56
- Postura: 77
- Presenca Visual: 76
- Clareza Verbal: 76
- Voz e Diccao: 51
- Variedade Vocal: 14
- Arquetipos (extra): 19

### Top metricas relevantes para os mentores
- WPM: 187 (acima do ideal 130-170)
- Pitch range: **21.6 semitons** (instrumento rico — Vinh)
- CV pitch: 0.0419 (instrumento sub-utilizado)
- CV volume: **0.0031** (quase zero variacao — problema #1)
- Eye contact: 100%
- Open posture: 100%
- Gesticulation: 100%
- Zona ideal pct: 1.5%
- pct_tempo_monotono: 83.6%
- Archetypes: 100% Friend (lock-in)
- Pausas: 3 estrategicas / 1 hesitacao / 13 respiracao
- Arco temporal: 61 → 80 → 74 (pico no meio)
- Vicios: 5 em 53s (`aí` 2x, `sabe`, `então`, +1)

### Padroes detectados pelos mentores

**Vinh:** "Voce tem o instrumento mas nao toca" (pitch range alto + CV baixo)

**Gui:** "Lock-in no Friend + base volume 9.6 = voce e amigavel mas grita o tempo todo"

---

**Status:** Backlog pronto para virar Epic 6. Aguardando decisao sobre priorizacao e inicio de implementacao.
