# booking-service

[![CI](https://github.com/sanjar2709/booking-service/actions/workflows/ci.yml/badge.svg)](https://github.com/sanjar2709/booking-service/actions/workflows/ci.yml)

Appointment booking API for places like a barbershop or a small clinic. Specialists have a weekly schedule,
services have a duration and a price, and clients pick a free time and book it.

Built with FastAPI and async SQLAlchemy. The part I cared about most is making sure one specialist
can never end up with two bookings at the same time, even when requests arrive at the same moment.

## Features

- Email login with JWT access and refresh tokens, two roles: `admin` and `client`
- Admin manages services, specialists, which services each specialist provides, and weekly working hours
- `GET /specialists/{id}/slots` returns free start times for a service on a given day
- Clients book, see and cancel their own bookings (no later than 2 hours before the start)
- Every error comes back in one format, login and register are rate limited

Stack: Python 3.12, FastAPI, SQLAlchemy 2 (async, asyncpg), Alembic, Pydantic 2, PostgreSQL 17, pytest, Docker, GitHub Actions.

## No double bookings

The usual way is "check if the time is free, then insert". That breaks when two requests run the check
at the same moment: both see a free slot and both insert.

Here the database decides. The `bookings` table has an exclusion constraint:

```sql
EXCLUDE USING gist (
    specialist_id WITH =,
    tstzrange(starts_at, ends_at, '[)') WITH &&
) WHERE (status <> 'cancelled')
```

It means: for the same specialist, two active bookings can't have overlapping time ranges.
`[)` leaves the end out, so 10:00-10:30 and 10:30-11:00 are fine together. Cancelled bookings
don't count, so a cancelled time can be booked again.

The app just inserts and, if PostgreSQL rejects the row, returns `409 Conflict`
(`apps/bookings/services.py`). The test `test_same_slot_booked_at_the_same_moment` sends ten requests
for one slot at once and expects exactly one `201` and nine `409`.

The constraint needs the `btree_gist` extension, which the migration turns on.

## Running it

```bash
cp .env.example .env    # fill in SECRET_KEY and database credentials
```

With Docker:

```bash
docker compose up -d
docker compose exec web python -m apps.users.cli admin@example.com
```

API docs: http://localhost:8001/api/docs

Without Docker for the app (database still in Docker):

```bash
docker compose up -d db
python -m venv venv && source venv/bin/activate
pip install -r requirements/dev.txt
alembic upgrade head
python -m apps.users.cli admin@example.com
uvicorn main:app --reload --port 8001
```

## API

| Method | Endpoint | Who |
|---|---|---|
| POST | `/api/v1/auth/register`, `/login`, `/refresh` | anyone |
| GET, PATCH | `/api/v1/auth/me` | user |
| GET | `/api/v1/services`, `/api/v1/specialists` | anyone |
| POST, PATCH | `/api/v1/services`, `/api/v1/specialists` | admin |
| PUT | `/api/v1/specialists/{id}/working-hours` | admin |
| PUT | `/api/v1/specialists/{id}/services` | admin |
| GET | `/api/v1/specialists/{id}/slots?service_id=1&date=2026-10-20` | anyone |
| POST, GET | `/api/v1/bookings` | client (admin sees all) |
| POST | `/api/v1/bookings/{id}/cancel` | owner or admin |
| POST | `/api/v1/bookings/{id}/status` | admin |

Booking a slot:

```bash
curl -X POST localhost:8001/api/v1/bookings \
  -H 'Authorization: Bearer <access token>' \
  -H 'Content-Type: application/json' \
  -d '{"specialist_id": 1, "service_id": 1, "starts_at": "2026-10-20T10:00:00+05:00"}'
```

`starts_at` must include a timezone. The end time is calculated from the service duration.

Errors look like this:

```json
{"error": {"code": "conflict", "message": "This time is already booked", "details": null}}
```

## Tests

```bash
pytest --cov
```

50 tests, 97% coverage. They run against a separate `<DB_NAME>_test` database that is built
with the real Alembic migrations, so the migrations are tested too. CI also runs `alembic check`
to catch model changes without a migration.

## Project layout

```
apps/
  common/        shared model mixin, test factories
  users/         user model, JWT auth, roles, create-admin command
  specialists/   services, specialists, working hours
  bookings/      bookings, free slots, the no-overlap rule
core/            settings, database, security, error handlers, rate limiter
migrations/      Alembic
requirements/    base.txt, dev.txt, prod.txt
main.py
```

## License

MIT
