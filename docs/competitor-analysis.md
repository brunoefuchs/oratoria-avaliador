# Competitive Analysis Report: Oratória Avaliador

**Data:** 2026-04-14
**Analista:** Atlas (@analyst)
**Produto:** Oratória Avaliador — IA que avalia vídeos de oratória em PT-BR
**Escopo:** Brasil (primário) + benchmarks globais relevantes
**Companion doc:** `docs/market-research.md`

---

## 1. Executive Summary

**Situação competitiva atual:**

O mercado brasileiro de comunicação/oratória corporativa é **bipolar e descoordenado**:

- **Lado "BR tradicional"** (SOAP, Reinaldo Polito, Conquer, Óh Quem Fala) — alta brand equity, clientes enterprise, zero SaaS/IA. Vendem **horas de consultor humano**.
- **Lado "AI-first global"** (Yoodli, Orai, Poised, Speeko, VoxAI) — tech moderna, zero presença BR, idioma = inglês. Vendem **software escalável**.

**Ninguém ainda ocupa a interseção**: *"AI nativa em português + entendimento de contexto corporativo brasileiro"*. Esta é a janela do Oratória Avaliador — estimada em **12–18 meses antes que Yoodli priorize PT-BR**.

**Principal ameaça:** **Yoodli** ($300M+ valuation dez/2025, +900% ARR em 12 meses, Series B US$ 40M fechada, clientes = Google/Snowflake/Databricks). Prova de que o espaço é grande e está sendo dominado globalmente por um player agressivo e bem capitalizado.

**Principal brand a navegar:** **SOAP** (83 das 100 maiores empresas BR como clientes). Não é competidor SaaS, mas é gate-keeper dos grandes deals corporativos. Pode virar aliado (integração/white-label) ou inimigo (se lançar produto SaaS próprio).

**3 movimentos estratégicos recomendados:**

1. **Speed offensive** — fechar 20+ logos BR em 18 meses com pricing 40–60% abaixo do Yoodli enterprise, aproveitando janela PT-BR
2. **Build data moat** — cada vídeo analisado em PT-BR é treino de modelo proprietário (Yoodli entra de fora sem isso)
3. **Partnership play com BR tradicional** — explorar white-label com SOAP ou Reinaldo Polito Pro (combina brand + tech), evitando guerra frontal com os gigantes de brand local

---

## 2. Analysis Scope & Methodology

### 2.1. Analysis Purpose

**Objetivos:**
- Avaliar ameaças competitivas (quem pode matar o Oratória Avaliador e quando)
- Identificar gaps de posicionamento/feature
- Definir estratégia de pricing versus benchmarks
- Mapear partnership/acquisition targets
- Criar intelligence plan para monitoramento contínuo

### 2.2. Competitor Categories Analyzed

| Categoria | Descrição | Exemplos |
|-----------|-----------|----------|
| **Direct Competitors** | Mesmo produto (AI speech coaching SaaS), mesmo target (corporate/professional) | Yoodli, Poised |
| **Indirect Competitors** | Produto diferente, mesma dor (melhorar comunicação) | Reinaldo Polito, SOAP, Conquer In Company, Liliane Bueno, Alura (cursos) |
| **Potential Competitors** | Podem entrar no mercado facilmente | Gong, Chorus.ai (se entrarem PT-BR), Alura (lançamento vertical), Totvs TAF + IA |
| **Substitute Products** | Soluções alternativas para a mesma dor | Coaches executivos 1:1, YouTube grátis, ChatGPT com prompts |
| **Aspirational Competitors** | Best-in-class global, referência | Yoodli (enterprise AI coaching), Duolingo (engagement design), Gong (conversation intelligence) |

### 2.3. Research Methodology

- **Sources primárias:** TechCrunch, GeekWire, Yahoo Finance, Crunchbase, PitchBook, Tracxn, CB Insights
- **Sources BR:** Sites oficiais (SOAP, Polito, Conquer, Liliane Bueno, The Speaker, Óh Quem Fala), LinkedIn oficial
- **Sources técnicas:** Pages de pricing Yoodli, app store Orai, G2, Capterra, research.com
- **Timeframe dos dados:** 2024–2026 (maioria 2025/Q4)
- **Confidence levels:**
  - **High:** Dados de funding Yoodli/Orai (fontes múltiplas confirmadas)
  - **Medium:** Pricing enterprise (Yoodli não publica — inferido de reviews G2/Capterra e benchmarks)
  - **Low:** Roadmap PT-BR de Yoodli/Orai (especulação baseada em pitch deck e tendências)
- **Limitações:**
  - Pricing enterprise real negociado não é público
  - Share de mercado BR específico por player não existe como dado consolidado
  - SOAP não divulga receita
  - Reinaldo Polito não divulga receita EAD

---

## 3. Competitive Landscape Overview

### 3.1. Market Structure

- **Active competitors (AI-first global):** 6–8 players em crescimento (Yoodli, Orai, Poised, Speeko, VoxAI, Verbalis, Speeched)
- **Active competitors (BR tradicional):** 30–50 players de relevância nacional; +1.500 provedores de treinamento corporativo se contar genéricos
- **Market concentration BR:** **ALTAMENTE FRAGMENTADO** — nenhum player com >5% market share em comunicação corporativa
- **Competitive dynamics:** lado AI em consolidação global (Yoodli puxa); lado BR tradicional estável, sem consolidação
- **Recent market entries:**
  - Yoodli Series B Dez/2025 (entrada agressiva enterprise)
  - VoxAI (2024, US) emergente
  - Nenhum novo player BR AI-first detectado
- **Recent market exits:** nenhum significativo

### 3.2. Competitor Prioritization Matrix (2×2)

