from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core import settings

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
async def health():
    return {'status': 'ok'}
