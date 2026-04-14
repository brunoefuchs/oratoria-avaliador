# Handoff de Pesquisa — Proximas Dimensoes para o Melhor App do Mundo

**Data:** 2026-04-14
**De:** @dev (Dex) — pesquisa + analise competitiva
**Para:** Avaliacao futura (Bruno + mentor)
**Status:** BACKLOG — considerar para Epic 7+

---

## Contexto

Apos completar Epics 4, 5 e 6 (espinha dorsal validada), foi feita pesquisa refinada para identificar o que falta para ter o **melhor app de analise de oratoria do mundo** focado em colaboradores de empresas.

---

## Mapa Competitivo — Estado da Arte (2026)

### Concorrentes diretos

| Tool | Foco | Metricas |
|------|------|----------|
| **Yoodli** | Meetings + practice | Pacing, tone, clarity, fillers, eye contact, body language, word choice, repetition, non-inclusive language, structure |
| **Poised** | Zoom/Teams meetings | Pace, fillers, tone, eye contact, confidence, empathy |
| **Orai** | Structured lessons | Pace, fillers, energy, clarity, confidence, facial expressions |
| **VirtualSpeech** | VR training | 10 workplace skills, immersive scenarios |

### O que JA TEMOS e nenhum concorrente tem (9 diferenciais)

1. **Variedade temporal (CV por janelas de 15s)** — mede variacao ao longo do tempo, nao so media
2. **4 Arquetipos vocais** — Educador/Coach/Motivador/Amigo com cycling detection
3. **Score de Identidade** — marcadores linguisticos de vicios emocionais + autoridade/vitima
4. **Analise de Abertura** — 7 tecnicas de conexao (pergunta reflexiva, dado chocante, etc)
5. **Congruencia entre canais** — cruza voz × postura × gesto (4 regras de contradicao)
6. **Arco temporal (3 tercos)** — abertura/meio/fechamento com padrao detectado
7. **Insights cruzados** — 10 regras combinando 2+ metricas em diagnostico composto
8. **Hierarquia de problemas** — ranking por impacto (weight × severity)
9. **Pesos contextuais** — 7 perfis de peso por motivacao do orador

---

## Pesquisa Cientifica Relevante

### Prosodia e Persuasao (Tilburg University, 2025)
- Prosodia alinhada com estrutura informacional aumenta percepcao de humanidade e personalizacao
- Fonte: https://www.tandfonline.com/doi/full/10.1080/0144929X.2024.2420871

### Velocidade Vocal e Persuasao (Journal of Nonverbal Behavior, 2024)
- 6 estudos (N=3.958): velocidade vocal tem relacao CURVILINEA com persuasao
- Rapido demais diminui efetividade (decelerating relationship)
- Fonte: https://link.springer.com/article/10.1007/s10919-024-00477-6

### Argument Mining (MIT Computational Linguistics)
- NLP pode detectar estrutura argumentativa (claims, evidencias, warrants)
- Modelos otimizam globalmente tipos de componentes e relacoes
- Fonte: https://direct.mit.edu/coli/article/45/4/765/93362/Argument-Mining-A-Survey

### Persuasividade Mensuravel (Frontiers in Communication, 2024)
- ML e NLP podem medir: Eloquencia, Especificidade, Relevancia, Evidencia
- Meios de persuasao: Ethos, Pathos, Logos
- Fonte: https://www.frontiersin.org/journals/communication/articles/10.3389/fcomm.2024.1457433/full

### Storytelling e Cerebro
- Historias ativam 7 regioes do cerebro simultaneamente (vs 2 para fatos)
- Oxitocina liberada durante vulnerabilidade aumenta empatia e confianca
- Fonte: https://pmc.ncbi.nlm.nih.gov/articles/PMC11487326/

---

## Parametros Propostos — O que Ninguem Mede

### TIER 1 — Implementavel AGORA (regex + transcript + prosodia existentes)

#### 1. Estrutura de Argumento (Logos)
- **O que:** Detectar se o orador tem ESTRUTURA ou esta divagando
- **Como:** Regex no transcript para marcadores argumentativos
  - Claim (afirmacao): "o servico X e o melhor porque..."
  - Evidence (dado/prova): numeros, "segundo pesquisa", "os dados mostram"
  - Example (exemplo concreto): "por exemplo", "imagine que"
  - Conclusion (fechamento): "portanto", "por isso", "em resumo"
- **Score:** % do tempo com estrutura vs divagacao
- **Esforco:** S | **Impacto:** ALTISSIMO
- **Diferencial:** Nenhum concorrente mede estrutura de argumento

