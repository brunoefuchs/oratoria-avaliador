# Project Brief: Oratória Avaliador

## Executive Summary

Plataforma de IA que avalia o desempenho de oratória em vídeo, analisando 4 dimensões: **postura corporal**, **gestual**, **tom de voz** e **vícios de linguagem**. O sistema recebe um vídeo do usuário e entrega um relatório detalhado com scores quantitativos e feedback qualitativo acionável, usando uma arquitetura híbrida que combina ferramentas especializadas de extração de features com LLMs para geração de insights.

**Problema:** Pessoas que falam em público (palestras, apresentações, aulas, vídeos) não têm feedback objetivo e estruturado sobre sua performance. Treinadores de oratória são caros e pouco acessíveis.

**Proposta de valor:** Feedback instantâneo, objetivo e acessível sobre oratória, com análise multidimensional que seria impossível para um humano fazer frame-a-frame.

---

## Problem Statement

### Dor atual

- Quem treina oratória depende de feedback subjetivo de terceiros ou de se assistir em vídeo sem critérios estruturados
- Treinadores/coaches de oratória cobram caro e não estão disponíveis em tempo real
- Auto-avaliação é enviesada — a pessoa não percebe seus próprios vícios e padrões
- Não existe ferramenta acessível que analise oratória de forma multidimensional (visual + áudio + linguística)

### Impacto

- Profissionais perdem oportunidades por comunicação ineficaz
- Criadores de conteúdo publicam vídeos sem consciência de problemas de apresentação
- Professores/instrutores não recebem feedback sobre engajamento corporal e vocal

### Por que soluções existentes não resolvem

- Apps de teleprompter/gravação não analisam performance
- Ferramentas de speech-to-text não avaliam qualidade prosódica ou postural
- Coaches humanos são caros, subjetivos e não escalam

---

## Proposed Solution

### Conceito

Sistema web que recebe upload de vídeo e gera relatório de avaliação de oratória em 4 dimensões, usando **arquitetura híbrida**:

1. **Extração de features** com ferramentas especializadas (MediaPipe, Whisper, Parselmouth)
2. **Análise qualitativa** com LLM (Claude/GPT) que interpreta os dados e gera feedback humano

### Fluxo principal

```
Upload de vídeo
  → Split audio/video
  → Video → MediaPipe (pose + hands + face) → métricas visuais
  → Audio → Whisper (transcrição) + Parselmouth (prosódia) + contagem de fillers
  → Métricas agregadas → LLM → Relatório com scores e feedback acionável
```

### Diferencial

- Análise multidimensional (4 dimensões) que nenhuma ferramenta oferece hoje
- Combina precisão numérica (ferramentas especializadas) com feedback natural (LLM)
- Custo-benefício superior a coaches humanos
- Escalável e disponível 24/7

---

## Target Users

### Segmento Primário: Profissionais que falam em público

- Palestrantes, apresentadores corporativos, professores
- Fazem apresentações regularmente e querem melhorar
- Já se gravam mas não sabem o que analisar
- Dispostos a investir em autodesenvolvimento

### Segmento Secundário: Criadores de conteúdo

- YouTubers, podcasters, instrutores online
- Produzem vídeos recorrentes e querem aumentar qualidade
- Buscam engajamento e retenção da audiência
- Sensíveis a métricas de performance

### Segmento Terciário: Estudantes e iniciantes

- Pessoas preparando apresentações acadêmicas/profissionais
- Buscando treinar para entrevistas, pitches, defesas de TCC
- Orçamento limitado, não podem pagar coach

---

## Goals & Success Metrics

### Business Objectives

- Validar product-market fit com MVP funcional
- Atingir 100 avaliações processadas no primeiro mês pós-lançamento
- Obter NPS >= 40 entre primeiros usuários
- Custo por avaliação < R$ 2,00 (infra + API)

### User Success Metrics

- Usuário recebe relatório em < 5 minutos após upload
- Relatório é percebido como útil (rating >= 4/5)
- Usuário retorna para avaliar novo vídeo (retenção D7 >= 30%)
- Feedback é acionável — usuário sabe O QUE melhorar

### Key Performance Indicators (KPIs)

