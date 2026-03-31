# Oratória Avaliador — Product Requirements Document (PRD)

## Goals and Background Context

### Goals

- Entregar MVP funcional que avalia oratória em vídeo nas 4 dimensões (postura, gestual, tom de voz, vícios de linguagem)
- Validar product-market fit com usuários reais (meta: 100 avaliações no 1º mês)
- Demonstrar que arquitetura híbrida (ferramentas especializadas + LLM) produz feedback acionável e percebido como útil
- Manter custo por avaliação < R$ 2,00 para viabilizar modelo acessível
- Obter NPS >= 40 entre primeiros usuários

### Background Context

Pessoas que falam em público — palestrantes, professores, criadores de conteúdo — não têm acesso a feedback objetivo e estruturado sobre sua performance. Coaches de oratória são caros e subjetivos; auto-avaliação é enviesada. Nenhuma ferramenta existente analisa oratória de forma multidimensional combinando análise visual (postura, gestos) com análise de áudio (prosódia, vícios de linguagem).

O brainstorm técnico (`docs/research/brainstorm-avaliacao-oratoria-ia.md`) mapeou abordagens viáveis para cada dimensão e recomendou uma arquitetura híbrida: ferramentas especializadas (MediaPipe, Whisper, Parselmouth) extraem métricas quantitativas, e um LLM (Claude/GPT) gera feedback qualitativo contextualizado. O Project Brief (`docs/brief.md`) validou escopo, stack, constraints e targets de sucesso.

### Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2026-03-30 | 0.1 | Draft inicial — YOLO mode a partir do Project Brief | @pm (Morgan) |

---

## Requirements

### Functional

- **FR1:** O sistema deve aceitar upload de vídeo nos formatos MP4 e WebM, com duração máxima de 10 minutos e tamanho máximo de 500MB
- **FR2:** O sistema deve separar o vídeo enviado em streams de áudio e vídeo para processamento independente
- **FR3:** O sistema deve extrair 33 keypoints corporais por frame usando MediaPipe Pose e calcular um score de alinhamento postural (0-100)
- **FR4:** O sistema deve calcular % do tempo em postura aberta vs fechada e score de estabilidade postural
- **FR5:** O sistema deve detectar presença/ausência de gesticulação com as mãos usando MediaPipe Hands
- **FR6:** O sistema deve estimar contato visual (olhando para câmera vs desviando) usando MediaPipe Face Mesh
- **FR7:** O sistema deve transcrever o áudio para texto com timestamps por palavra usando Whisper, em PT-BR
- **FR8:** O sistema deve extrair métricas prosódicas (pitch F0, intensidade/volume, taxa de fala) usando Parselmouth
- **FR9:** O sistema deve detectar e contar fillers ("né", "tipo", "então", "éee", "hum", "aí") na transcrição, com timestamps de cada ocorrência
- **FR10:** O sistema deve calcular WPM (palavras por minuto), variação de pitch em semitones e razão fala/silêncio
- **FR11:** O sistema deve agregar todas as métricas das 4 dimensões em um JSON estruturado para consumo pelo LLM
- **FR12:** O sistema deve gerar relatório qualitativo usando LLM (Claude ou GPT) a partir das métricas agregadas, com feedback específico e acionável por dimensão
- **FR13:** O sistema deve exibir dashboard do relatório com score geral e scores por dimensão (0-100)
- **FR14:** O sistema deve exibir detalhamento por dimensão com métricas específicas, timestamps relevantes e recomendações
- **FR15:** O sistema deve permitir que o usuário avalie a qualidade do relatório (1-5 estrelas)
- **FR16:** O sistema deve mostrar status de processamento em tempo real (etapa atual, progresso estimado)
- **FR17:** O sistema deve operar exclusivamente em PT-BR no MVP (interface e análise linguística)

### Non Functional

- **NFR1:** Tempo de processamento total < 5 minutos para vídeo de 10 minutos
- **NFR2:** Custo total por avaliação < R$ 2,00 (infraestrutura + APIs)
- **NFR3:** Tempo de resposta da UI < 200ms para operações não-processamento
- **NFR4:** Vídeos devem ser deletados após processamento (período de retenção configurável, default: imediato)
- **NFR5:** Suportar processamento concorrente de pelo menos 3 vídeos simultaneamente
- **NFR6:** Degradação graceful: se uma dimensão de análise falhar, o relatório deve apresentar as dimensões disponíveis com nota indicando a falha
- **NFR7:** Design responsivo (mobile-friendly), funcional em telas >= 375px
- **NFR8:** Logging estruturado e error tracking implementados desde o Epic 1
- **NFR9:** Aplicação deve funcionar nos browsers Chrome, Firefox, Safari e Edge (últimas 2 versões)