#### 2. Energia Comunicativa (curva composta)
- **O que:** Combinar rate + volume + pitch + gesticulacao em curva temporal unica
- **Como:** `energia[janela] = (wpm_norm × 0.3 + volume_norm × 0.3 + pitch_norm × 0.2 + gesture_norm × 0.2)`
- **Visualizacao:** Curva de energia — "aqui voce estava no 3/10, aqui subiu pra 8/10"
- **Esforco:** S | **Impacto:** ALTO
- **Diferencial:** Ninguem mostra curva de energia composta

#### 3. Marcadores de Credibilidade (Ethos)
- **O que:** Contagem de recursos que transmitem autoridade na fala
- **Como:** Regex no transcript
  - Citacoes: "segundo", "de acordo com", "como disse"
  - Dados: numeros, porcentagens, estatisticas
  - Experiencia: "na minha experiencia", "trabalhei com X clientes"
  - Resultados: "conseguimos X%", "o resultado foi"
- **Esforco:** XS | **Impacto:** ALTO
- **Complementa:** Autoridade Transferida do Gui + Identity Analyzer

#### 4. Deteccao de CTA (Call to Action)
- **O que:** O orador termina com chamada para acao clara?
- **Como:** Regex nos ultimos 15% do transcript
  - Patterns: "faca isso", "entre em contato", "acesse", "comece agora", "o proximo passo e"
- **Score:** Existe CTA? E especifico? Esta no final?
- **Pesquisa:** Apresentacoes SEM CTA sao 40% menos efetivas
- **Esforco:** XS | **Impacto:** ALTO

#### 5. Repeticao Estrategica vs Acidental
- **O que:** Distinguir repeticao de ENFASE (anafora) de repeticao por FALTA DE VOCABULARIO
- **Como:** Contagem de palavras repetidas + analise de posicao
  - Estrategica: mesma frase repetida em posicoes de enfase (inicio de paragrafos)
  - Acidental: mesma palavra usada >3x em janela de 30s
- **Esforco:** S | **Impacto:** MEDIO-ALTO

#### 6. Deteccao de Mensagem-Chave
- **O que:** Qual e o conceito mais repetido/enfatizado? O orador reforçou o suficiente?
- **Como:** NLP basico — extrair top 3 conceitos mais frequentes no transcript
- **Pesquisa:** Mensagem repetida 3+ vezes tem 70% mais recall na audiencia
- **Score:** Mensagem-chave aparece < 2x = fraco, 3-5x = bom, 6+x = excelente
- **Esforco:** S | **Impacto:** ALTO

#### 7. Readability / Complexidade Lexical
- **O que:** A linguagem e adequada ao contexto?
- **Como:** Adaptacao do indice Flesch-Kincaid para PT-BR
  - Muito simples para apresentacao corporativa = falta de autoridade
  - Muito complexa para video de rede social = perde audiencia
- **Cruza com:** Contexto do questionario (motivacao)
- **Esforco:** S | **Impacto:** MEDIO

### TIER 2 — Implementavel com LLM (custo extra por chamada Gemini)

#### 8. Classificacao Ethos/Pathos/Logos
- **O que:** Classificar cada trecho do transcript no triangulo retorico
  - Ethos (credibilidade): citacoes, experiencia, autoridade
  - Pathos (emocao): historias, vulnerabilidade, humor
  - Logos (logica): dados, argumentos, evidencias
- **Como:** Chamada extra ao LLM com prompt especifico
- **Score:** Equilibrio entre os 3. Pesquisa mostra persuasao otima usa os 3
- **Esforco:** M | **Impacto:** ALTISSIMO

#### 9. Analise de Sentimento Temporal
- **O que:** Arco emocional — positivo → tensao → resolucao
- **Como:** LLM classifica sentimento de cada terco
- **Score:** Arco com variacao emocional > monotonia emocional
- **Esforco:** M | **Impacto:** ALTO

#### 10. Adequacao Audiencia-Linguagem
- **O que:** A complexidade da linguagem esta adequada ao contexto declarado?
- **Como:** Cruzar readability score com motivacao do questionario
- **Esforco:** S | **Impacto:** MEDIO

### TIER 3 — Futuro (requer ML dedicado)

#### 11. Expressao Facial / Micro-expressoes
- **O que:** Sorriso, sobrancelha, expressividade geral
- **MediaPipe Face:** 478 landmarks ja disponiveis
- **Complexidade:** Alta (calibragem necessaria)

#### 12. Reacao da Audiencia em Tempo Real
- **O que:** Engajamento da audiencia via dispositivos
- **Requer:** App complementar ou integracao com plataformas de video

---

## Ranking de Priorizacao (para o mentor avaliar)

