"""Create an admin user: python -m apps.users.cli admin@example.com"""

import asyncio
import getpass
import sys

from core.db import SessionLocal

from . import services
from .models import Role
from .schemas import UserCreate


async def create_admin(email: str, password: str):
    async with SessionLocal() as db:
        user = await services.create_user(db, UserCreate(email=email, password=password), role=Role.ADMIN)
        print(f'Admin {user.email} created')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit('Usage: python -m apps.users.cli <email>')
    asyncio.run(create_admin(sys.argv[1], getpass.getpass('Password: ')))