```
                ALTA AMEAÇA (strategic threat)
                        ↑
                        |
   P2 — EMERGING        |  P1 — CORE COMPETITORS
   THREATS              |  (High share + High threat)
                        |
   • Orai (US)          |  • Yoodli (global enterprise)
   • Yoodli PT futuro   |  • SOAP (BR brand enterprise)
                        |
  ← BAIXA ───────────── + ──────────────── ALTA →
  BR market share                          BR market share
                        |
   P4 — MONITOR ONLY    |  P3 — ESTABLISHED PLAYERS
                        |  (High share + Low tech threat)
   • Poised, Speeko,    |  • Reinaldo Polito
     VoxAI (US B2C)     |  • Conquer In Company
   • JCI Oratória nas   |  • Liliane Bueno
     Escolas            |  • Óh Quem Fala
   • Cursos gen.        |  • The Speaker
     (Alura/Hotmart)    |
                        |
                        ↓
                BAIXA AMEAÇA
```

**Legenda:**

| Priority | # Competitors | Depth of Profile |
|----------|---------------|-------------------|
| **P1 Core** (core competitors) | 2 (Yoodli, SOAP) | Full profile |
| **P2 Emerging** (emerging threats) | 1 (Orai) | Full profile |
| **P3 Established** (brand-strong but tech-weak) | 4 (Polito, Conquer, Liliane, Óh Quem Fala) | Condensed profile |
| **P4 Monitor** (lower priority) | 5 (Poised, Speeko, VoxAI, JCI, Alura) | Short notes |

---

## 4. Individual Competitor Profiles

### 4.1. **YOODLI** — Priority 1 (Core Competitor + Principal Ameaça Estratégica)

#### Company Overview
- **Founded:** 2021 por **Varun Puri** (ex-Google X, special projects Sergey Brin) e **Esha Joshi** (ex-Apple engineer)
- **Headquarters:** Seattle, US
- **Company Size:** ~30–60 funcionários (post Series B)
- **Funding:** **US$ ~60M total** (Seed + $13.7M Series A em Mai/2025 + **US$ 40M Series B em Dez/2025**)
- **Valuation:** **US$ 300M+** (Dez/2025, tripled em 6 meses)
- **Investors:** WestBridge Capital (lead Series B), Neotribe, Madrona Ventures
- **Leadership:** Varun Puri (CEO), Esha Joshi (CTO)

#### Business Model & Strategy
- **Revenue Model:** SaaS subscription (B2C individual: US$ 11–28/mês; B2B Enterprise: custom high-ticket)
- **Target Market:** Enterprise sales enablement + L&D + coaching firms (white-label)
- **Value Proposition:** "AI role-play for communication practice — assist not replace people"
- **Go-to-Market Strategy:** Top-down enterprise + parcerias com coaching firms (Franklin Covey, LHH) + bottom-up individual
- **Strategic Focus (2026):** Escalar enterprise (já é a maioria da revenue); expansão vertical (sales, leadership, partner enablement)

#### Product/Service Analysis
- **Core Offerings:** Plataforma AI roleplay + Zoom/Teams live feedback + sales practice + pitch coaching
- **Key Features:**
  - Real-time feedback durante Zoom/Teams/Google Meet
  - Custom AI roleplays (construídos pelo cliente)
  - Analytics + SSO + enterprise admin
  - Integrations Zoom/Teams/Google/Slack
  - White-label para coaching firms
- **User Experience:** Interface moderna, desktop+mobile, live feedback discreto
- **Technology Stack:** Proprietary LLM fine-tuning + ASR + vision models
- **Pricing:**
  - Free tier
  - Pro: **US$ 11/mês** (10 Yoodlis/semana)
  - Advanced: **US$ 28/mês** (unlimited)
  - Enterprise: custom (benchmark G2: **~US$ 30–60/user/mês** com volume deals)

#### Strengths
- Capital pesado (US$ 60M raised, valuation em trajetória unicorn)
- Brand de credibilidade (founders ex-Google X/Apple, clientes Google/Databricks/Snowflake)
- Revenue +900% em 12 meses — product-market fit claro
- White-label deal com Franklin Covey + LHH = distribuição em escala coaching global
- Positioning narrativo forte ("assist, don't replace" — vence objeção anti-IA)
- Pitch deck público + co-fundadora indiana forte = brand de inovação

#### Weaknesses
- **Sem PT-BR nativo** (hoje)
- Pricing enterprise 3–5× acima do budget T&D médio BR
- Zero suporte local BR (timezone, contratos em PT, LGPD compliance formal)
- Foco dominante em sales enablement US — não customiza para oratória/palestra/liderança executiva BR
- LGPD compliance vaga (data residency US)
- Zero integração com sistemas HR brasileiros (Totvs, Senior, Sólides, Gupy)

#### Market Position & Performance
- **Market Share:** Estimado #1 global AI speech coaching enterprise
- **Customer Base:** Google, Snowflake, Databricks, RingCentral, Sandler Sales; + coaching firms Franklin Covey, LHH
- **Growth Trajectory:** +900% ARR em 12 meses — trajetória de IPO em 3–5 anos se mantiver
- **Recent Developments:**
  - Dez/2025: Series B US$ 40M (WestBridge lead)
  - Valuation US$ 300M+ (tripled)
  - Foco estratégico: enterprise expansion + integrações ecossistema empresarial

**🔴 Tese de ameaça:** Se Yoodli priorizar PT-BR antes de Q4/2026, a janela do Oratória Avaliador diminui drasticamente. Mas 2 fatores reduzem urgência: (1) o foco atual está em enterprise US/EU (capital pede growth rápido em markets maiores); (2) localização PT-BR competitiva exige dataset, compliance local, time BR — eles vão terceirizar ou demorar.

---

### 4.2. **SOAP** — Priority 1 (Brand Gate-Keeper BR Enterprise)

