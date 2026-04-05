import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import routes
from app.core import rag_core

app = FastAPI(title='RAG Chatbot')

frontend_dir = Path(__file__).resolve().parents[1] / 'frontend'
allowed_origins = [origin.strip() for origin in os.getenv('ALLOWED_ORIGINS', '*').split(',') if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(routes.router, prefix='/api')
app.mount('/assets', StaticFiles(directory=frontend_dir), name='assets')


@app.on_event('startup')
def startup_event():
    rag_core.initialize_database()


@app.get('/')
def read_root():
    return FileResponse(frontend_dir / 'index.html')


@app.get('/healthz')
def healthcheck():
    return {'status': 'ok'}