---

## User Interface Design Goals

### Overall UX Vision

Interface minimalista e focada no fluxo principal: **upload → espera → relatório**. A experiência deve transmitir credibilidade técnica (a IA está analisando seriamente) sem sobrecarregar o usuário com complexidade. O relatório é o produto — deve ser claro, visual e acionável.

### Key Interaction Paradigms

- **Single-task focus:** Uma tela por vez, sem multitasking — upload OU relatório
- **Progressive disclosure:** Score geral primeiro, depois detalhe por dimensão on-demand
- **Status transparency:** Durante processamento, mostrar etapa atual ("Analisando postura...", "Transcrevendo áudio...")
- **Feedback loop:** Rating do relatório sempre visível e acessível

### Core Screens and Views

1. **Landing/Upload** — Drag-and-drop de vídeo + instruções breves sobre formato e duração
2. **Processing** — Status de processamento com etapas e progresso estimado
3. **Report Dashboard** — Score geral + cards por dimensão (postura, gestual, voz, vícios)
4. **Report Detail** — Detalhamento de uma dimensão: métricas, timeline, recomendações
5. **Rating** — Avaliação de qualidade do relatório (1-5 estrelas + comentário opcional)

### Accessibility: WCAG AA

Conformidade básica com WCAG AA: contraste adequado, navegação por teclado, textos alternativos para gráficos.

### Branding

MVP sem branding definido. Estilo clean/moderno com paleta neutra. Possível uso de tons de azul (confiança) e verde (progresso/sucesso). Tipografia sans-serif. Sem logo definido.

### Target Device and Platforms: Web Responsive

Web responsivo com foco primário em desktop (onde a maioria das avaliações será feita), mas funcional em mobile para visualização de relatórios.

---

## Technical Assumptions

### Repository Structure: Monorepo

Monorepo com três diretórios principais:
- `apps/web/` — Frontend Next.js (Vercel)
- `apps/api/` — API leve Python/FastAPI (Render free)
- `ml-worker/` — ML worker pesado Python (HF Spaces free)

**Rationale:** Dev solo, custo zero, deploy independente por serviço.

### Service Architecture

Arquitetura de 4 camadas:
1. **Frontend (Next.js / Vercel free)** — UI, upload, polling de status, visualização de relatório
2. **API leve (FastAPI / Render free)** — Recebe uploads, dispara ML worker, serve relatórios (512MB RAM)
3. **ML Worker (FastAPI / HF Spaces free)** — Processamento pesado (MediaPipe, Whisper, Parselmouth, Gemini) com 16GB RAM
4. **Supabase (free)** — PostgreSQL, Storage, Auth (futuro)

**Async processing:** API leve dispara ML worker via HTTP. ML worker processa e faz callback com resultados. Frontend faz polling de status na API.

**Storage:** Supabase Storage para vídeos temporários + Supabase PostgreSQL para relatórios e métricas.

### Testing Requirements

- **Unit tests** para funções de cálculo de métricas (scores, WPM, fillers)
- **Integration tests** para pipeline de processamento (input → output por dimensão)
- **E2E tests** mínimos para fluxo crítico (upload → relatório)
- Framework: pytest (API + ML worker), Vitest (frontend)

### Additional Technical Assumptions and Requests

- Python 3.11+ para API e ML worker (compatibilidade com MediaPipe e Parselmouth)
- Node.js 18+ para frontend
- FFmpeg disponível no ML worker (HF Spaces Dockerfile)
- MediaPipe roda em CPU (sem GPU — HF Spaces free tier é CPU only, 16GB RAM)
- Whisper model: `medium` (melhor trade-off para PT-BR)
- LLM: Gemini 2.0 Flash (Google, free tier — 15 RPM)
- Deploy: Vercel free (frontend) + Render free (API) + HF Spaces free (ML worker)
- Supabase projeto gratuito para MVP
- **Custo total estimado: $0/mês**

---

## Epic List

### Epic 1: Foundation, Upload & Processing Skeleton