#### Company Overview
- **Founded:** 2001 (São Paulo, BR) — 25 anos de mercado
- **Headquarters:** São Paulo, BR
- **Company Size:** Estimado 80–150 funcionários (consultoria premium)
- **Funding:** Bootstrapped (não divulgado/captação externa)
- **Leadership:** Evandro Garla (CEO/fundador) + time sênior de consultores
- **Escala operacional:** 15k+ apresentações criadas, **2.200 empresas** atendidas (BR + 26 países), 30k+ pessoas treinadas

#### Business Model & Strategy
- **Revenue Model:** Consultoria B2B premium por projeto/hora + treinamentos in-company
- **Target Market:** Enterprises grandes BR — **83 das 100 maiores empresas do país**
- **Value Proposition:** "Apresentações e comunicação que geram resultado" — boutique premium
- **Go-to-Market Strategy:** Relacionamento enterprise top-down (diretores/C-level); referral e reputação
- **Strategic Focus:** Explorar IA em content/criação (curiosidade cautelosa), manter core de consultoria humana

#### Product/Service Analysis
- **Core Offerings:**
  - Consultoria em apresentações (SOAP cria slides/decks premium)
  - Treinamentos in-company (apresentação, storytelling, comunicação)
  - Vídeos corporativos
- **Key Features:** Método proprietário, time sênior, cases consolidados
- **User Experience:** High-touch, presencial+híbrido, personalizado
- **Technology Stack:** Ferramentas Microsoft Office/Google + ferramentas de design tradicionais; explorando IA generativa
- **Pricing:** Projetos tipicamente R$ 30k–R$ 500k (consultoria); treinamentos R$ 15k–R$ 100k por turma

#### Strengths
- Brand **mais forte** em comunicação corporativa BR enterprise
- Carteira: 83 das 100 maiores empresas BR
- Cases de sucesso décadas (Ambev, Itaú, Bradesco, Petrobras, Claro, etc.)
- Pricing power (alta margem consultoria premium)
- Brand embaixador (Evandro Garla como autoridade)
- Metodologia proprietária, não facilmente replicável

#### Weaknesses
- **Zero SaaS** — modelo de receita linear com horas de consultor (não escala)
- Zero AI nativa em produto (apenas "explora" IA em marketing)
- **Não vende ferramenta digital a colaboradores** — só treinamentos/projetos
- Preço proibitivo para empresas médias
- Dependência de pessoas-chave (founders + sêniores)
- Geração Z de RHs preferiu tech → brand pode envelhecer

#### Market Position & Performance
- **Market Share:** #1 consultoria premium BR em apresentações/comunicação
- **Customer Base:** Top-100 empresas BR + 26 países
- **Growth Trajectory:** Estável/moderada (consultoria não escala exponencial)
- **Recent Developments:** Conteúdo sobre IA em blog — sinaliza awareness mas zero produto lançado

**🟡 Tese estratégica:** SOAP não é competidor SaaS direto, **é gate-keeper de deals enterprise BR**. Se Oratória Avaliador vender pra Itaú, provavelmente vai esbarrar em relação SOAP. 2 plays possíveis:
- **Play A (aliança):** Oferecer white-label ou integração "SOAP method + Oratória Avaliador tech" → SOAP vende consultoria + tecnologia agregada
- **Play B (competição):** Atacar o mid-market (empresas 100–500 FTE) onde SOAP é caro demais — deixar o top-100 para uma próxima fase

---

### 4.3. **ORAI** — Priority 2 (Emerging Threat Latente)

#### Company Overview
- **Founded:** 2016 (10 anos de mercado)
- **Headquarters:** Philadelphia, US
- **Company Size:** **apenas 7 funcionários** (lean)
- **Funding:** **US$ 4,86M total** (Seed 2019 + Series A 2022)
- **Leadership:** Danish Dhamani (CEO/co-founder), Paritosh Gupta (co-founder) — TEDx talk 3M+ views
- **Users:** 450k+ users iOS+Android; **1,5M+ gravações** analisadas

#### Business Model & Strategy
- **Revenue Model:** SaaS B2C mobile subscription (freemium + premium)
- **Target Market:** B2C profissionais individuais (sales, executives, students)
- **Value Proposition:** "Your pocket speech coach"
- **Go-to-Market Strategy:** App store ASO + content marketing + TEDx halo effect
- **Strategic Focus:** Crescimento B2C mobile; não parecem priorizar B2B enterprise

#### Product/Service Analysis
- **Core Offerings:** App iOS + Android de análise de speech
- **Key Features:** Analisa pace, filler words, energy, clarity, confidence, facial expressions (basic)
- **User Experience:** Mobile-first, friendly, interactive lessons
- **Pricing:** Freemium + Pro (cerca de US$ 10/mês)
- **Revenue 2024:** **US$ 1,1M** — pequeno mesmo para B2C

#### Strengths
- Brand reconhecida B2C (TEDx viral founder)
- 10 anos de data (1,5M gravações) = moat
- Execução lean (7 funcionários, $1.1M revenue = eficiente)
- User base ampla (450k users) para experimentos

#### Weaknesses
- **Revenue modesta** (US$ 1,1M) → sem capital pra atacar BR com localização
- Foco B2C mobile → zero capacidade B2B enterprise
- Pricing baixo dificulta investimento em PT-BR específico
- 7 funcionários = zero bandwidth para novos mercados
- Não tem sales/CS team para B2B

#### Market Position & Performance
- **Market Share:** #2 após Yoodli em B2C mobile global
- **Customer Base:** individuais profissionais — não enterprise
- **Growth Trajectory:** Lenta e consistente (revenue cresce mas não exponencial)

**🟡 Tese de ameaça:** Orai tem dataset e brand B2C, mas **capital é crítico**. Sem Series B, dificilmente prioriza BR nos próximos 24 meses. Se entrar, será via app store em PT (baixo investimento) — risco pro canal B2C mas pouco pro B2B Oratória Avaliador. **Monitorar trimestralmente**.

---

### 4.4. Priority 3 — Established Players BR (Condensed Profiles)

