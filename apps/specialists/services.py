from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Service, Specialist, WorkingHours
from .schemas import WorkingHoursItem


class DuplicateWeekdayError(Exception):
    pass


class UnknownServiceError(Exception):
    pass


async def list_services(db: AsyncSession, *, include_inactive=False, limit=50, offset=0) -> list[Service]:
    query = select(Service).order_by(Service.title).limit(limit).offset(offset)
    if not include_inactive:
        query = query.where(Service.is_active)
    return list(await db.scalars(query))


async def list_specialists(
    db: AsyncSession,
    *,
    service_id: int | None = None,
    include_inactive=False,
    limit=50,
    offset=0,
) -> list[Specialist]:
    query = select(Specialist).order_by(Specialist.full_name).limit(limit).offset(offset)
    if not include_inactive:
        query = query.where(Specialist.is_active)
    if service_id is not None:
        query = query.where(Specialist.services.any(Service.id == service_id))
    return list(await db.scalars(query))


async def set_working_hours(db: AsyncSession, specialist: Specialist, items: list[WorkingHoursItem]) -> Specialist:
    """Replace the whole weekly schedule."""
    weekdays = [item.weekday for item in items]
    if len(weekdays) != len(set(weekdays)):
        raise DuplicateWeekdayError

    specialist.working_hours.clear()
    await db.flush()
    specialist.working_hours.extend(WorkingHours(**item.model_dump()) for item in items)
    await db.commit()
    await db.refresh(specialist)
    return specialist


async def set_services(db: AsyncSession, specialist: Specialist, service_ids: list[int]) -> Specialist:
    services = list(await db.scalars(select(Service).where(Service.id.in_(service_ids))))
    if len(services) != len(set(service_ids)):
        raise UnknownServiceError

    specialist.services = services
    await db.commit()
    await db.refresh(specialist)
    return specialist
