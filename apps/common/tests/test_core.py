import pytest
from fastapi import APIRouter
from httpx import ASGITransport, AsyncClient

from main import app


@pytest.fixture
async def raw_client():
    # Root base url and no re-raising, so we see exactly what a real client would get on a 500
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url='http://test') as client:
        yield client


@pytest.fixture
def broken_endpoint():
    router = APIRouter()

    @router.get('/api/test-error')
    async def boom():
        raise RuntimeError('secret internals')

    app.include_router(router)
    yield
    app.router.routes = [r for r in app.router.routes if getattr(r, 'path', '') != '/api/test-error']


async def test_health(raw_client):
    response = await raw_client.get('/api/health')

    assert response.json() == {'status': 'ok', 'database': 'ok'}


async def test_unhandled_error_hides_details(raw_client, broken_endpoint):
    response = await raw_client.get('/api/test-error')

    assert response.status_code == 500
    assert response.json()['error']['code'] == 'internal_server_error'
    assert 'secret' not in response.text