#### **Reinaldo Polito** — "O Yoda brasileiro da oratória"
- **Founded:** ~1976 (50 anos!)
- **Model:** Cursos presenciais in-company + EAD (Hotmart, Portal Educação)
- **Scale:** 100k+ alunos (CEOs, TV apresentadores, políticos, líderes religiosos)
- **Cursos EAD flagship:** "Oratória para Líderes e Gestores" (6 módulos, 13 videoaulas, 2h) e "Oratória Política" (7 módulos, 4h)
- **Strengths:** Brand #1 reconhecimento BR, metodologia consolidada, autor de livros best-sellers
- **Weaknesses:** EAD é linear/commodity (gravação + módulos), zero IA, zero mensuração individual, cursos curtos (~2h) nao geram LTV contínuo
- **Threat to Oratória Avaliador:** BAIXA no tech, MÉDIA no brand — se posicionar como "IA que completa método Polito" e buscar partnership, pode converter brand em distribuição. Se competir frontalmente no "brand", perde.

#### **Escola Conquer — In Company** — Brand forte PME/mid-market
- **Model:** Treinamentos presenciais + blended, in-company customizado
- **Scale:** Operação em múltiplas capitais, milhares de empresas atendidas
- **Strengths:** Pricing acessível vs. SOAP, operação distribuída multi-cidades
- **Weaknesses:** Zero IA, dependência de instrutores humanos, lento pra escalar
- **Threat:** Baixa — mas se criar SaaS próprio ou fizer partnership com AI player, pode acelerar

#### **Liliane Bueno — Oratória para Negócios** — Nicho vendas consultivas
- **Model:** Cursos online síncronos + presenciais + livros
- **Scale:** 16k+ profissionais impactados
- **Strengths:** Nicho bem definido (oratória comercial/vendas), brand pessoal
- **Weaknesses:** Operação pequena/boutique, zero tech, baixa escala
- **Threat:** Muito baixa

#### **Óh Quem Fala** — Boutique executivo
- **Model:** Treinamentos C-level, mentoria
- **Strengths:** Nicho C-level/premium
- **Weaknesses:** Pequeno, zero tech
- **Threat:** Baixíssima

#### **The Speaker / outros players regionais** — Pulverizados
- **Ameaça individual:** baixa
- **Ameaça coletiva:** fragmentação cria ruído comercial, confusão de RH na escolha

### 4.5. Priority 4 — Monitor Only (Short Notes)

- **Poised** (US): Desktop app live feedback Zoom — foco estreito, B2B US, não PT, zero ameaça BR 12m
- **Speeko** (US): iOS-only, voice-specific, B2C nicho — zero presença BR
- **VoxAI** (US): Multi-style presentations — startup early, pouca tração
- **JCI Oratória nas Escolas** (BR): Projeto escolar sem fins lucrativos — não é competidor comercial
- **Alura for Business** (BR): LMS B2B — curso de oratória hipótese; hoje não tem vertical específica, mas **sinal de alerta** se lançar IA speech analysis — monitor trimestral
- **Gong / Chorus.ai** (US): Conversation intelligence para sales — não entram em PT-BR hoje, mas se entrarem são **supercompetidores** com capital infinito — monitor trimestral

---

## 5. Comparative Analysis

### 5.1. Feature Comparison Matrix

| Feature Category | **Oratória Avaliador** (projeto) | Yoodli | Orai | SOAP | Reinaldo Polito EAD |
|------------------|----------------------------------|--------|------|------|---------------------|
| **Core Functionality** | | | | | |
| Análise de vídeo (multimodal) | ✅ Sim (core) | ✅ Sim | ✅ Sim (mobile) | ❌ Não | ❌ Não |
| Feedback em PT-BR nativo | 🔥 Sim (diferencial) | ❌ Não | ❌ Não | ✅ Sim (humano) | ✅ Sim (humano) |
| Análise de fillers/muletas | ✅ Sim | ✅ Sim | ✅ Sim | ❌ Não auto | ❌ Não |
| Detecção tom/prosódia | ✅ Sim | ✅ Sim | ✅ Sim | ❌ Não | ❌ Não |
| Análise expressão facial | ✅ Sim | ❌ Limited | ✅ Sim | ❌ Não | ❌ Não |
| Live feedback Zoom/Teams | ⚠️ Roadmap | ✅ Sim | ❌ Não | ❌ Não | ❌ Não |
| AI roleplay simulação | ⚠️ Roadmap | ✅ Sim | ❌ Não | ❌ Não | ❌ Não |
| **User Experience** | | | | | |
| Mobile App | ⚠️ Roadmap | ✅ Sim | ✅ Sim (core) | ❌ Não | ❌ Não |
| Web App | ✅ Sim | ✅ Sim | ⚠️ Limited | ❌ Não (consultoria) | ⚠️ Hotmart/Portal |
| Desktop app | ❌ Não | ✅ Sim | ❌ Não | ❌ Não | ❌ Não |
| Onboarding time | < 15 min (target) | < 10 min | < 5 min | Semanas (projeto) | Horas (curso) |
| Interface PT-BR | ✅ Sim | ❌ Não | ❌ Não | ✅ Sim | ✅ Sim |
| **B2B Enterprise Features** | | | | | |
| Dashboard gestor (individual + squad) | 🔥 Sim (diferencial) | ✅ Sim | ❌ Não (B2C only) | ❌ Não | ❌ Não |
| SSO (SAML/OIDC) | ⚠️ Roadmap | ✅ Sim | ❌ Não | N/A | ❌ Não |
| Analytics team-level | ✅ Sim | ✅ Sim | ❌ Não | ❌ Não | ❌ Não |
| Admin + user management | ✅ Sim | ✅ Sim | ❌ Não | N/A | ❌ Não |
| **Integration & Ecosystem** | | | | | |
| API pública | ⚠️ Roadmap | ✅ Sim | ❌ Não | ❌ Não | ❌ Não |
| Integração CRMs (Salesforce/HubSpot) | ❌ Não | ✅ Sim | ❌ Não | ❌ Não | ❌ Não |
| Integração LMS/HR BR (Totvs, Senior, Gupy) | 🔥 Oportunidade roadmap | ❌ Não | ❌ Não | ❌ Não | ❌ Não |
| Calendar (Zoom/Teams/Google) | ⚠️ Roadmap | ✅ Sim | ❌ Não | ❌ Não | ❌ Não |
| **Localização / Compliance** | | | | | |
| PT-BR idioma + sotaque | 🔥 Sim (DIFERENCIAL CRÍTICO) | ❌ Não | ❌ Não | ✅ Humano | ✅ Humano |
| LGPD compliance explícita | ✅ Sim | ⚠️ Parcial | ⚠️ Parcial | ✅ Sim | ⚠️ Parcial |
| Data residency BR | ✅ Possível | ❌ Não | ❌ Não | ✅ Sim | ⚠️ Hotmart infra |
| **Pricing (normalizado BRL)** | | | | | |
| Starting price individual | R$ 39/mês (target) | ~R$ 55/mês (Pro US$11) | ~R$ 50/mês | Não aplicável | R$ 297–997 curso único |
| Free tier | ✅ Planejado | ✅ Sim | ✅ Sim | ❌ Não | ❌ Não |
| Enterprise starting | R$ 8k setup + R$ 45/user/mês | Custom (~R$ 150+/user) | N/A | R$ 30k+ projeto | N/A |