Estabelecer infraestrutura do projeto (monorepo, Next.js, FastAPI, Supabase) e entregar o fluxo completo de upload de vídeo com split audio/video e tracking de status — sem análise real ainda, mas com pipeline funcional end-to-end.

### Epic 2: Analysis Engines (4 Dimensões)

Implementar os 4 motores de análise (postura, gestual básico, tom de voz, vícios de linguagem) e o serviço de agregação de métricas. Cada story entrega uma dimensão funcional e testável.

### Epic 3: Report Generation & Dashboard

Integrar LLM para geração de feedback qualitativo, construir o dashboard de relatório com scores e detalhamento por dimensão, e fechar o loop com rating do usuário.

---

## Epic 1: Foundation, Upload & Processing Skeleton

**Goal:** Entregar a base do projeto com um fluxo funcional end-to-end: o usuário faz upload de um vídeo, o sistema armazena, separa áudio/vídeo, e mostra o status do processamento. Não há análise inteligente ainda, mas a infraestrutura está pronta para recebê-la.

### Story 1.1: Project Scaffolding & Dev Environment

As a developer,
I want the monorepo structure with Next.js frontend, FastAPI backend, and Supabase integration configured,
so that I have a working dev environment to build features on.

**Acceptance Criteria:**

1. Monorepo criado com `apps/web/` (Next.js 14+ com App Router, Tailwind CSS) e `apps/api/` (FastAPI com Python 3.11+)
2. Frontend roda com `npm run dev` e exibe página de health check na rota `/`
3. Backend roda com `uvicorn` e responde `GET /health` com `{"status": "ok"}`
4. Supabase client configurado no backend com variáveis de ambiente (`.env`)
5. Linting configurado: ESLint (frontend) + Ruff (backend)
6. `.gitignore` adequado para ambos os stacks
7. README com instruções de setup local

### Story 1.2: Video Upload UI & Storage

As a user,
I want to upload a video file through the web interface,
so that the system can process it for oratory evaluation.

**Acceptance Criteria:**

1. Página de upload com drag-and-drop zone e botão de seleção de arquivo
2. Validação client-side: aceita MP4/WebM, max 500MB, max 10 min de duração
3. Exibe mensagem de erro clara para arquivos inválidos (formato, tamanho, duração)
4. Upload faz stream para Supabase Storage via API backend
5. Após upload bem-sucedido, cria registro na tabela `evaluations` com status `uploaded`
6. UI exibe progresso de upload (% concluído)
7. Após upload, redireciona para tela de processamento com o ID da avaliação

### Story 1.3: Video Ingestion & Audio/Video Split

As a system,
I want to receive an uploaded video and split it into separate audio and video streams,
so that each analysis engine can process its relevant stream independently.

**Acceptance Criteria:**

1. Worker assíncrono é disparado quando avaliação entra no status `uploaded`
2. FFmpeg extrai áudio (WAV 16kHz mono) e mantém referência ao vídeo original
3. Arquivos processados são armazenados temporariamente (Supabase Storage ou filesystem local)
4. Status da avaliação atualizado para `processing` com substatus `splitting`
5. Em caso de erro no FFmpeg, status atualizado para `error` com mensagem descritiva
6. Logging estruturado registra início, duração e resultado do split
7. Endpoint `GET /evaluations/{id}/status` retorna status atual com substatus

### Story 1.4: Processing Status UI & Polling

As a user,
I want to see the current processing status of my video in real-time,
so that I know the system is working and approximately how long it will take.

**Acceptance Criteria:**

1. Tela de processamento mostra etapa atual (ex: "Separando áudio e vídeo...")
2. Frontend faz polling do endpoint de status a cada 3 segundos
3. Exibe indicador visual de progresso (spinner ou progress bar por etapa)
4. Quando status muda para `completed`, redireciona automaticamente para relatório
5. Quando status muda para `error`, exibe mensagem de erro amigável com opção de tentar novamente
6. Tela funciona em mobile (responsiva)

---

## Epic 2: Analysis Engines (4 Dimensões)

**Goal:** Implementar os 4 motores de análise que processam o vídeo e áudio para extrair métricas quantitativas nas dimensões de postura, gestual básico, tom de voz e vícios de linguagem. Cada dimensão é um módulo independente que recebe o stream relevante e produz métricas estruturadas.

### Story 2.1: Voice Analysis — Transcription & Prosody