- **Taxa de conclusão:** % de uploads que geram relatório completo
- **Tempo de processamento:** Média de tempo entre upload e relatório pronto
- **Custo por avaliação:** Custo médio de infra + APIs por vídeo processado
- **Satisfação:** Rating médio do relatório (1-5)
- **Retenção:** % de usuários que voltam em 7 dias

---

## MVP Scope

### Core Features (Must Have)

- **Upload de vídeo:** Aceitar MP4/WebM, até 10 minutos de duração
- **Análise de postura:** Score de alinhamento postural via MediaPipe Pose (pose estimation com 33 keypoints)
- **Análise gestual básica:** Detecção de gesticulação (presença/ausência de gestos com as mãos) e contato visual estimado via MediaPipe Face Mesh — sem heatmaps ou tracking detalhado
- **Análise de tom de voz:** WPM, variação de pitch, projeção vocal via Whisper + Parselmouth
- **Detecção de vícios de linguagem:** Contagem de fillers ("né", "tipo", "então", "éee") via transcrição + regex/NLP
- **Relatório unificado:** Dashboard com scores nas 4 dimensões + feedback qualitativo gerado por LLM
- **Interface web básica:** Upload, processamento, visualização do relatório

### Out of Scope for MVP

- Análise gestual avançada (heatmaps de movimentação, classificação de tipos de gestos, tracking contínuo) — V2
- Processamento em tempo real / streaming
- Comparação histórica entre vídeos
- App mobile nativo
- Gravação direta pela plataforma (webcam)
- Integração com plataformas de vídeo (YouTube, Zoom)
- Gamificação / sistema de progresso
- Multi-idioma (MVP: português BR apenas)
- Autenticação avançada / planos pagos

### MVP Success Criteria

O MVP é bem-sucedido se:
1. Processa um vídeo de até 10 min e gera relatório em < 5 min
2. O relatório cobre as 4 dimensões com scores numéricos
3. O feedback qualitativo é coerente e acionável (validado com 5+ usuários)
4. Custo por avaliação < R$ 2,00

---

## Post-MVP Vision

### Phase 2 Features

- **Análise gestual completa:** Hand tracking, heatmap de movimentação, contato visual
- **Histórico e comparação:** Evolução do score ao longo do tempo
- **Gravação pela plataforma:** Webcam direto na interface
- **Relatório PDF exportável:** Para compartilhar com coaches/mentores

### Long-term Vision

- Plataforma de referência para treino de oratória no Brasil
- IA que não só avalia, mas **ensina** — sugere exercícios e treinos personalizados
- Integrações com ferramentas corporativas (Zoom, Teams, Google Meet) para feedback pós-reunião
- Marketplace de coaches que usam a plataforma como ferramenta de diagnóstico

### Expansion Opportunities

- B2B: Empresas treinando equipes de vendas/apresentação
- Educação: Universidades avaliando apresentações acadêmicas
- White-label: API de avaliação de oratória para outras plataformas
- Internacionalização: Inglês, espanhol

---

## Technical Considerations

### Platform Requirements

- **Target Platforms:** Web (browser-based), responsive
- **Browser Support:** Chrome, Firefox, Safari, Edge (últimas 2 versões)
- **Performance Requirements:** Processamento de vídeo de 10 min em < 5 min; UI responsiva < 200ms

### Technology Preferences

- **Frontend:** Next.js (React) + Tailwind CSS
- **Backend API:** Python (FastAPI) — API leve no Render (free, 512MB RAM)
- **ML Worker:** Python — Processamento pesado no Hugging Face Spaces (free, 16GB RAM)
- **LLM:** Gemini 2.0 Flash (Google, free tier)
- **Database:** Supabase (PostgreSQL + Auth + Storage)
- **Hosting:** Vercel free (frontend) + Render free (API) + HF Spaces free (ML) = **$0/mês**

### Architecture Considerations

- **Repository Structure:** Monorepo com frontend (Next.js) e backend (Python) separados
- **Service Architecture:** Frontend → API Gateway → Workers de processamento (async)
- **Integration Requirements:** MediaPipe, OpenAI Whisper, Parselmouth, Claude/GPT API
- **Security/Compliance:** Vídeos deletados após processamento (ou período configurável), dados pessoais mínimos

---

