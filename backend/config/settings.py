"""
Django settings for TheCloeIntegration - Módulo de Integración Tributaria.
"""

from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-change-me-in-production')

DEBUG = os.environ.get('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '*').split(',')

# Application definition
INSTALLED_APPS = [
    # Django core
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third party
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'django_q',
    # Local apps
    'integrations',
    'configurations',
    'reports',
    'sales',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database - SQL Server
DB_ENGINE = os.environ.get('DB_ENGINE', 'mssql')
DATABASES = {
    'default': {
        'ENGINE': DB_ENGINE,
        'NAME': os.environ.get('DB_NAME', 'the_cloe'),
        'HOST': os.environ.get('DB_HOST', 'host.docker.internal'),
        'PORT': os.environ.get('DB_PORT', '1433'),
        'USER': os.environ.get('DB_USER', 'sa'),
        'PASSWORD': os.environ.get('DB_PASSWORD', 'YourStrong!Passw0rd'),
        'OPTIONS': {},
    }
}

# Las OPTIONS de ODBC solo aplican al backend de SQL Server.
if DB_ENGINE == 'mssql':
    DATABASES['default']['OPTIONS']['driver'] = os.environ.get(
        'DB_DRIVER', 'ODBC Driver 18 for SQL Server'
    )
    # Extra connection params (ej. TrustServerCertificate=yes,Encrypt=yes).
    # mssql-django los concatena al connection string de ODBC.
    extra_params = os.environ.get('DB_OPTIONS_EXTRA_PARAMS', '').strip()
    if extra_params:
        DATABASES['default']['OPTIONS']['extra_params'] = ';'.join(
            p.strip() for p in extra_params.split(',') if '=' in p
        )

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'es-cl'
TIME_ZONE = 'America/Santiago'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = '/static/'

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_THROTTLE_RATES': {
        'anon': '10/minute',
        'user': '60/minute',
    },
}

# CORS
CORS_ALLOWED_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:3000').split(',')
CORS_ALLOW_CREDENTIALS = True

# SimpleAPI (SII)
SIMPLEAPI_KEY = os.environ.get('SIMPLEAPI_KEY', '')
SIMPLEAPI_BASE_URL = os.environ.get('SIMPLEAPI_BASE_URL', 'https://api.simpleapi.cl/api/v1')
SIMPLEAPI_TIMEOUT = int(os.environ.get('SIMPLEAPI_TIMEOUT', '30'))

# SimpleFactura (emisión de DTE - FASE 2)
# Credenciales demo de certificación: demo@chilesystems.com / Rv8Il4eV
SIMPLEFACTURA_EMAIL = os.environ.get('SIMPLEFACTURA_EMAIL', '')
SIMPLEFACTURA_PASSWORD = os.environ.get('SIMPLEFACTURA_PASSWORD', '')
SIMPLEFACTURA_BASE_URL = os.environ.get('SIMPLEFACTURA_BASE_URL', 'https://api.simplefactura.cl')
SIMPLEFACTURA_SUCURSAL = os.environ.get('SIMPLEFACTURA_SUCURSAL', 'Casa_Matriz')
SIMPLEFACTURA_MODE = os.environ.get('SIMPLEFACTURA_MODE', 'simulate')  # 'live' | 'simulate'

# django-q2 - cola de emisión de DTE. Broker ORM sobre la BD default (SQL Server).
# NOTA django-q2 >= 1.8: el factory de broker requiere la clave 'orm' con un alias
# de BD válido. El key heredado 'django_redis': None ya NO selecciona ORM: sin 'orm'
# el cluster cae al broker Redis y falla en arranque sin Redis disponible.
Q_CLUSTER = {
    'name': 'DjangORM',
    'workers': 2,
    'recycle': 500,
    'timeout': 120,
    'retry': 180,  # lease/redelivery del cluster; debe ser > timeout
    'compress': True,
    'save_limit': 250,
    'queue_limit': 500,
    'cpu_affinity': 1,
    'label': 'Django Q2',
    'orm': 'default',
    # Reintentos globales: un task fallido se re-entrega cada `retry` (180s) y
    # se abandona tras 3 intentos. En django-q2 1.11 NO existe retry per-task
    # ni max_retries; sin max_attempts (default 0) reintenta para SIEMPRE.
    'max_attempts': 3,
}

# Circuit Breaker
CIRCUIT_BREAKER_FAILURE_THRESHOLD = int(os.environ.get('CIRCUIT_BREAKER_FAILURE_THRESHOLD', '3'))
CIRCUIT_BREAKER_RECOVERY_TIMEOUT = int(os.environ.get('CIRCUIT_BREAKER_RECOVERY_TIMEOUT', '30'))

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': os.environ.get('LOG_LEVEL', 'INFO'),
    },
}