**Legenda:** ✅ sim/forte | ⚠️ parcial/roadmap | ❌ ausente | 🔥 diferencial/oportunidade crítica

### 5.2. SWOT Comparison

#### 5.2.1. Oratória Avaliador (Your Solution)

- **Strengths:**
  - Único SaaS AI nativo PT-BR no BR
  - Dashboard de gestor + narrativa de ROI "+10% = +10%"
  - Data residency BR + LGPD first
  - Pricing agressivo viável
  - Founder-led sales close access ao mercado BR
- **Weaknesses:**
  - Capital limitado vs Yoodli (US$ 60M raised)
  - Zero brand hoje → precisa construir do zero
  - Sem integrações enterprise hoje (SSO, HR systems, CRMs)
  - Produto em MVP — features como live feedback e AI roleplay ainda roadmap
  - Sem case studies públicos
- **Opportunities:**
  - Janela 12–18 meses antes Yoodli PT-BR
  - +1.500 provedores BR fragmentados → nenhum player único com share dominante
  - Adoção IA em T&D saltou 8→69% (2024→2025) = RHs procurando ativamente
  - Partnership white-label com SOAP/Polito/Conquer se forem open
  - LATAM expansion ano 3 (México, Argentina, Colômbia = US$ 5,1B adicional)
- **Threats:**
  - Yoodli priorizar PT-BR antes de Q4/2026
  - Orai entrar via app store PT (B2C threat)
  - SOAP lançar produto SaaS próprio com AI
  - Alura for Business lançar vertical de comunicação
  - Commoditização por ChatGPT plugins custom

#### 5.2.2. vs. Yoodli (Main Competitor)

- **Competitive Advantages (Oratória Avaliador):**
  - 🔥 PT-BR nativo + sotaque brasileiro + referências culturais
  - 🔥 LGPD compliance + data residency BR
  - 🔥 Pricing 40–60% abaixo (R$ 45–75 vs US$ 30–60 enterprise)
  - 🔥 Suporte local + time BR + contratos em PT
  - 🔥 Integração com stack HR brasileiro (Totvs, Senior, Sólides, Gupy)
  - 🔥 Narrativa "+10% comunicação = +10% lucro" com foco em ROI
- **Competitive Disadvantages:**
  - ❌ Capital 50× menor (US$ 1M vs US$ 60M raised)
  - ❌ Zero brand global
  - ❌ Sem parcerias white-label (Yoodli tem Franklin Covey + LHH)
  - ❌ Zero clientes Fortune 500 de refência
  - ❌ Produto com features menos completas (live feedback, AI roleplay em roadmap)
- **Differentiation Opportunities:**
  - "O Yoodli brasileiro com entendimento cultural real"
  - Posicionar-se no "oratória corporativa premium" vs. Yoodli em "sales enablement"
  - Partnership com escola de comunicação BR (Polito white-label) → brand + tech
  - Vertical focus: oratória executiva (C-level e aspiracional) onde Yoodli é genérico

#### 5.2.3. vs. SOAP (Brand Gate-Keeper BR)

- **Competitive Advantages (Oratória Avaliador):**
  - 🔥 Modelo SaaS escalável (SOAP = consultoria linear)
  - 🔥 Dashboard individual por colaborador (SOAP não tem)
  - 🔥 Preço acessível para mid-market (SOAP é caro demais para empresas 100–500 FTE)
  - 🔥 Onboarding rápido (dias vs semanas)
- **Competitive Disadvantages:**
  - ❌ Zero brand vs SOAP (83 das 100 maiores empresas BR)
  - ❌ Sem relacionamento C-level estabelecido
  - ❌ Falta de "consultoria humana" pode ser objeção para enterprise top-100
- **Differentiation Opportunities:**
  - Posicionar-se no **mid-market** (100–500 FTE) — SOAP é caro demais, brand não importa tanto
  - **Partnership play:** oferecer white-label para SOAP adicionar à oferta ("SOAP + Oratória Avaliador tech")
  - Complementar ao SOAP em clientes enterprise: SOAP faz apresentações + treinamento premium, Oratória Avaliador faz prática contínua + mensuração

### 5.3. Positioning Map

**Dimensões escolhidas:** Preço (vertical) × Escalabilidade / IA nativa (horizontal)