## Constraints & Assumptions

### Constraints

- **Budget:** Projeto pessoal / bootstrap — custo de infra: $0/mês (todos os serviços em free tier)
- **Timeline:** MVP funcional em 4-6 semanas
- **Resources:** Desenvolvedor solo (Bruno)
- **Technical:** Processamento de vídeo pesado exige backend com GPU ou serviços cloud; APIs de LLM têm custo por token

### Key Assumptions

- MediaPipe Pose roda eficientemente no backend sem GPU dedicada (CPU ok para vídeos curtos)
- Whisper (small/medium) oferece qualidade suficiente de transcrição para PT-BR
- Parselmouth extrai métricas prosódicas de forma confiável em áudio de qualidade variada
- Custo de API do LLM (Claude/GPT) por relatório fica < R$ 1,00
- Usuários estão dispostos a esperar 2-5 minutos pelo relatório
- Vídeos de webcam/celular têm qualidade suficiente para pose estimation

---

## Risks & Open Questions

### Key Risks

- **Qualidade de pose estimation em vídeos amadores:** Iluminação ruim, ângulos estranhos, resolução baixa podem comprometer a análise do MediaPipe
- **Custo de processamento escalando:** Se cada vídeo exige CPU intensiva + API calls, o custo pode inviabilizar
- **Precisão da detecção de fillers em PT-BR:** Modelos de STT podem não captar bem hesitações e fillers em português
- **Expectativa vs realidade:** Usuários podem esperar feedback tão bom quanto de um coach humano
- **Latência de processamento:** Pipeline com múltiplas etapas pode ultrapassar os 5 min

### Open Questions

- Whisper local vs API — qual a melhor relação custo/qualidade para PT-BR?
- Qual o threshold mínimo de qualidade de vídeo aceitável?
- Como calibrar os scores (o que é "boa postura"?) — precisa de dataset de referência?
- Processing pipeline síncrono ou assíncrono com fila?
- Armazenamento de vídeos: S3/Supabase Storage ou processar e deletar?

### Areas Needing Further Research

- Benchmarks de MediaPipe Pose em vídeos de webcam (precisão real)
- Qualidade do Whisper (small vs medium vs large) para PT-BR com sotaques
- Ferramentas/APIs de detecção de fillers específicas para português
- Custos reais de processamento por vídeo (CPU time + API costs)
- Estado da arte em avaliação automática de oratória (papers acadêmicos)

---

## Appendices

### A. Research Summary

Brainstorm completo disponível em `docs/research/brainstorm-avaliacao-oratoria-ia.md`, cobrindo:
- 4 dimensões de avaliação com abordagens técnicas detalhadas
- 3 opções de arquitetura analisadas (pipeline modular, multimodal end-to-end, híbrida)
- Métricas deriváveis por dimensão
- Recomendação de arquitetura híbrida (ferramentas especializadas + LLM)

### C. References

- [MediaPipe Pose](https://developers.google.com/mediapipe/solutions/vision/pose_landmarker) — Pose estimation
- [OpenAI Whisper](https://github.com/openai/whisper) — Speech-to-text
- [Parselmouth](https://github.com/YannickJadworski/Parselmouth) — Análise prosódica (Python wrapper para Praat)
- [FastAPI](https://fastapi.tiangolo.com/) — Backend Python
- [Next.js](https://nextjs.org/) — Frontend React
- [Supabase](https://supabase.com/) — Database + Auth + Storage

---

## Next Steps

### Immediate Actions

1. Revisar e validar este Project Brief
2. Inicializar repositório git e estrutura do projeto
3. Criar PRD detalhado a partir deste brief (handoff para @pm)
4. Pesquisar custos reais de API (Whisper, Claude, infra)
5. Criar PoC mínima: upload de vídeo → extração de 1 métrica → feedback simples

### PM Handoff

This Project Brief provides the full context for Oratória Avaliador. Please start in 'PRD Generation Mode', review the brief thoroughly to work with the user to create the PRD section by section as the template indicates, asking for any necessary clarification or suggesting improvements.

---

*Project Brief gerado por @analyst (Atlas) — YOLO Mode*
*Baseado em: docs/research/brainstorm-avaliacao-oratoria-ia.md*
