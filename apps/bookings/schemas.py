from datetime import datetime
from decimal import Decimal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from .models import BookingStatus


class BookingCreate(BaseModel):
    specialist_id: int
    service_id: int
    starts_at: AwareDatetime = Field(description='With timezone, e.g. 2026-10-20T10:00:00+05:00')
    comment: str = Field(default='', max_length=500)


class BookingSpecialist(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str


class BookingService(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    duration_minutes: int


class BookingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    specialist: BookingSpecialist
    service: BookingService
    starts_at: datetime
    ends_at: datetime
    status: BookingStatus
    price: Decimal
    comment: str
    created_at: datetime


class BookingStatusUpdate(BaseModel):
    status: BookingStatus
