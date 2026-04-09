# Handoff: Sessao Epic 4 + Epic 5 — Feedback do Mentor

**Data:** 2026-04-08 → 2026-04-09
**Contexto:** 2 epics implementados em sequencia apos feedback do mentor de oratoria
**Status:** Tudo pushado para `origin/main`, banco atualizado, pronto para testes

---

## Resumo Executivo

| Epic | Stories | Commits | Status |
|------|---------|---------|--------|
| **Epic 4** — Ajustes do Mentor | 6 stories (4.1-4.6) | `c2a64ef` | Pushed |
| **Epic 5** — Raio-X do Mentor | 10 stories (5.1-5.10) | `57c53f9`, `3aa5cf7` | Pushed |
| Setup local | dev.sh + porta 8002 | `6b77b76` | Pushed |

**Total da sessao:** 4 commits, 43 arquivos modificados, ~4200 linhas adicionadas.

---

## Epic 4 — Ajustes do Mentor (Calibracao + Terminologia)

### Origem
Mentor avaliou um relatorio real e anotou correcoes em 10 imagens (em `ajustes oratoria/`).

### Stories Implementadas

| Story | Descricao | Arquivos |
|-------|-----------|----------|
| **4.1** | Fix bugs: zona gestual, distribuicao do olhar, filler "ne" | `gesture_analyzer.py`, `filler_detector.py` |
| **4.2** | Renomear 11+ termos tecnicos para linguagem de oratoria | Frontend `[id]/page.tsx`, `[dimension]/page.tsx`, `report_generator.py` |
| **4.3** | Remover Arquetipos do score principal (extra bloqueado) | `aggregator.py`, frontend dashboard, `report_generator.py` |
| **4.4** | Reduzir peso de Zona/Olhar (10% cada) | `gesture_analyzer.py` |
| **4.5** | Exercicios LLM mais sucintos (max 2 frases) | `report_generator.py` |
| **4.6** | [Spike] Investigar contradicao voz vs variedade | (pendente — precisa video) |

### Mudancas chave

**Bugs corrigidos:**
- Zona gestual: media expandida 0.35-0.60 → **0.30-0.65**
- Distribuicao do olhar: floor de 50 quando eye_contact >= 80% (camera unica)
- Filler "ne": pattern adicional sem acento (Whisper transcreve sem)

**Terminologia (11+ substituicoes):**
| De | Para |
|----|------|
| Prosodia | **Diccao** |
| Pitch | **Tom** |
| Grounding | **Estabilidade Corporal** |
| Fillers | **Vicios de Linguagem** |
| Cluster de Fillers | **Problemas de Fluencia** |
| Diversidade Lexical | **Riqueza de Vocabulario** |
| Default | **Padroes** |
| Dimensoes Travadas | **Pilares Travados** |
| WPM | **Palavras por Minuto** |
| Score | **Pontuacao** |
| Sub-scores | **Pontuacoes** |

**Novos pesos do gesture_analyzer:**
| Componente | Antes | Depois |
|------------|-------|--------|
| Contato Visual | 30% | **35%** |
| Gesticulacao | 25% | **30%** |
| Duas Maos | 15% | 15% |
| Zona | 15% | **10%** |
| Distribuicao Olhar | 15% | **10%** |

**Pesos do aggregator (sem arquetipos):**
| Dimensao | Antes | Depois |
|----------|-------|--------|
| Variety | 0.25 | **0.29** |
| Voice | 0.20 | **0.24** |
| Gesture | 0.15 | **0.18** |
| Posture | 0.15 | **0.18** |
| Fillers | 0.10 | **0.11** |
| Archetypes | 0.15 | **REMOVIDO** |

---

## Epic 5 — Raio-X do Mentor (Camada Humana)

