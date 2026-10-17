from datetime import datetime, time

from apps.common.tests.factories import TZ, at, auth, create_specialist, create_user, future_day


async def get_slots(client, specialist, service_id, day):
    return await client.get(f'/specialists/{specialist.id}/slots', params={'service_id': service_id, 'date': str(day)})


def times(response) -> list[str]:
    return [datetime.fromisoformat(s).astimezone(TZ).strftime('%H:%M') for s in response.json()['slots']]


async def test_free_day(client):
    specialist, service = await create_specialist(duration_minutes=45, start=time(9), end=time(11))

    response = await get_slots(client, specialist, service.id, future_day())

    assert response.status_code == 200
    assert times(response) == ['09:00', '09:15', '09:30', '09:45', '10:00', '10:15']


async def test_booked_time_is_excluded(client):
    specialist, service = await create_specialist(duration_minutes=45, start=time(9), end=time(12))
    user = await create_user()
    day = future_day()
    await client.post(
        '/bookings',
        json={'specialist_id': specialist.id, 'service_id': service.id, 'starts_at': at(day, 10)},
        headers=auth(user),
    )

    response = await get_slots(client, specialist, service.id, day)

    # 10:00-10:45 is taken: 9:15 still fits (ends at 10:00), 9:30 doesn't
    assert times(response) == ['09:00', '09:15', '10:45', '11:00', '11:15']


async def test_day_off_has_no_slots(client):
    day = future_day()
    specialist, service = await create_specialist(weekdays=[(day.weekday() + 1) % 7])

    response = await get_slots(client, specialist, service.id, day)

    assert times(response) == []


async def test_unknown_service(client):
    specialist, _ = await create_specialist()

    response = await get_slots(client, specialist, 999, future_day())

    assert response.status_code == 404
