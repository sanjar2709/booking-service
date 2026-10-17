from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from apps.users.dependencies import AdminUser
from core.db import DBSession

from . import services
from .models import Service, Specialist
from .schemas import (
    ServiceCreate,
    ServiceRead,
    ServiceUpdate,
    SpecialistCreate,
    SpecialistRead,
    SpecialistServicesUpdate,
    SpecialistUpdate,
    WorkingHoursItem,
)

router = APIRouter(tags=['specialists'])

Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]


async def get_or_404(db, model, obj_id: int):
    obj = await db.get(model, obj_id)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'{model.__name__} not found')
    return obj


# Services

@router.get('/services', response_model=list[ServiceRead])
async def list_services(db: DBSession, limit: Limit = 50, offset: Offset = 0):
    return await services.list_services(db, limit=limit, offset=offset)


@router.get('/services/{service_id}', response_model=ServiceRead)
async def get_service(service_id: int, db: DBSession):
    return await get_or_404(db, Service, service_id)


@router.post('/services', response_model=ServiceRead, status_code=status.HTTP_201_CREATED)
async def create_service(data: ServiceCreate, db: DBSession, admin: AdminUser):
    service = Service(**data.model_dump())
    db.add(service)
    await db.commit()
    await db.refresh(service)
    return service


@router.patch('/services/{service_id}', response_model=ServiceRead)
async def update_service(service_id: int, data: ServiceUpdate, db: DBSession, admin: AdminUser):
    service = await get_or_404(db, Service, service_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(service, field, value)
    await db.commit()
    await db.refresh(service)
    return service


# Specialists

@router.get('/specialists', response_model=list[SpecialistRead])
async def list_specialists(db: DBSession, service_id: int | None = None, limit: Limit = 50, offset: Offset = 0):
    return await services.list_specialists(db, service_id=service_id, limit=limit, offset=offset)


@router.get('/specialists/{specialist_id}', response_model=SpecialistRead)
async def get_specialist(specialist_id: int, db: DBSession):
    return await get_or_404(db, Specialist, specialist_id)


@router.post('/specialists', response_model=SpecialistRead, status_code=status.HTTP_201_CREATED)
async def create_specialist(data: SpecialistCreate, db: DBSession, admin: AdminUser):
    specialist = Specialist(**data.model_dump(), services=[], working_hours=[])
    db.add(specialist)
    await db.commit()
    await db.refresh(specialist)
    return specialist


@router.patch('/specialists/{specialist_id}', response_model=SpecialistRead)
async def update_specialist(specialist_id: int, data: SpecialistUpdate, db: DBSession, admin: AdminUser):
    specialist = await get_or_404(db, Specialist, specialist_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(specialist, field, value)
    await db.commit()
    await db.refresh(specialist)
    return specialist


@router.put('/specialists/{specialist_id}/working-hours', response_model=SpecialistRead)
async def set_working_hours(specialist_id: int, items: list[WorkingHoursItem], db: DBSession, admin: AdminUser):
    specialist = await get_or_404(db, Specialist, specialist_id)
    try:
        return await services.set_working_hours(db, specialist, items)
    except services.DuplicateWeekdayError:
        detail = 'Each weekday can appear only once'
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail) from None


@router.put('/specialists/{specialist_id}/services', response_model=SpecialistRead)
async def set_services(specialist_id: int, data: SpecialistServicesUpdate, db: DBSession, admin: AdminUser):
    specialist = await get_or_404(db, Specialist, specialist_id)
    try:
        return await services.set_services(db, specialist, data.service_ids)
    except services.UnknownServiceError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Some services do not exist') from None
