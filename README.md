# Oratoria Avaliador

IA que avalia oratoria em video — analise multidimensional (variedade vocal, voz e diccao, presenca visual, postura, clareza verbal) com coaching personalizado por LLM e plano de evolucao de 12 semanas.

## Arquitetura

- **Frontend:** Next.js 14 + Tailwind CSS
- **API:** Python FastAPI
- **ML Worker:** Python FastAPI + MediaPipe + Whisper + Parselmouth
- **Database:** Supabase (PostgreSQL + Storage)
- **LLM:** Gemini 2.5 Flash

## Quick Start

```bash
./dev.sh           # roda local: API + ML Worker + Frontend
./dev.sh --share   # mesma coisa + cria tunneis publicos (cloudflared)
```

> O `dev.sh` sobe os 3 servicos em 1 terminal so. Logs unificados via tail.
> Modo `--share` cria tunneis cloudflared automaticamente para mostrar a outras pessoas sem deploy.

## Servicos e Portas

| Servico | Porta | URL |
|---------|-------|-----|
| Frontend (Next.js) | **3000** | http://localhost:3000 |
| API (FastAPI) | **8002** | http://localhost:8002 |
| ML Worker (FastAPI) | **7860** | http://localhost:7860 |

## Pre-requisitos

- Node.js 18+
- Python 3.11+
- FFmpeg
- Conta Supabase (DB + Storage)
- Gemini API Key (free tier)

## Setup Inicial

### 1. Variaveis de ambiente

```bash
cp .env.example .env
# Editar .env com:
# - SUPABASE_URL
# - SUPABASE_ANON_KEY
# - SUPABASE_SERVICE_ROLE_KEY
# - GEMINI_API_KEY
```

### 2. Frontend

```bash
cd apps/web
npm install
cd ../..
```

### 3. API

```bash
cd apps/api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd ../..
```

### 4. ML Worker

```bash
cd ml-worker
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd ..
```

### 5. Migrations Supabase

```bash
SUPABASE_DB_PASSWORD='sua_senha' supabase db push
```

### 6. Subir tudo

```bash
./dev.sh
```

## Setup Manual (sem dev.sh)

Se preferir rodar cada servico em um terminal separado:

```bash
# Terminal 1 — ML Worker
cd ml-worker && source .venv/bin/activate && uvicorn app:app --port 7860

# Terminal 2 — API
cd apps/api && source .venv/bin/activate && uvicorn app.main:app --port 8002 --reload

# Terminal 3 — Frontend
cd apps/web && npm run dev
```

## Compartilhar com Mentor (sem deploy)

```bash
./dev.sh --share
```

O script vai:
1. Subir os 3 servicos locais
2. Criar tunnel cloudflared para a API
3. Atualizar `apps/web/.env.local` com a URL do tunnel
4. Reiniciar o frontend para pegar a nova URL
5. Criar tunnel cloudflared para o frontend
6. Mostrar o **link publico** para compartilhar

Custo: **R$0** (mas precisa estar com a maquina ligada).

## Estrutura do Projeto

```
oratoria-avaliador/
├── apps/
│   ├── web/                # Next.js frontend
│   │   └── src/app/
│   │       ├── page.tsx                       # Home + onboarding
│   │       ├── evaluate/[id]/context/         # Questionario pre-avaliacao
│   │       ├── evolution/                     # Dashboard de evolucao
│   │       └── report/[id]/
│   │           ├── page.tsx                   # Dashboard do relatorio
│   │           ├── [dimension]/page.tsx       # Detalhe por dimensao
│   │           ├── replay/page.tsx            # Replay com timeline
│   │           └── shared/page.tsx            # View compartilhada
│   └── api/                # FastAPI
│       └── app/
│           ├── main.py
│           ├── routes/
│           │   ├── evaluations.py             # Upload, status, report, share
│           │   └── callback.py                # Callbacks do ml-worker
│           └── services/dispatcher.py         # Dispatch para ml-worker
├── ml-worker/              # FastAPI + ML pipeline
│   ├── app.py              # Pipeline principal (10 steps)
│   └── workers/
│       ├── voice_analyzer.py
│       ├── variety_analyzer.py
│       ├── gesture_analyzer.py
│       ├── posture_analyzer.py
│       ├── filler_detector.py
│       ├── archetype_classifier.py
│       ├── aggregator.py                      # Pesos contextuais
│       ├── temporal_analyzer.py               # Analise por terco
│       ├── congruence_analyzer.py             # Cruzamento entre canais
│       └── report_generator.py                # Gemini LLM
├── supabase/migrations/    # 7 migrations SQL
├── docs/
│   ├── stories/            # Stories Epic 1-5
│   └── sessions/           # Handoffs por mes
├── dev.sh                  # Script para subir tudo
└── README.md
```

## Pipeline ML (10 Steps)

1. Splitting → audio + video
2. Postura
3. Gestos + olhar
4. Voz (Whisper + Parselmouth)
5. Vicios de linguagem (com classificacao contextual)
6. Variedade (meta-analise temporal)
7. Arquetipos vocais (extra, nao no score principal)
8. Buscar contexto do orador (questionario)
9. Aggregator (pesos contextuais por tipo de apresentacao)
9.5. Congruencia (cruzamento entre canais)
9.6. Analise temporal (3 tercos)
10. Report LLM (Gemini com contexto, congruencia, temporal, guard rails)

## Dimensoes Avaliadas

| Dimensao | Peso default | Descricao |
|----------|--------------|-----------|
| Variedade Vocal | 29% | Variacao em volume, tom, velocidade, gesticulacao (meta-principio) |
| Voz e Diccao | 24% | WPM, tom, volume, pausas, anti-monotonia |
| Presenca Visual | 18% | Contato visual, gesticulacao, duas maos, zona, distribuicao do olhar |
| Postura e Presenca | 18% | Alinhamento, postura aberta, estabilidade corporal, movimento proposital |
| Clareza Verbal | 11% | Vicios de linguagem, hesitacoes, problemas de fluencia, riqueza de vocabulario |

> **Arquetipos Vocais** (Educador, Coach, Motivador, Amigo) sao calculados mas nao entram no score principal — sao um recurso extra a ser desbloqueado.

## Pesos Contextuais

Os pesos das dimensoes se adaptam ao contexto da apresentacao (selecionado no questionario pre-avaliacao):

| Contexto | Variety | Voice | Gesture | Posture | Fillers |
|----------|---------|-------|---------|---------|---------|
| Default | 0.29 | 0.24 | 0.18 | 0.18 | 0.11 |
| Palco presencial | 0.25 | 0.20 | 0.18 | **0.22** | 0.15 |
| Podcast/audio | 0.30 | **0.35** | 0.10 | 0.05 | 0.20 |
| Vendas | 0.20 | 0.25 | 0.20 | 0.15 | **0.20** |
| Rede social | 0.25 | 0.20 | 0.20 | 0.15 | 0.20 |
| Reuniao | 0.20 | 0.25 | 0.15 | 0.20 | 0.20 |
| Aula | 0.25 | 0.25 | 0.20 | 0.15 | 0.15 |

## Documentacao

- [Project Brief](docs/brief.md)
- [PRD](docs/prd.md)
- [Architecture](docs/architecture.md)
- [Stories Epic 1-5](docs/stories/)
- [Session Handoffs](docs/sessions/)
