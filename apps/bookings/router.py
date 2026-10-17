from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from apps.users.dependencies import AdminUser, CurrentUser
from core.db import DBSession

from . import services
from .models import Booking, BookingStatus
from .schemas import BookingCreate, BookingRead, BookingStatusUpdate

router = APIRouter(tags=['bookings'])


async def get_booking_for(db, booking_id: int, user) -> Booking:
    booking = await db.get(Booking, booking_id)
    # Someone else's booking looks the same as a missing one
    if booking is None or (booking.user_id != user.id and not user.is_admin):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Booking not found')
    return booking


@router.post('/bookings', response_model=BookingRead, status_code=status.HTTP_201_CREATED)
async def create_booking(data: BookingCreate, db: DBSession, user: CurrentUser):
    try:
        return await services.create_booking(db, user, data)
    except services.SlotTakenError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from None
    except services.BookingError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from None


@router.get('/bookings', response_model=list[BookingRead])
async def list_bookings(
    db: DBSession,
    user: CurrentUser,
    specialist_id: int | None = None,
    day: date | None = None,
    booking_status: Annotated[BookingStatus | None, Query(alias='status')] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    return await services.list_bookings(
        db, user, specialist_id=specialist_id, day=day, status=booking_status, limit=limit, offset=offset
    )


@router.get('/bookings/{booking_id}', response_model=BookingRead)
async def get_booking(booking_id: int, db: DBSession, user: CurrentUser):
    return await get_booking_for(db, booking_id, user)


@router.post('/bookings/{booking_id}/cancel', response_model=BookingRead)
async def cancel_booking(booking_id: int, db: DBSession, user: CurrentUser):
    booking = await get_booking_for(db, booking_id, user)
    try:
        return await services.cancel_booking(db, booking, user)
    except services.BookingError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from None


@router.post('/bookings/{booking_id}/status', response_model=BookingRead)
async def set_status(booking_id: int, data: BookingStatusUpdate, db: DBSession, admin: AdminUser):
    booking = await get_booking_for(db, booking_id, admin)
    try:
        if data.status == BookingStatus.CANCELLED:
            return await services.cancel_booking(db, booking, admin)
        if data.status == BookingStatus.COMPLETED:
            return await services.complete_booking(db, booking)
    except services.BookingError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from None
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='A booking cannot go back to confirmed')