```
                 PREÇO ALTO
                      ↑
                      |
       SOAP •         |
                      |
   Reinaldo Polito •  |  Yoodli Enterprise •
                      |
   Conquer/Liliane •  |
                      |
                      |   ★ Oratória Avaliador
                      |     (sweet spot BR mid-market)
                      |
   Cursos Alura/      |  Yoodli Pro •
   Hotmart genéricos• |  Orai •
                      |  Speeko/Poised •
                      |
                      ↓
                 PREÇO BAIXO
  BAIXA ESCALA ←─────────────────→ ALTA ESCALA / AI NATIVA
```

**Leitura estratégica:**
- **Quadrante Alto preço + Alta escala (Yoodli Enterprise):** Sweet spot do Yoodli — high-ticket + AI
- **Quadrante Alto preço + Baixa escala (SOAP, Polito, Conquer):** Premium BR tradicional
- **Quadrante Baixo preço + Alta escala (Yoodli Pro, Orai, Speeko, Poised):** B2C commoditizado
- **Quadrante Baixo preço + Baixa escala (Alura/Hotmart cursos):** Commodity
- **Quadrante SWEET SPOT aberto:** Preço **mid-high BR** + Alta escala AI — **ninguém ocupa hoje**. É exatamente onde Oratória Avaliador deve se posicionar.

---

## 6. Strategic Analysis

### 6.1. Competitive Advantages Assessment

#### 6.1.1. Sustainable Advantages (moats construíveis ou existentes)

| Moat | Difficulty to build | Time to build | Strength | Notas |
|------|---------------------|---------------|----------|-------|
| **Dataset proprietário PT-BR anotado** | Média-alta | 12–18m | Alta | Cada vídeo do usuário é treino; concorrente de fora precisa importar volume BR |
| **Brand BR + cases enterprise** | Alta | 18–36m | Alta | 20+ logos + 3 cases quantificados = moat de referência |
| **Integrações stack HR brasileiro** | Média | 6–12m | Média-alta | Totvs/Senior/Sólides/Gupy = switching cost |
| **Partnership com player tradicional** (Polito/SOAP white-label) | Média | 6–12m | Alta | Brand + distribuição instantâneos |
| **Switching costs via histórico longitudinal** | Baixa-média | Orgânico | Média | Usuário perde timeline de evolução — importante para engajamento |
| **Compliance BR (LGPD + residency)** | Baixa | 3–6m | Baixa-média | Barreira para players US — mas Yoodli pode comprar em 6m |
| **Network effects** | Alta | 3–5 anos | Baixa hoje | Pode emergir via comunidade aspiracional (tipo Strava) |

#### 6.1.2. Vulnerable Points of Each Competitor (onde atacar)

**Yoodli:**
- PT-BR inexistente hoje → atacar antes deles chegarem
- Preço enterprise proibitivo para empresas BR 100–500 FTE (80% do mercado)
- Zero customização para oratória/palestra (foco é sales enablement)
- Ausência de parceiros BR

**SOAP / Polito / Conquer:**
- Modelo não escala per-seat → atacar mid-market com preço acessível
- Zero IA → atacar com mensuração individual + dashboard
- Brand envelhecendo com geração Z de RHs → atacar com messaging tech-forward

**Orai:**
- Revenue modesta + capital limitado → atacar pela banda enterprise onde eles não chegam
- B2C mobile = sem dashboard de gestor
- Zero PT-BR

### 6.2. Blue Ocean Opportunities

**Uncontested spaces que ninguém ocupa hoje:**

1. **AI nativa PT-BR + vertical oratória executiva BR** (Oratória Avaliador target direto)
2. **Integrações com HR systems BR** (Totvs TAF, Senior, Sólides, Gupy) — ninguém fez
3. **Consultorias de coaching BR com white-label AI** (mercado de 200+ coaches executivos que não tem ferramenta digital própria)
4. **Preparação específica para eventos BR** (TEDx, palestras, reuniões conselho) com conteúdo treinado em PT-BR
5. **Dashboard familiar/pedagógico** (ICP pai que quer acompanhar filho desenvolvendo comunicação — adjacente ao 9.2 do market research, pero nicho explorável)
6. **Integração com podcasts/YouTube (creators)** (auto-análise de gravações, nicho premium)
7. **Vertical sales call intelligence PT-BR** (Gong/Chorus não entraram — TAM BR ~R$ 500M)

---

## 7. Strategic Recommendations

### 7.1. Differentiation Strategy — "Posicionamento Central"

**Posicionamento recomendado:**
> "O **sistema operacional da comunicação corporativa brasileira** — única IA em português que mede, treina e comprova evolução individual e coletiva. Onde SOAP ensina método e Yoodli resolve enterprise US, a gente entrega prática contínua em PT-BR com ROI mensurado."

**Unique Value Propositions a enfatizar (por ordem):**

1. **"Único em PT-BR"** — capture antes que Yoodli venha
2. **"Dashboard de gestor ROI-driven"** — narrativa "+10% = +10%" repetida em todos os pitches
3. **"Brasileiro, feito para brasileiros"** — integrações HR BR + LGPD + suporte em PT + contratos em real
4. **"Evolução mensurável e longitudinal"** — diferenciação vs cursos fechados (Polito, Alura)
5. **"Pricing mid-market"** — democratiza AI coaching para empresas 100–500 FTE

**Features a priorizar em roadmap (12 meses):**

| Feature | Prioridade | Racional competitivo |
|---------|------------|---------------------|
| SSO enterprise (SAML, OIDC) | 🔥 Crítico | Gate para deals enterprise |
| Integração Totvs + Senior | 🔥 Crítico | Moat PT-BR vs Yoodli |
| Dashboard gestor multi-level | 🔥 Crítico | Gate para tese "+10%" |
| Live feedback Zoom/Teams | 🟡 Alto | Paridade com Yoodli core feature |
| AI roleplay customizável (por empresa) | 🟡 Alto | Paridade com Yoodli enterprise |
| Mobile app | 🟡 Alto | B2C pull-through |
| Community / leaderboards | 🟢 Médio | Engagement longitudinal (lição Duolingo) |
| Coaching humano complementar (hybrid) | 🟢 Médio | Defesa contra "IA não substitui humano" |

