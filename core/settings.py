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

TIME_ZONE = 'Asia/Tashkent'
