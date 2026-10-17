from datetime import time
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ServiceBase(BaseModel):
    title: str = Field(max_length=150)
    description: str = ''
    duration_minutes: int = Field(gt=0, le=600)
    price: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    is_active: bool = True


class ServiceCreate(ServiceBase):
    pass


class ServiceUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=150)
    description: str | None = None
    duration_minutes: int | None = Field(default=None, gt=0, le=600)
    price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    is_active: bool | None = None


class ServiceRead(ServiceBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


class WorkingHoursItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    weekday: int = Field(ge=0, le=6, description='0 = Monday, 6 = Sunday')
    start_time: time
    end_time: time

    @model_validator(mode='after')
    def check_times(self):
        if self.start_time >= self.end_time:
            raise ValueError('start_time must be before end_time')
        return self


class SpecialistBase(BaseModel):
    full_name: str = Field(max_length=150)
    position: str = Field(default='', max_length=100)
    bio: str = ''
    is_active: bool = True


class SpecialistCreate(SpecialistBase):
    pass


class SpecialistUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=150)
    position: str | None = Field(default=None, max_length=100)
    bio: str | None = None
    is_active: bool | None = None


class SpecialistRead(SpecialistBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    services: list[ServiceRead]
    working_hours: list[WorkingHoursItem]


class SpecialistServicesUpdate(BaseModel):
    service_ids: list[int]
