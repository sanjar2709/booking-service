from apps.common.tests.factories import PASSWORD, auth, create_user
from apps.users.models import Role
from core.security import create_refresh_token


async def test_register(client):
    response = await client.post('/auth/register', json={'email': 'New@Example.com', 'password': PASSWORD})

    assert response.status_code == 201
    assert response.json()['email'] == 'new@example.com'
    assert response.json()['role'] == 'client'
    assert 'password' not in response.text


async def test_register_duplicate_email(client):
    await create_user(email='taken@example.com')

    response = await client.post('/auth/register', json={'email': 'TAKEN@example.com', 'password': PASSWORD})

    assert response.status_code == 400


async def test_register_validation_error_format(client):
    response = await client.post('/auth/register', json={'email': 'not-an-email', 'password': 'short'})

    assert response.status_code == 422
    error = response.json()['error']
    assert error['code'] == 'unprocessable_entity'
    assert {d['field'] for d in error['details']} == {'email', 'password'}


async def test_client_cannot_register_as_admin(client):
    data = {'email': 'a@example.com', 'password': PASSWORD, 'role': 'admin'}

    response = await client.post('/auth/register', json=data)

    assert response.json()['role'] == 'client'


async def test_login_and_me(client):
    await create_user(email='me@example.com')

    tokens = (await client.post('/auth/login', json={'email': 'me@example.com', 'password': PASSWORD})).json()
    response = await client.get('/auth/me', headers={'Authorization': f'Bearer {tokens["access"]}'})

    assert response.status_code == 200
    assert response.json()['email'] == 'me@example.com'


async def test_login_wrong_password(client):
    await create_user(email='me@example.com')

    response = await client.post('/auth/login', json={'email': 'me@example.com', 'password': 'wrong-password'})

    assert response.status_code == 401


async def test_inactive_user_cannot_login(client):
    await create_user(email='me@example.com', is_active=False)

    response = await client.post('/auth/login', json={'email': 'me@example.com', 'password': PASSWORD})

    assert response.status_code == 401


async def test_refresh_token_cannot_be_used_as_access_token(client):
    user = await create_user()

    response = await client.get('/auth/me', headers={'Authorization': f'Bearer {create_refresh_token(user.id)}'})

    assert response.status_code == 401


async def test_refresh(client):
    user = await create_user()

    response = await client.post('/auth/refresh', json={'refresh': create_refresh_token(user.id)})

    assert response.status_code == 200
    assert {'access', 'refresh'} <= response.json().keys()


async def test_refresh_with_garbage(client):
    assert (await client.post('/auth/refresh', json={'refresh': 'garbage'})).status_code == 401


async def test_update_me_cannot_change_role(client):
    user = await create_user()

    response = await client.patch('/auth/me', json={'phone': '+998901112233', 'role': Role.ADMIN}, headers=auth(user))

    assert response.json()['phone'] == '+998901112233'
    assert response.json()['role'] == 'client'


async def test_login_is_rate_limited(client):
    for _ in range(10):
        await client.post('/auth/login', json={'email': 'x@example.com', 'password': 'wrong-password'})

    response = await client.post('/auth/login', json={'email': 'x@example.com', 'password': 'wrong-password'})

    assert response.status_code == 429
    assert 'Retry-After' in response.headers
