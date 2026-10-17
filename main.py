from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from apps.bookings.router import router as bookings_router
from apps.specialists.router import router as specialists_router
from apps.users.router import router as auth_router
from core import settings
from core.db import DBSession
from core.exceptions import register_exception_handlers

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    docs_url='/api/docs',
    openapi_url='/api/openapi.json',
)

register_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.get('/api/health', tags=['health'])
async def health(db: DBSession):
    await db.execute(text('SELECT 1'))
    return {'status': 'ok', 'database': 'ok'}


app.include_router(auth_router, prefix='/api/v1')
app.include_router(specialists_router, prefix='/api/v1')
app.include_router(bookings_router, prefix='/api/v1')
