from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from apps.specialists.models import Service, Specialist
from apps.users.models import User
from core import settings

from .models import Booking, BookingStatus
from .schemas import BookingCreate

TZ = ZoneInfo(settings.TIME_ZONE)


class BookingError(Exception):
    """Business rule violation. The message is safe to show to the client."""


class SlotTakenError(BookingError):
    pass


def now() -> datetime:
    return datetime.now(TZ)


async def get_bookable(db: AsyncSession, specialist_id: int, service_id: int) -> tuple[Specialist, Service]:
    specialist = await db.get(Specialist, specialist_id)
    if specialist is None or not specialist.is_active:
        raise BookingError('Specialist not found')
    service = next((s for s in specialist.services if s.id == service_id and s.is_active), None)
    if service is None:
        raise BookingError('This specialist does not provide this service')
    return specialist, service


def fits_working_hours(specialist: Specialist, starts_at: datetime, ends_at: datetime) -> bool:
    start, end = starts_at.astimezone(TZ), ends_at.astimezone(TZ)
    if start.date() != end.date():
        return False
    hours = next((h for h in specialist.working_hours if h.weekday == start.weekday()), None)
    return hours is not None and hours.start_time <= start.time() and end.time() <= hours.end_time


async def get_free_slots(db: AsyncSession, specialist_id: int, service_id: int, day: date) -> list[datetime]:
    """Start times on the given day when the service fits into working hours and doesn't clash with a booking."""
    specialist, service = await get_bookable(db, specialist_id, service_id)

    hours = next((h for h in specialist.working_hours if h.weekday == day.weekday()), None)
    if hours is None or day > now().date() + timedelta(days=settings.BOOKING_WINDOW_DAYS):
        return []

    day_start = datetime.combine(day, hours.start_time, TZ)
    day_end = datetime.combine(day, hours.end_time, TZ)
    busy = list(await db.execute(
        select(Booking.starts_at, Booking.ends_at).where(
            Booking.specialist_id == specialist_id,
            Booking.status != BookingStatus.CANCELLED,
            Booking.starts_at < day_end,
            Booking.ends_at > day_start,
        )
    ))

    duration = timedelta(minutes=service.duration_minutes)
    step = timedelta(minutes=settings.SLOT_STEP_MINUTES)
    current_time = now()

    slots = []
    start = day_start
    while start + duration <= day_end:
        end = start + duration
        if start > current_time and not any(start < b_end and end > b_start for b_start, b_end in busy):
            slots.append(start)
        start += step
    return slots


async def create_booking(db: AsyncSession, user: User, data: BookingCreate) -> Booking:
    specialist, service = await get_bookable(db, data.specialist_id, data.service_id)

    starts_at = data.starts_at
    ends_at = starts_at + timedelta(minutes=service.duration_minutes)

    if starts_at <= now():
        raise BookingError('Booking time must be in the future')
    if starts_at > now() + timedelta(days=settings.BOOKING_WINDOW_DAYS):
        raise BookingError(f'You can book at most {settings.BOOKING_WINDOW_DAYS} days ahead')
    if not fits_working_hours(specialist, starts_at, ends_at):
        raise BookingError('The specialist does not work at this time')

    booking = Booking(
        user_id=user.id,
        specialist_id=specialist.id,
        service_id=service.id,
        starts_at=starts_at,
        ends_at=ends_at,
        price=service.price,
        comment=data.comment,
    )
    db.add(booking)
    try:
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        # No "check, then insert" here: two requests could both pass the check.
        # The exclusion constraint makes the database the single judge.
        if 'no_overlapping_bookings' in str(e.orig):
            raise SlotTakenError('This time is already booked') from None
        raise
    await db.refresh(booking)
    return booking


async def cancel_booking(db: AsyncSession, booking: Booking, by: User) -> Booking:
    if booking.status != BookingStatus.CONFIRMED:
        raise BookingError('Only confirmed bookings can be cancelled')
    deadline = booking.starts_at - timedelta(hours=settings.CANCEL_DEADLINE_HOURS)
    if not by.is_admin and now() > deadline:
        raise BookingError(f'Bookings can be cancelled at least {settings.CANCEL_DEADLINE_HOURS} hours in advance')

    booking.status = BookingStatus.CANCELLED
    await db.commit()
    await db.refresh(booking)
    return booking


async def complete_booking(db: AsyncSession, booking: Booking) -> Booking:
    if booking.status != BookingStatus.CONFIRMED:
        raise BookingError('Only confirmed bookings can be completed')
    booking.status = BookingStatus.COMPLETED
    await db.commit()
    await db.refresh(booking)
    return booking


async def list_bookings(
    db: AsyncSession,
    user: User,
    *,
    specialist_id: int | None = None,
    day: date | None = None,
    status: BookingStatus | None = None,
    limit=50,
    offset=0,
) -> list[Booking]:
    query = select(Booking).order_by(Booking.starts_at).limit(limit).offset(offset)
    # Clients see only their own bookings, admins see everything
    if not user.is_admin:
        query = query.where(Booking.user_id == user.id)
    if specialist_id is not None:
        query = query.where(Booking.specialist_id == specialist_id)
    if status is not None:
        query = query.where(Booking.status == status)
    if day is not None:
        day_start = datetime.combine(day, datetime.min.time(), TZ)
        query = query.where(Booking.starts_at >= day_start, Booking.starts_at < day_start + timedelta(days=1))
    return list(await db.scalars(query))