### Origem
Mentor fez um "Raio-X" completo do produto identificando 10 fragilidades organizadas em 3 niveis:
- **Nivel 1 (Emocional):** Falta identidade, contexto, estado emocional
- **Nivel 2 (Comunicacao):** Falta congruencia, analise temporal, replay, evolucao
- **Nivel 3 (Persuasao):** UX generica, sem onboarding, sem CTA

Notas do mentor: Filosofia 8/10, Dimensoes 7/10, Algoritmos 6/10, UX 6/10, Coaching 7/10, Diferencial 5/10.

### Stories Implementadas

| Story | Descricao | Arquivos chave |
|-------|-----------|----------------|
| **5.1** | Fix icones ScoreCard (dimensionKey prop) + copy home + guard rails LLM | `score-card.tsx`, `page.tsx`, `report_generator.py` |
| **5.2** | Questionario pre-avaliacao (5 perguntas, contexto + emocao + objetivo) | Migration 005, novas pages `/evaluate/[id]/context` |
| **5.3** | Pesos contextuais (7 perfis: palco, podcast, vendas, etc) | `aggregator.py` |
| **5.4** | Dashboard de evolucao com historico (`/evolution`) | Migration 006, novo endpoint, nova page |
| **5.5** | Analise temporal (3 tercos: abertura/meio/fechamento) | `temporal_analyzer.py` (novo) |
| **5.6** | Replay de video com timeline anotada | `video-player.tsx`, novo endpoint, page `/replay` |
| **5.7** | Dimensao de Congruencia (cruzar sinais entre canais) | `congruence_analyzer.py` (novo) |
| **5.8** | Fillers contextuais (nervoso vs estilistico) | `filler_detector.py` |
| **5.9** | Onboarding (3 slides) + CTA pos-relatorio | `onboarding.tsx` (novo) |
| **5.10** | Compartilhamento de relatorio com link expirable | Migration 007, novos endpoints, botao share |

### Arquivos Novos Criados

**ML Worker:**
- `ml-worker/workers/temporal_analyzer.py` — Analise por terco temporal
- `ml-worker/workers/congruence_analyzer.py` — Cruzamento de sinais entre canais

**Frontend:**
- `apps/web/src/components/onboarding.tsx` — 3 slides de boas-vindas
- `apps/web/src/components/video-player.tsx` — Player com timeline anotada
- `apps/web/src/app/evaluate/[id]/context/page.tsx` — Questionario pre-avaliacao
- `apps/web/src/app/evolution/page.tsx` — Dashboard de evolucao
- `apps/web/src/app/report/[id]/replay/page.tsx` — Replay com timeline

**Migrations Supabase:**
- `supabase/migrations/005_evaluation_context.sql` — Contexto do orador
- `supabase/migrations/006_user_token.sql` — Agrupamento por usuario
- `supabase/migrations/007_report_shares.sql` — Links de compartilhamento

### Pipeline Novo (ml-worker/app.py)

```
1. Splitting → audio + video
2. Postura
3. Gestos
4. Voz (Whisper + prosody)
5. Vicios de linguagem (com classificacao contextual nervoso/estilistico)
6. Variedade (meta-analise)
7. Arquetipos (dados salvos mas nao no score principal)
8. Buscar contexto do orador (questionario 5.2)
9. Aggregator com pesos contextuais (5.3)
9.5. Analise de congruencia (5.7 — informativo)
9.6. Analise temporal 3 tercos (5.5)
10. Report generator (LLM com contexto + congruencia + temporal + guard rails)
```

### Aspectos Importantes

**Guard rails LLM (5.1):**
Quando uma dimensao tem `confidence: low/failed`, o prompt do LLM recebe instrucao explicita para NAO dar coaching nessa dimensao — apenas mencionar que e inconclusiva e sugerir regravar.

**Contexto do orador no LLM (5.2):**
Respostas do questionario sao injetadas no prompt com instrucoes de adaptacao de tom:
- Nervoso (1-2): Tom EXTRA encorajador
- Confiante (4-5): Tom direto e desafiador
- Primeira avaliacao: Explicar metricas
- Adaptacao por contexto (vendas, palco, podcast, etc)

