# Oratoria Avaliador

IA que avalia oratoria em video — postura, gestual, tom de voz e vicios de linguagem.

## Arquitetura

- **Frontend:** Next.js 14 + Tailwind CSS (Vercel free)
- **API:** Python FastAPI (Render free)
- **ML Worker:** Python FastAPI + MediaPipe + Whisper + Parselmouth (HF Spaces free)
- **Database:** Supabase (PostgreSQL + Storage, free)
- **LLM:** Gemini 2.0 Flash (free)

## Setup Local

### Pre-requisitos

- Node.js 18+
- Python 3.11+
- FFmpeg

### Frontend

```bash
cd apps/web
npm install
cp .env.local.example .env.local
npm run dev
# http://localhost:3000
```

### API

```bash
cd apps/api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Editar .env com credenciais do Supabase
uvicorn app.main:app --reload
# http://localhost:8000
```

### ML Worker

```bash
cd ml-worker
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Editar .env com credenciais
uvicorn app:app --port 7860 --reload
# http://localhost:7860
```

## Docs

- [Project Brief](docs/brief.md)
- [PRD](docs/prd.md)
- [Architecture](docs/architecture.md)
- [Stories](docs/stories/)
