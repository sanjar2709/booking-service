import asyncio
from datetime import datetime, timedelta

import pytest

from apps.bookings.models import Booking
from apps.common.tests.factories import TZ, at, auth, create_specialist, create_user, future_day
from apps.users.models import Role
from core.db import SessionLocal


@pytest.fixture
async def setup():
    specialist, service = await create_specialist(duration_minutes=30)
    user = await create_user()
    return specialist, service, user


def booking(specialist, service, starts_at):
    return {'specialist_id': specialist.id, 'service_id': service.id, 'starts_at': starts_at}


async def book(client, user, specialist, service, starts_at):
    return await client.post('/bookings', json=booking(specialist, service, starts_at), headers=auth(user))


async def test_create_booking(client, setup):
    specialist, service, user = setup
    day = future_day()

    response = await book(client, user, specialist, service, at(day, 10))

    assert response.status_code == 201
    data = response.json()
    assert datetime.fromisoformat(data['ends_at']) - datetime.fromisoformat(data['starts_at']) == timedelta(minutes=30)
    assert data['price'] == '80000.00'
    assert data['status'] == 'confirmed'


async def test_booking_requires_auth(client, setup):
    specialist, service, _ = setup

    assert (await client.post('/bookings', json=booking(specialist, service, at(future_day(), 10)))).status_code == 401


@pytest.mark.parametrize(('hour', 'minute', 'expected'), (
    (10, 15, 409),  # overlaps 10:00-10:30
    (9, 45, 409),   # 9:45-10:15 overlaps too
    (10, 30, 201),  # starts right when the other one ends
    (9, 30, 201),   # ends right when the other one starts
))
async def test_overlapping_bookings(client, setup, hour, minute, expected):
    specialist, service, user = setup
    day = future_day()
    await book(client, user, specialist, service, at(day, 10))

    other = await create_user()
    response = await book(client, other, specialist, service, at(day, hour, minute))

    assert response.status_code == expected


async def test_different_specialists_can_be_booked_at_same_time(client, setup):
    specialist, service, user = setup
    other_specialist, other_service = await create_specialist()
    day = future_day()

    first = await book(client, user, specialist, service, at(day, 10))
    second = await client.post(
        '/bookings', json=booking(other_specialist, other_service, at(day, 10)), headers=auth(user)
    )

    assert (first.status_code, second.status_code) == (201, 201)


@pytest.mark.parametrize(('hour', 'minute'), ((8, 30), (17, 45), (18, 0)))
async def test_outside_working_hours(client, setup, hour, minute):
    specialist, service, user = setup

    response = await book(client, user, specialist, service, at(future_day(), hour, minute))

    assert response.status_code == 400


async def test_day_off(client):
    day = future_day()
    specialist, service = await create_specialist(weekdays=[(day.weekday() + 1) % 7])
    user = await create_user()

    response = await book(client, user, specialist, service, at(day, 10))

    assert response.status_code == 400


async def test_past_and_too_far_dates(client, setup):
    specialist, service, user = setup
    past = (datetime.now(TZ) - timedelta(hours=1)).isoformat()

    assert (await book(client, user, specialist, service, past)).status_code == 400
    far = at(future_day(90), 10)
    assert (await book(client, user, specialist, service, far)).status_code == 400


async def test_naive_datetime_is_rejected(client, setup):
    specialist, service, user = setup
    naive = f'{future_day()}T10:00:00'

    assert (await book(client, user, specialist, service, naive)).status_code == 422


async def test_service_of_another_specialist(client, setup):
    specialist, _, user = setup
    _, foreign_service = await create_specialist()

    response = await book(client, user, specialist, foreign_service, at(future_day(), 10))

    assert response.status_code == 400


async def test_cancelled_slot_can_be_booked_again(client, setup):
    specialist, service, user = setup
    day = future_day()
    first = (await book(client, user, specialist, service, at(day, 10))).json()

    response = await client.post(f'/bookings/{first["id"]}/cancel', headers=auth(user))
    assert response.json()['status'] == 'cancelled'

    other = await create_user()
    response = await book(client, other, specialist, service, at(day, 10))
    assert response.status_code == 201


async def test_cancel_too_late(client, setup):
    specialist, service, user = setup
    soon = datetime.now(TZ) + timedelta(hours=1)
    async with SessionLocal() as db:
        late = Booking(
            user_id=user.id, specialist_id=specialist.id, service_id=service.id,
            starts_at=soon, ends_at=soon + timedelta(minutes=30), price=service.price,
        )
        db.add(late)
        await db.commit()

    assert (await client.post(f'/bookings/{late.id}/cancel', headers=auth(user))).status_code == 400

    # Admin can still cancel
    admin = await create_user(role=Role.ADMIN)
    assert (await client.post(f'/bookings/{late.id}/cancel', headers=auth(admin))).status_code == 200


async def test_clients_see_only_their_bookings(client, setup):
    specialist, service, user = setup
    day = future_day()
    mine = (await book(client, user, specialist, service, at(day, 10))).json()
    other = await create_user()
    await book(client, other, specialist, service, at(day, 11))
    admin = await create_user(role=Role.ADMIN)

    assert len((await client.get('/bookings', headers=auth(user))).json()) == 1
    assert len((await client.get('/bookings', headers=auth(admin))).json()) == 2
    assert (await client.get(f'/bookings/{mine["id"]}', headers=auth(other))).status_code == 404
    assert (await client.post(f'/bookings/{mine["id"]}/cancel', headers=auth(other))).status_code == 404


async def test_list_filters(client, setup):
    specialist, service, user = setup
    admin = await create_user(role=Role.ADMIN)
    day = future_day()
    await book(client, user, specialist, service, at(day, 10))
    await book(client, user, specialist, service, at(future_day(3), 10))

    assert len((await client.get('/bookings', params={'day': str(day)}, headers=auth(admin))).json()) == 1
    assert len((await client.get('/bookings', params={'status': 'cancelled'}, headers=auth(admin))).json()) == 0


async def test_admin_status_changes(client, setup):
    specialist, service, user = setup
    admin = await create_user(role=Role.ADMIN)
    created = (await book(client, user, specialist, service, at(future_day(), 10))).json()
    url = f'/bookings/{created["id"]}/status'

    assert (await client.post(url, json={'status': 'completed'}, headers=auth(user))).status_code == 403
    assert (await client.post(url, json={'status': 'completed'}, headers=auth(admin))).json()['status'] == 'completed'
    assert (await client.post(url, json={'status': 'cancelled'}, headers=auth(admin))).status_code == 400
    assert (await client.post(url, json={'status': 'confirmed'}, headers=auth(admin))).status_code == 400


async def test_same_slot_booked_at_the_same_moment(client, setup):
    """Ten clients send a booking for the same free slot at once. Exactly one should get it."""
    specialist, service, _ = setup
    users = [await create_user() for _ in range(10)]
    payload = booking(specialist, service, at(future_day(), 15))

    responses = await asyncio.gather(*(client.post('/bookings', json=payload, headers=auth(u)) for u in users))

    codes = sorted(r.status_code for r in responses)
    assert codes == [201] + [409] * 9