**Pesos contextuais (5.3):**
| Contexto | Variety | Voice | Gesture | Posture | Fillers |
|----------|---------|-------|---------|---------|---------|
| **Default** | 0.29 | 0.24 | 0.18 | 0.18 | 0.11 |
| Palco | 0.25 | 0.20 | 0.18 | 0.22 | 0.15 |
| Podcast | 0.30 | 0.35 | 0.10 | 0.05 | 0.20 |
| Vendas | 0.20 | 0.25 | 0.20 | 0.15 | 0.20 |
| Rede social | 0.25 | 0.20 | 0.20 | 0.15 | 0.20 |
| Reuniao | 0.20 | 0.25 | 0.15 | 0.20 | 0.20 |
| Aula | 0.25 | 0.25 | 0.20 | 0.15 | 0.15 |

**Padroes detectados pela analise temporal (5.5):**
- `crescente` — constroi energia ao longo
- `decrescente` — comeca forte e perde
- `vale` — abre/fecha bem mas perde no meio
- `pico` — forca no meio (desenvolvimento)
- `estavel` — performance constante

**Regras de congruencia (5.7) — 4 contradicoes detectadas:**
1. Voz entusiasmada (pitch >= 10 semitons) + postura fechada (open < 50%)
2. Volume alto (>= 65dB) + olhar para baixo (> 20%)
3. Gestos amplos (gesticulation >= 50%) + volume baixo (< 55dB)
4. Velocidade alta (WPM >= 170) + gesticulacao parada (< 20%)

---

## Setup de Desenvolvimento

### dev.sh — 1 comando para tudo

```bash
./dev.sh           # Roda local: API + ML Worker + Frontend
./dev.sh --share   # Mesma coisa + cria tunneis publicos para mostrar ao mentor
```

### Portas (atualizadas)

| Servico | Porta | Por que |
|---------|-------|---------|
| Frontend | **3000** | Padrao Next.js |
| API | **8002** | (era 8000, mudou pq o usuario tem outro projeto rodando em :8000) |
| ML Worker | **7860** | Padrao do Dockerfile |

### Bug fix em paralelo

`apps/api/app/services/dispatcher.py` tinha `callback_url = "http://localhost:8001"` — porta inexistente. Foi corrigido para `8002` (a porta real da API).

### Cloudflared (modo --share)

Cria 2 tunnels:
1. API → URL publica
2. Atualiza `apps/web/.env.local` com a URL da API
3. Reinicia o frontend automaticamente
4. Cria tunnel do frontend → URL publica
5. Mostra link final para o mentor

Logs em `.dev-logs/` (gitignored).

---

## Banco de Dados (Supabase)

### Migrations Aplicadas no Remoto

| Migration | Conteudo | Status |
|-----------|----------|--------|
| 001 | Schema base (`evaluations`) | Pre-existente |
| 002 | `analysis_results`, `transcriptions`, `aggregated_metrics` | Pre-existente |
| 003 | `reports`, `report_ratings` | Pre-existente |
| 004 | Evaluation v2 dimensions (forcas, melhorias, plano_12_semanas, mensagem_final) | Pre-existente |
| **005** | `evaluation_context` (questionario pre-avaliacao) | **Aplicada nesta sessao** |
| **006** | `user_token` na tabela evaluations | **Aplicada nesta sessao** |
| **007** | `report_shares` (links de compartilhamento) | **Aplicada nesta sessao** |

### Como aplicar no remoto

```bash
SUPABASE_DB_PASSWORD='SENHA' supabase db push
```

> **Aviso de seguranca:** A senha do DB foi compartilhada no chat para aplicar as migrations. **Trocar a senha** apos esta sessao.

---

## Onde estao as coisas

### Stories

