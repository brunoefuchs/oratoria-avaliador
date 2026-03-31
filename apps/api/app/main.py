from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.callback import router as callback_router
from app.routes.evaluations import router as evaluations_router
from app.routes.health import router as health_router

app = FastAPI(title="Oratoria Avaliador API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(evaluations_router)
app.include_router(callback_router)
