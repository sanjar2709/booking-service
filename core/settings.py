import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / '.env')

PROJECT_NAME = 'Booking Service'
VERSION = '1.0.0'

DEBUG = os.getenv('DEBUG') == '1'

SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    raise RuntimeError('SECRET_KEY environment variable is not set')

ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS', '').split()

ACCESS_TOKEN_LIFETIME_MINUTES = int(os.getenv('ACCESS_TOKEN_LIFETIME_MINUTES', 30))
REFRESH_TOKEN_LIFETIME_DAYS = int(os.getenv('REFRESH_TOKEN_LIFETIME_DAYS', 7))

TIME_ZONE = 'Asia/Tashkent'

# Bookings

BOOKING_WINDOW_DAYS = int(os.getenv('BOOKING_WINDOW_DAYS', 60))
CANCEL_DEADLINE_HOURS = int(os.getenv('CANCEL_DEADLINE_HOURS', 2))
SLOT_STEP_MINUTES = int(os.getenv('SLOT_STEP_MINUTES', 15))

# Database

DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')

DATABASE_URL = f'postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
DB_ECHO = os.getenv('DB_ECHO') == '1'
