from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from core import settings
from core.db import DBSession

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    docs_url='/api/docs',
    openapi_url='/api/openapi.json',
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.get('/api/health', tags=('health',))
async def health(db: DBSession):
    await db.execute(text('SELECT 1'))
    return {'status': 'ok', 'database': 'ok'}
