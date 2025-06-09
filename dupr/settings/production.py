import os
from .base import * # Import your base settings
from dotenv import load_dotenv

# Load environment variables from .env file
# Assumes .env is in the project root, adjust the path if necessary
# dotenv_path = os.path.join(BASE_DIR, '..', '.env')
# load_dotenv(dotenv_path)
load_dotenv()

# --- SECURITY SETTINGS ---

DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'

SECRET_KEY = os.environ.get('SECRET_KEY')

# Get allowed hosts from environment variable, split by comma
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')

# --- DATABASE SETTINGS ---
# Assumes you have a 'DATABASES' dictionary in your base.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME'),
        'USER': os.environ.get('DB_USER'),
        'PASSWORD': os.environ.get('DB_PASSWORD'),
        'HOST': os.environ.get('DB_HOST'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}

# --- STATIC AND MEDIA FILE CONFIGURATION ---
# These paths are relative to your BASE_DIR. Assuming BASE_DIR is in
# 'dupr/settings', '../' goes up to the 'dupr/' directory, and a
# second '../' goes up to the project root '/home/matthijs/wagtaildupr/'.
# Adjust if your BASE_DIR definition is different. A common definition is
# BASE_DIR = Path(__file__).resolve().parent.parent

# The absolute path to the directory where collectstatic will gather static files.
STATIC_ROOT = os.path.join(BASE_DIR, '..', 'static_collected')

# The URL that static files will be served from.
# This should already be in your base.py, but ensure it's here.
STATIC_URL = '/static/'

# The absolute path to the directory where user-uploaded media files will be stored.
MEDIA_ROOT = os.path.join(BASE_DIR, '..', 'media')

# The URL that media files will be served from.
MEDIA_URL = '/media/'




# --- CADDY / REVERSE PROXY SETTINGS ---
# These settings ensure Django works correctly behind a reverse proxy like Caddy
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True

# --- LOGGING (Optional but Recommended) ---
# Example: Log errors to a file in production
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, '..', 'logs', 'django-errors.log'),
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'ERROR',
            'propagate': True,
        },
    },
}

# Create a 'logs' directory if it doesn't exist
os.makedirs(os.path.join(BASE_DIR, '..', 'logs'), exist_ok=True)