**Messaging diferenciado (hero copy do site + decks):**
- Headline: "Sua IA brasileira de comunicação corporativa"
- Sub: "Avalie, treine e comprove evolução de comunicação do seu time. +10% em comunicação se traduz em mais vendas, retenção e produtividade — agora mensurado."
- CTA B2B: "Agende um piloto de 90 dias com 30 colaboradores"
- CTA B2C: "Comece grátis — sua primeira análise em 2 minutos"

### 7.2. Competitive Response Planning

#### 7.2.1. Offensive Strategies (como ganhar share)

1. **Speed-to-logo vs Yoodli ausente:** fechar **20+ logos B2B em 18 meses** antes de Yoodli lançar PT-BR. Pricing agressivo (40–60% abaixo Yoodli enterprise) + piloto pago com desconto de case study
2. **Lock-in multi-anual com desconto:** contratos 2 anos com -25% no ticket anual — cria switching cost preventivo
3. **Capturar clientes Polito/SOAP que querem escalar mensuração:** vender como "complemento digital" ao método que já conhecem. "Faça SOAP anualmente e Oratória Avaliador continuamente"
4. **Win competitive deals vs Yoodli (quando houver):** pitch de suporte local + LGPD + pricing → RH conservador BR tende a preferir fornecedor BR
5. **Hackathon + virality reverso:** programa "Oratória Avaliador for Startups" — 500 startups pagam R$ 0–500/mês → ganham visibilidade + atraem talentos → viram case de adoção natural

#### 7.2.2. Defensive Strategies (como proteger a posição)

1. **Construir dataset PT-BR proprietário** (cada vídeo = treino). Fine-tuning de modelos pequenos próprios (reduz custo LLM + aumenta moat)
2. **Strengthen integração HR BR (Totvs, Senior, Sólides)** — switching cost real em 12m
3. **Community flywheel** — grupo no LinkedIn "Comunicadores Corporativos BR", newsletter mensal, eventos trimestrais (brand defense contra Yoodli que é tech-only)
4. **Customer obsession + CS top-tier** — quarterly business reviews, NPS targeting 60+ em todos os logos (brand defense via advocacy)
5. **Lock-in via data/histórico** — tornar histórico longitudinal do colaborador tão valioso que migrar é perder anos de desenvolvimento medido
6. **Patent filings (opcionais)** em algumas inovações técnicas — sinal de moat para investidores

### 7.3. Partnership & Ecosystem Strategy

**Potential partnerships priorizadas:**

| Partner Type | Specific Partners | Play | Prioridade |
|--------------|-------------------|------|------------|
| **Escolas tradicionais de oratória** | Reinaldo Polito Pro, SOAP, Conquer In Company | White-label ou "powered by" — eles vendem método humano + nossa tech mensura | 🔥 High (high reach) |
| **LMS/HR Tech BR** | Totvs TAF, Senior Sistemas, Alura for Business, Sólides | Integração técnica + co-sell em suas bases | 🔥 High |
| **Consultorias HR** | Korn Ferry BR, Mercer BR, PageGroup | Canal de referral para enterprise | 🟡 Medium |
| **Escolas de negócios** | FGV, Insper, ISE, Saint Paul | Endosso acadêmico + pipeline alunos MBA (adjacente) | 🟡 Medium |
| **Integradoras corporate** | Globant, CI&T, Stefanini (clientes enterprise) | Implementação e customização para grandes empresas | 🟢 Low-Medium |
| **Coaches executivos individuais** | Marca própria (ex: Guilherme Peixoto, Rogério Chér, Adriana Prates) | White-label para coaches adicionarem tech | 🟡 Medium |
| **Wellness/benefits aggregators** | Gympass/Wellhub, Flash, Pluxee | Bundle em benefícios corporativos (B2B2C) | 🟢 Low (long-shot high reward) |

**Parceria estratégica ideal curto prazo (6 meses):**
- **Opção A:** Reinaldo Polito Pro → white-label (método Polito + tech Oratória Avaliador) → desbloqueia brand + gera early revenue
- **Opção B:** Totvs TAF → integração nativa → acesso a 60k+ empresas clientes Totvs

---

## 8. Monitoring & Intelligence Plan

### 8.1. Key Competitors to Track

| Priority | Competitor | Rationale | Update Cadence |
|----------|------------|-----------|----------------|
| 1 | **Yoodli** | Principal ameaça — PT-BR entry é evento existencial | Semanal |
| 1 | **SOAP** | Gate-keeper BR enterprise — lançamento SaaS próprio = ameaça | Mensal |
| 2 | **Orai** | Monitor se entrar em PT ou receber Series B | Mensal |
| 2 | **Alura for Business** | Pode lançar vertical de comunicação + IA | Mensal |
| 3 | **Reinaldo Polito** | Monitor se digitalizar mais agressivamente (plataforma própria) | Trimestral |
| 3 | **Conquer In Company** | Monitor se fizer partnership com AI player | Trimestral |
| 3 | **Gong, Chorus.ai** | Monitor entrada em PT-BR (baixa probabilidade, alta ameaça) | Trimestral |
| 4 | **Poised, Speeko, VoxAI** | Acompanhar tendências tech | Semestral |

### 8.2. Monitoring Metrics

**O que trackear por competitor:**