As a user,
I want my speech transcribed and analyzed for prosodic quality,
so that I can understand my speaking pace, vocal projection, and pitch variation.

**Acceptance Criteria:**

1. Whisper transcreve o áudio em PT-BR com timestamps por palavra
2. Transcrição armazenada na tabela `transcriptions` vinculada à avaliação
3. Parselmouth extrai: pitch médio (Hz), variação de pitch (semitones), intensidade média (dB), duração de silêncios
4. WPM calculado a partir dos timestamps da transcrição (total palavras / duração líquida)
5. Razão fala/silêncio calculada
6. Métricas armazenadas em JSON estruturado na tabela `analysis_results` com `dimension = 'voice'`
7. Status da avaliação atualizado com substatus `analyzing_voice`
8. Erro em Whisper ou Parselmouth não bloqueia pipeline — registra falha e continua

### Story 2.2: Filler Detection — Linguistic Analysis

As a user,
I want my speech fillers and verbal tics detected and counted,
so that I know which verbal habits I need to work on.

**Acceptance Criteria:**

1. Fillers detectados na transcrição via regex + NLP: "né", "tipo", "então", "éee", "hum", "aí", "assim", "basicamente"
2. Cada filler registrado com timestamp (início) e contexto (3 palavras antes/depois)
3. Total de fillers por minuto calculado
4. Top 3 fillers mais frequentes identificados
5. Diversidade léxical (type-token ratio) calculada na transcrição
6. Métricas armazenadas em JSON estruturado com `dimension = 'fillers'`
7. Depende de Story 2.1 (precisa da transcrição com timestamps)

### Story 2.3: Posture Analysis — Body Pose Estimation

As a user,
I want my body posture analyzed throughout the video,
so that I can understand if I maintain confident, open posture while speaking.

**Acceptance Criteria:**

1. MediaPipe Pose processa frames do vídeo (sampling: 1-2 fps para performance)
2. 33 keypoints extraídos por frame com coordenadas normalizadas
3. Score de alinhamento postural calculado (ângulos ombros, coluna, cabeça) — escala 0-100
4. % do tempo em postura aberta vs fechada classificado (baseado em ângulo dos ombros e posição dos braços)
5. Score de estabilidade calculado (variância da posição do centro de massa ao longo do tempo)
6. Métricas armazenadas em JSON estruturado com `dimension = 'posture'`
7. Processamento resiliente: frames com detecção falha são ignorados (log + skip)

### Story 2.4: Basic Gesture & Gaze Analysis

As a user,
I want basic feedback on my hand gestures and eye contact,
so that I know if I'm gesticulating enough and looking at my audience.

**Acceptance Criteria:**

1. MediaPipe Hands detecta presença/ausência de mãos visíveis por frame (sampling 1-2 fps)
2. % do tempo com gesticulação ativa calculado (mãos visíveis e em movimento)
3. Zona de gesticulação classificada (acima/abaixo da cintura, baseado nos keypoints de pose)
4. MediaPipe Face Mesh estima direção do olhar por frame
5. % de contato visual com câmera estimado (gaze direction within threshold)
6. Métricas armazenadas em JSON estruturado com `dimension = 'gesture'`
7. Se detecção de mãos ou face falhar em > 50% dos frames, métrica marcada como `low_confidence`

### Story 2.5: Metrics Aggregation Service

As a system,
I want all dimension metrics aggregated into a single structured payload,
so that the LLM can generate a comprehensive report from complete data.

**Acceptance Criteria:**

1. Serviço coleta resultados das 4 dimensões da tabela `analysis_results`
2. Calcula score geral ponderado (média das 4 dimensões, peso igual por default)
3. Gera JSON agregado com: scores por dimensão, score geral, métricas detalhadas, metadados (duração do vídeo, frames processados, etc.)
4. JSON salvo na tabela `aggregated_metrics` vinculado à avaliação
5. Status atualizado para `analyzed` quando todas as dimensões completam
6. Se alguma dimensão falhou, inclui flag `incomplete_dimensions` com lista das dimensões faltantes
7. Dispara próxima etapa (relatório LLM) quando agregação completa

---

## Epic 3: Report Generation & Dashboard

**Goal:** Fechar o loop de valor: transformar métricas quantitativas em feedback qualitativo acionável via LLM e apresentar tudo num dashboard claro e útil para o usuário, incluindo detalhamento por dimensão e mecanismo de feedback.

### Story 3.1: LLM Report Generation