```
docs/stories/
├── 4.0.epic-mentor-adjustments.md         # Epic 4 overview
├── 4.1.fix-scoring-bugs.story.md
├── 4.2.rename-terminology.story.md
├── 4.3.remove-archetypes-from-main.story.md
├── 4.4.adjust-gesture-weights.story.md
├── 4.5.improve-exercise-content.story.md
├── 4.6.spike-voice-variety-contradiction.story.md
├── 5.0.epic-raio-x-mentor.md              # Epic 5 overview
├── 5.1.quick-wins-ux-llm.story.md
├── 5.2.pre-evaluation-questionnaire.story.md
├── 5.3.contextual-weights.story.md
├── 5.4.evolution-dashboard.story.md
├── 5.5.temporal-analysis.story.md
├── 5.6.video-replay-timeline.story.md
├── 5.7.congruence-dimension.story.md
├── 5.8.contextual-fillers.story.md
├── 5.9.onboarding-cta.story.md
└── 5.10.report-sharing.story.md
```

### Workers (ml-worker/workers/)

| Arquivo | Status |
|---------|--------|
| `voice_analyzer.py` | Existente, modificado |
| `variety_analyzer.py` | Existente |
| `gesture_analyzer.py` | Existente, modificado (Epic 4 + 5.5 indireto) |
| `posture_analyzer.py` | Existente |
| `filler_detector.py` | Existente, modificado (Epic 4 + 5.8) |
| `archetype_classifier.py` | Existente (continua salvando dados) |
| `aggregator.py` | Existente, modificado (Epic 4 + 5.3) |
| `report_generator.py` | Existente, modificado (Epic 4 + 5.1, 5.2, 5.5, 5.7) |
| **`temporal_analyzer.py`** | **Novo (5.5)** |
| **`congruence_analyzer.py`** | **Novo (5.7)** |

---

## O que esta pendente

### Stories nao implementadas (precisam acoes externas)
- **4.6 [Spike]** — Investigar contradicao voz 51 vs variedade 14. Precisa do video do mentor para reprocessar.

### Tasks pendentes nas stories implementadas
- Testes de regressao em todas as stories Epic 4 e Epic 5 com video real
- Verificacao visual completa da terminologia em todas as paginas
- Validacao do comportamento do LLM com diferentes contextos do questionario

### Deploy
- Aplicacao roda **100% local** atualmente
- Para deploy publico: ml-worker e o gargalo (precisa de RAM significativa, free tiers nao aguentam)
- **Solucao recomendada:** Continuar local + `./dev.sh --share` quando precisar mostrar para terceiros
- Custo estimado para deploy real: $10-30/mes (Railway/Fly.io)

---

## Decisoes Tomadas

1. **YOLO mode** — Bruno preferiu execucao autonoma sem aprovacao por step
2. **dev.sh ao inves de docker-compose** — Mais simples, sem overhead de Docker
3. **Porta 8002 ao inves de 8000** — Conflito com outro projeto local (`transcricao-dqfb`)
4. **Cloudflared ao inves de Vercel** — Deploy parcial nao faz sentido se ml-worker nao deploya
5. **Arquetipos como "extra bloqueado"** — Mentor pediu para tirar do score principal mas continuar coletando dados
6. **Questionario opcional** — Usuario pode pular e receber coaching generico

---

## Proximos Passos Logicos

1. **Testar com video do mentor** — Reprocessar e validar que correcoes do Epic 4 funcionam
2. **Validar Epic 5 com mentor** — Mostrar via `./dev.sh --share` o questionario, evolucao, replay
3. **Resolver Spike 4.6** — Quando tiver video novo, rodar a investigacao
4. **Pensar em deploy real** — Quando tiver validacao positiva do mentor

---

**Quem implementou:** @pm Morgan, @po Pax, @dev Dex, @devops Gage (sequencia de agentes AIOX)
**Modo:** YOLO (autonomous)
**LLM:** Claude Opus 4.6 (1M context)
