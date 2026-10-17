from fastapi import APIRouter, Depends, HTTPException, status

from core import settings
from core.db import DBSession
from core.rate_limit import RateLimiter
from core.security import create_access_token, create_refresh_token, decode_token

from . import services
from .dependencies import CurrentUser
from .models import User
from .schemas import LoginRequest, RefreshRequest, TokenPair, UserCreate, UserRead, UserUpdate

router = APIRouter(prefix='/auth', tags=['auth'])

auth_limiter = RateLimiter(times=settings.AUTH_RATE_LIMIT, seconds=60)


def make_tokens(user_id: int) -> TokenPair:
    return TokenPair(access=create_access_token(user_id), refresh=create_refresh_token(user_id))


@router.post(
    '/register',
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(auth_limiter)],
)
async def register(data: UserCreate, db: DBSession):
    try:
        return await services.create_user(db, data)
    except services.EmailTakenError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Email is already registered') from None


@router.post('/login', response_model=TokenPair, dependencies=[Depends(auth_limiter)])
async def login(data: LoginRequest, db: DBSession):
    user = await services.authenticate(db, data.email, data.password)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Wrong email or password')
    return make_tokens(user.id)


@router.post('/refresh', response_model=TokenPair)
async def refresh(data: RefreshRequest, db: DBSession):
    user_id = decode_token(data.refresh, 'refresh')
    user = await db.get(User, user_id) if user_id else None
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid refresh token')
    return make_tokens(user.id)


@router.get('/me', response_model=UserRead)
async def me(user: CurrentUser):
    return user


@router.patch('/me', response_model=UserRead)
async def update_me(data: UserUpdate, user: CurrentUser, db: DBSession):
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    await db.commit()
    await db.refresh(user)
    return user
