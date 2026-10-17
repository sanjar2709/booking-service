import asyncio
import os

import asyncpg
import pytest
from alembic import command
from alembic.config import Config
from dotenv import load_dotenv

# Tests use their own database, so local data is never touched.
# This has to happen before core.settings is imported anywhere.
load_dotenv()
os.environ['DB_NAME'] = f'{os.environ["DB_NAME"]}_test'

from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from apps.users.router import auth_limiter  # noqa: E402
from core import settings  # noqa: E402
from core.db import engine  # noqa: E402
from main import app  # noqa: E402


async def recreate_test_database():
    conn = await asyncpg.connect(
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        database='postgres',
    )
    try:
        await conn.execute(f'DROP DATABASE IF EXISTS "{settings.DB_NAME}" WITH (FORCE)')
        await conn.execute(f'CREATE DATABASE "{settings.DB_NAME}"')
    finally:
        await conn.close()


def pytest_sessionstart(session):
    asyncio.run(recreate_test_database())
    # Build the schema with the real migrations, so they get tested too
    command.upgrade(Config('alembic.ini'), 'head')


@pytest.fixture(autouse=True)
async def clean_db():
    yield
    async with engine.begin() as conn:
        await conn.execute(text('TRUNCATE users, services, specialists, bookings RESTART IDENTITY CASCADE'))


@pytest.fixture(autouse=True)
def reset_rate_limit():
    auth_limiter.reset()


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test/api/v1') as client:
        yield client