As a system,
I want to generate a qualitative feedback report from the aggregated metrics using an LLM,
so that the user receives human-readable, actionable insights about their oratory.

**Acceptance Criteria:**

1. Prompt estruturado envia métricas agregadas para Claude API (Haiku ou Sonnet)
2. Prompt inclui: scores por dimensão, métricas detalhadas, contexto sobre oratória, instruções de formato
3. LLM retorna: resumo geral (2-3 frases), feedback por dimensão (pontos fortes + pontos a melhorar + dica prática), score qualitativo (ex: "Bom", "Precisa atenção")
4. Resposta do LLM parseada e armazenada em JSON estruturado na tabela `reports`
5. Status da avaliação atualizado para `completed`
6. Em caso de erro na API do LLM, retry com backoff (max 3 tentativas) antes de marcar como `error`
7. Custo da chamada LLM logado para monitoramento de custo por avaliação

### Story 3.2: Report Dashboard UI

As a user,
I want to see a clear dashboard with my oratory scores and key insights,
so that I can quickly understand my overall performance and where to improve.

**Acceptance Criteria:**

1. Dashboard exibe score geral (0-100) com indicador visual (cor: verde/amarelo/vermelho)
2. 4 cards de dimensão com: nome, score (0-100), indicador visual, resumo de 1 linha
3. Resumo geral do LLM exibido abaixo do score geral
4. Cada card de dimensão é clicável → navega para detalhamento
5. Layout responsivo: grid 2x2 em desktop, stack vertical em mobile
6. Dados carregados do endpoint `GET /evaluations/{id}/report`
7. Loading state enquanto dados são buscados

### Story 3.3: Dimension Detail View

As a user,
I want to see detailed analysis for each dimension,
so that I can understand specific metrics and get targeted improvement tips.

**Acceptance Criteria:**

1. Página de detalhe mostra: score da dimensão, todas as métricas específicas, feedback do LLM (pontos fortes, melhorias, dica)
2. Para voz: exibe WPM, variação de pitch, projeção vocal, razão fala/silêncio
3. Para fillers: exibe fillers/minuto, top 3 fillers, diversidade léxical, lista de ocorrências com timestamps
4. Para postura: exibe score de alinhamento, % postura aberta/fechada, estabilidade
5. Para gestual: exibe % gesticulação ativa, zona predominante, % contato visual
6. Métricas com indicador de referência (ex: "WPM: 145 — ideal: 130-170 ✓")
7. Botão de voltar para dashboard
8. Se dimensão estiver marcada como `low_confidence`, exibir aviso contextual

### Story 3.4: Report Rating & Feedback

As a user,
I want to rate the quality of my evaluation report,
so that the system can track user satisfaction and improve over time.

**Acceptance Criteria:**

1. Componente de rating (1-5 estrelas) visível no dashboard do relatório
2. Campo opcional de comentário (textarea, max 500 chars)
3. Rating salvo via `POST /evaluations/{id}/rating` na tabela `report_ratings`
4. Confirmação visual após envio ("Obrigado pelo feedback!")
5. Rating só pode ser enviado uma vez por avaliação (idempotente)
6. Dados de rating disponíveis para análise de KPI (satisfação média)

---

## Next Steps

### UX Expert Prompt

> @ux-design-expert: Revise o PRD em `docs/prd.md`, seções "User Interface Design Goals" e "Core Screens and Views". Crie o frontend-spec com wireframes conceituais para as 5 telas principais (Landing/Upload, Processing, Report Dashboard, Dimension Detail, Rating). Considere o fluxo single-task e progressive disclosure. Stack: Next.js + Tailwind CSS, web responsive com foco desktop.

### Architect Prompt

> @architect: Revise o PRD completo em `docs/prd.md` e o Project Brief em `docs/brief.md`. Crie a arquitetura técnica para o Oratória Avaliador: monorepo Next.js + FastAPI + Supabase, pipeline assíncrono de processamento de vídeo (FFmpeg + MediaPipe + Whisper + Parselmouth + LLM), deploy Vercel + Railway. Foco em: schema do banco, estrutura de diretórios, contratos de API, e design do pipeline de processamento assíncrono.

---

*PRD gerado por @pm (Morgan) — YOLO Mode*
*Inputs: Project Brief (docs/brief.md) + Brainstorm (docs/research/brainstorm-avaliacao-oratoria-ia.md)*
