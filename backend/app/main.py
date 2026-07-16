import os
from dotenv import load_dotenv

# Precisa vir ANTES dos imports de app.routers, porque app/ai/ollama_client.py
# lê a variável OLLAMA_MODEL assim que é importado.
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database import Base, engine
from app import models  # garante que os modelos são registrados antes do create_all
from app.routers import income, debts, plan, ai

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Livre de Dívidas API",
    description="API local para gestão financeira e quitação de dívidas, com análise via IA local (Ollama).",
    version="0.1.0",
)

# CORS só é necessário no modo de desenvolvimento (frontend em `npm run dev`,
# porta separada). No modo "tudo em um" (frontend buildado servido por aqui
# mesmo), a mesma origem já resolve isso, mas deixamos liberado para não
# atrapalhar quem estiver desenvolvendo com o Vite dev server.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:4173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Todas as rotas da API ficam sob /api, para não colidir com as rotas do frontend
app.include_router(income.router, prefix="/api")
app.include_router(debts.router, prefix="/api")
app.include_router(plan.router, prefix="/api")
app.include_router(ai.router, prefix="/api")


@app.get("/api/health")
def health_check():
    return {"status": "ok"}


# Serve o frontend já buildado (frontend/dist), se existir, na raiz "/".
# Isso permite abrir só http://localhost:8000 e ter tudo funcionando,
# sem precisar rodar `npm run dev` separadamente.
_FRONTEND_DIST = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "frontend", "dist"
)
_FRONTEND_DIST = os.path.normpath(_FRONTEND_DIST)

if os.path.isdir(_FRONTEND_DIST):
    app.mount("/", StaticFiles(directory=_FRONTEND_DIST, html=True), name="frontend")
