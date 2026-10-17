import pytest

from apps.common.tests.factories import auth, create_specialist, create_user
from apps.users.models import Role

SERVICE = {'title': 'Haircut', 'duration_minutes': 45, 'price': '80000'}


@pytest.fixture
async def admin():
    return auth(await create_user(role=Role.ADMIN))


async def test_anyone_can_list_services_and_specialists(client):
    await create_specialist()

    assert len((await client.get('/services')).json()) == 1
    assert len((await client.get('/specialists')).json()) == 1


async def test_client_cannot_create_service(client):
    client_user = await create_user()

    assert (await client.post('/services', json=SERVICE, headers=auth(client_user))).status_code == 403


async def test_admin_creates_and_updates_service(client, admin):
    service = (await client.post('/services', json=SERVICE, headers=admin)).json()

    response = await client.patch(f'/services/{service["id"]}', json={'price': '90000'}, headers=admin)

    assert response.status_code == 200
    assert response.json()['price'] == '90000.00'


@pytest.mark.parametrize('bad', ({'duration_minutes': 0}, {'price': '-1'}, {'title': 'x' * 151}))
async def test_service_validation(client, admin, bad):
    assert (await client.post('/services', json={**SERVICE, **bad}, headers=admin)).status_code == 422


async def test_inactive_service_is_hidden(client, admin):
    service = (await client.post('/services', json={**SERVICE, 'is_active': False}, headers=admin)).json()

    assert service['id'] not in [s['id'] for s in (await client.get('/services')).json()]


async def test_working_hours(client, admin):
    specialist = (await client.post('/specialists', json={'full_name': 'Aziz'}, headers=admin)).json()
    hours = [{'weekday': d, 'start_time': '09:00', 'end_time': '18:00'} for d in range(5)]

    response = await client.put(f'/specialists/{specialist["id"]}/working-hours', json=hours, headers=admin)
    assert len(response.json()['working_hours']) == 5

    # Replacing the schedule removes the old rows
    response = await client.put(f'/specialists/{specialist["id"]}/working-hours', json=hours[:2], headers=admin)
    assert [h['weekday'] for h in response.json()['working_hours']] == [0, 1]


async def test_working_hours_validation(client, admin):
    specialist = (await client.post('/specialists', json={'full_name': 'Aziz'}, headers=admin)).json()
    url = f'/specialists/{specialist["id"]}/working-hours'
    day = {'weekday': 0, 'start_time': '09:00', 'end_time': '18:00'}

    assert (await client.put(url, json=[day, day], headers=admin)).status_code == 400
    assert (await client.put(url, json=[{**day, 'end_time': '08:00'}], headers=admin)).status_code == 422
    assert (await client.put(url, json=[{**day, 'weekday': 7}], headers=admin)).status_code == 422


async def test_set_services_and_filter(client, admin):
    specialist, service = await create_specialist()
    other = (await client.post('/services', json=SERVICE, headers=admin)).json()

    response = await client.put(
        f'/specialists/{specialist.id}/services', json={'service_ids': [service.id, other['id']]}, headers=admin
    )
    assert len(response.json()['services']) == 2

    assert len((await client.get('/specialists', params={'service_id': other['id']})).json()) == 1
    assert (await client.get('/specialists', params={'service_id': 999})).json() == []


async def test_set_unknown_service(client, admin):
    specialist, _ = await create_specialist()

    response = await client.put(f'/specialists/{specialist.id}/services', json={'service_ids': [999]}, headers=admin)

    assert response.status_code == 400


async def test_specialist_not_found(client):
    response = await client.get('/specialists/999')

    assert response.status_code == 404
    assert response.json()['error']['code'] == 'not_found'
