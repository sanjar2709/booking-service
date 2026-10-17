from datetime import date, datetime, time, timedelta
from decimal import Decimal
from itertools import count
from zoneinfo import ZoneInfo

from apps.specialists.models import Service, Specialist, WorkingHours
from apps.users.models import Role, User
from core import settings
from core.db import SessionLocal
from core.security import create_access_token, hash_password

TZ = ZoneInfo(settings.TIME_ZONE)
PASSWORD = 'Str0ngPass!42'

_numbers = count(1)


async def create_user(role: Role = Role.CLIENT, **kwargs) -> User:
    async with SessionLocal() as db:
        user = User(
            email=kwargs.pop('email', f'user{next(_numbers)}@example.com'),
            hashed_password=hash_password(PASSWORD),
            role=role,
            **kwargs,
        )
        db.add(user)
        await db.commit()
        return user


def auth(user: User) -> dict:
    return {'Authorization': f'Bearer {create_access_token(user.id)}'}


async def create_specialist(
    duration_minutes=30,
    price='80000.00',
    start=time(9),
    end=time(18),
    weekdays=range(7),
) -> tuple[Specialist, Service]:
    """A specialist with one service who works every day from 9 to 18 by default."""
    async with SessionLocal() as db:
        service = Service(title=f'Service {next(_numbers)}', duration_minutes=duration_minutes, price=Decimal(price))
        specialist = Specialist(
            full_name=f'Specialist {next(_numbers)}',
            services=[service],
            working_hours=[WorkingHours(weekday=d, start_time=start, end_time=end) for d in weekdays],
        )
        db.add(specialist)
        await db.commit()
        return specialist, service


def future_day(days=2) -> date:
    return date.today() + timedelta(days=days)


def at(day: date, hour: int, minute: int = 0) -> str:
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=TZ).isoformat()