| # | Parametro | Esforco | Impacto | Diferencial | Prioridade |
|---|-----------|---------|---------|-------------|-----------|
| 1 | **Estrutura de Argumento** | S | ALTISSIMO | Unico no mercado | ⭐⭐⭐ |
| 2 | **Energia Comunicativa** | S | ALTO | Visualizacao unica | ⭐⭐⭐ |
| 3 | **Marcadores de Credibilidade** | XS | ALTO | Complementa identity | ⭐⭐⭐ |
| 4 | **CTA Detection** | XS | ALTO | Corporativo precisa | ⭐⭐⭐ |
| 5 | **Mensagem-Chave** | S | ALTO | "Reforçou sua mensagem?" | ⭐⭐ |
| 6 | **Repeticao Estrategica** | S | MEDIO-ALTO | Refinamento de vicios | ⭐⭐ |
| 7 | **Readability** | S | MEDIO | Adequacao ao contexto | ⭐⭐ |
| 8 | **Ethos/Pathos/Logos** (LLM) | M | ALTISSIMO | Ninguem faz auto | ⭐⭐ |
| 9 | **Sentimento Temporal** (LLM) | M | ALTO | Arco emocional | ⭐ |
| 10 | **Adequacao Audiencia** | S | MEDIO | Cruza com questionario | ⭐ |

---

## Visao do Produto "Melhor do Mundo" — 5 Camadas

### Camada 1 — Tecnica Vocal ✅ (temos)
Variedade, WPM, pitch, volume, pausas, monotonia, arquetipos

### Camada 2 — Presenca Fisica ✅ (temos)
Gesticulacao ativa, contato visual, postura, zona gestual, congruencia

### Camada 3 — Identidade e Abertura ✅ (temos)
Score de identidade, tecnicas de abertura, vicios emocionais

### Camada 4 — Conteudo e Estrutura 🔜 (proposto)
Estrutura argumentativa, mensagem-chave, CTA, marcadores de credibilidade

### Camada 5 — Impacto e Persuasao 🔜 (proposto)
Energia comunicativa, repeticao estrategica, Ethos/Pathos/Logos

### Total: 5 camadas × ~30 metricas = a analise mais completa que existe

---

## Para o Colaborador Corporativo

O que um lider/vendedor/apresentador precisa que NINGUEM oferece:

1. "Minha apresentacao teve ESTRUTURA?" → Argument score
2. "Eu fui PERSUASIVO?" → Ethos/Pathos/Logos balance
3. "A audiencia vai LEMBRAR?" → Mensagem-chave reinforcement
4. "Eu terminei com DIRECAO CLARA?" → CTA detection
5. "Minha ENERGIA foi adequada?" → Curva de energia
6. "Eu transmiti CREDIBILIDADE?" → Marcadores de autoridade
7. "Eu EVOLUI?" → Dashboard de evolucao (ja temos)

---

## Nota sobre UI

Bruno atualizou o frontend com design system novo (Material Design 3 tokens, AppShell, ghost-border, ai-pulse, stage-ambient, fluency-wave). Todas as paginas (home, questionario, report, replay, evolution, shared) foram atualizadas com o novo visual. Os componentes (ScoreCard, VideoPlayer, Onboarding, StarRating) tambem foram redesenhados.

**Essas mudancas de UI sao independentes do backend** — nao afetam o pipeline ML nem os analyzers. O frontend esta mais profissional e pronto para apresentar ao mentor/investidores.

---

## Proximos Passos

1. **Bruno + mentor avaliam** quais parametros do Tier 1 implementar primeiro
2. **@architect** faz spec arquitetural das features escolhidas
3. **@sm** cria stories
4. **@po** valida
5. **@dev** implementa

**Recomendacao:** Comece pelos 4 XS/S do Tier 1 (Estrutura de Argumento, Credibilidade, CTA, Energia). Sao 4-5 dias de trabalho para um salto de diferenciacao brutal.

---

## Sources da Pesquisa

- [Yoodli AI](https://yoodli.ai/)
- [Poised AI](https://www.poised.com/)
- [Orai AI](https://orai.com/)
- [Prosody and Persuasion - Tilburg University 2025](https://www.tandfonline.com/doi/full/10.1080/0144929X.2024.2420871)
- [Vocal Speed and Persuasion - Springer 2024](https://link.springer.com/article/10.1007/s10919-024-00477-6)
- [Argument Mining Survey - MIT](https://direct.mit.edu/coli/article/45/4/765/93362/Argument-Mining-A-Survey)
- [Decoding Persuasion - Frontiers 2024](https://www.frontiersin.org/journals/communication/articles/10.3389/fcomm.2024.1457433/full)
- [Measuring LLM Persuasiveness - ArXiv](https://arxiv.org/html/2410.02653v2)
- [Speech Prosody SIG](https://www.sprosig.org/)
- [Impactful Presentations - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC11487326/)
- [AI Tools for Public Speaking - Unite.AI](https://www.unite.ai/best-ai-tools-for-public-speaking/)
- [Duarte AI Platform Review](https://www.duarte.com/blog/review-of-public-speaking-ai-platforms/)