| Métrica | Fonte | Frequência |
|---------|-------|------------|
| Product releases (changelog, blog posts) | Sites oficiais, newsletter | Semanal (P1) / Mensal (P2) |
| Pricing changes | Pricing pages + G2/Capterra reviews | Mensal |
| Customer wins & logos novos | LinkedIn, PR, press releases | Semanal (Yoodli) |
| Funding / M&A | Crunchbase, PitchBook, TechCrunch | Alerta diário |
| Job postings (contratações BR?) | LinkedIn, Glassdoor, Gupy | Semanal (Yoodli, Orai) |
| Ads/PR campaigns | Google Ads, LinkedIn Ads, Meta | Mensal |
| Community chatter (Reddit, LinkedIn, G2) | Search alerts | Diário |
| Patent filings | USPTO (US), INPI (BR) | Trimestral |
| Events BR (RH Tech, HSM, CONARH) | Event programs + speakers | Trimestral |
| Roadmap announcements | Yoodli blog, TechCrunch interviews | Semanal |

### 8.3. Intelligence Sources

**Estruturadas:**
- TechCrunch (com filtro "AI communication" / "speech AI")
- GeekWire (cobre Yoodli e players Seattle)
- Crunchbase alerts (Yoodli, Orai)
- PitchBook profile tracking
- G2 + Capterra reviews
- LinkedIn Sales Navigator (saved searches: Yoodli customers BR)

**Informais:**
- LinkedIn de Varun Puri (Yoodli CEO) + Danish Dhamani (Orai CEO)
- X/Twitter dos founders
- Reddit r/sales, r/publicspeaking
- YouTube dos founders (Yoodli/Orai publicam content)
- Newsletters: Hacker News AI, Tracxn EdTech

**BR específicas:**
- Valor Econômico, Exame (cobertura edtech/hrtech)
- Distrito (portal de inovação BR)
- LinkedIn conteúdo de Evandro Garla (SOAP), Reinaldo Polito
- Eventos: CONARH, HSM Expo, HR Summit BR, HSM Experience

### 8.4. Update Cadence

| Frequência | Items |
|------------|-------|
| **Diária** | Alertas Google/Crunchbase de Yoodli, menções Oratória Avaliador + competitors |
| **Semanal** | Product updates Yoodli; movimentos de SOAP em conteúdo IA; novos deals enterprise |
| **Mensal** | Pricing scan todos P1+P2; LinkedIn ads dos competitors; revisão matriz de features |
| **Trimestral** | Full competitive refresh — atualizar este doc; análise de entradas/saídas do mercado; reavaliar priorização 2x2 |
| **Anual** | Deep stress test competitive — repetir pesquisas de funding, contratações regionais, roadmap signals |

---

## 9. Appendices

### A. Quick-Reference Summary Card

| Competitor | Priority | Threat Level (1–5) | Threat Window | Your Response |
|------------|----------|--------------------|-----------------|--------------|
| Yoodli | 1 | 5/5 | 12–18m | Speed offensive, lock-in, dataset moat |
| SOAP | 1 | 3/5 | Ongoing | Partnership play OR mid-market focus |
| Orai | 2 | 3/5 | 24m+ | Monitor, ignore no B2B; defesa B2C se entrar PT |
| Reinaldo Polito | 3 | 2/5 | Low urgency | White-label opportunity |
| Conquer | 3 | 2/5 | Low | Competition or partnership |
| Liliane/Óh Quem Fala/The Speaker | 3 | 1/5 | Very low | Ignore |
| Poised/Speeko/VoxAI | 4 | 1/5 | Low | Monitor semestral |
| Alura for Business | 4 | 3/5 (sleeper) | 12–24m | Monitor + considerar partnership |
| Gong/Chorus (se entrar PT) | 4 | 5/5 (sleeper) | 24–36m | Monitor trimestral |

### B. Decision Triggers — Quando reagir imediatamente

1. **Yoodli anuncia PT-BR ou abertura BR** → acionar plano de aceleração: 3 announcements de clientes + desconto de 20% para novos logos B2B (30 dias)
2. **SOAP ou Polito anuncia SaaS próprio com IA** → avaliar pivô de partnership (nós construímos a tech para eles) vs competição direta
3. **Alura for Business lança vertical de comunicação** → acelerar parceria com Totvs/Senior (lock-in de canal alternativo)
4. **Gong ou Chorus entram em PT-BR** → pivotar rápido para vertical não-sales (oratória executiva, palestras, liderança)

### C. Data Sources

- [Ex-Googler's Yoodli triples valuation to $300M+ — TechCrunch](https://techcrunch.com/2025/12/05/ex-googlers-yoodli-triples-valuation-to-300m-with-ai-built-to-assist-not-replace-people/)
- [Yoodli Raises $40M Series B — Yoodli Blog](https://yoodli.ai/blog/yoodli-raises-40-million-series-b-to-lead-the-future-of-experiential-learning)
- [Yoodli pitch deck — GeekWire](https://www.geekwire.com/2025/heres-the-pitch-deck-used-by-yoodli-the-seattle-startup-now-valued-at-more-than-300m/)
- [Yoodli 2026 Profile — PitchBook](https://pitchbook.com/profiles/company/482256-82)
- [Yoodli — Crunchbase](https://www.crunchbase.com/organization/yoodli)
- [Yoodli Pricing & Plans](https://yoodli.ai/pricing)
- [Orai — Crunchbase](https://www.crunchbase.com/organization/orai)
- [How Orai hit $1.1M revenue — GetLatka](https://getlatka.com/companies/orai.com)
- [SOAP — Sobre a empresa](https://soap.com.br/sobre-a-soap/)
- [Reinaldo Polito — Cursos](https://www.reinaldopolito.com.br/curso)
- [Escola Conquer In Company](https://incompany.escolaconquer.com.br/treinamento-de-comunicacao)
- [Yoodli Alternatives Comparison — Outdoo AI](https://www.outdoo.ai/blog/yoodli-alternatives)
- [Best AI Communication Coaches — The AI Surf](https://theaisurf.com/best-ai-communication-coaches/)

---

**Fim do competitive analysis. Pronto para elicitação avançada ou handoff para @pm (PRD/epic) ou @architect (arquitetura produto).**
