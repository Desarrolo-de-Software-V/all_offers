"""
Django settings for alloffers_project project.
"""

from pathlib import Path
import os
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-your-secret-key-change-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'False') == 'True'

# Hosts permitidos
# 🔴 SOLO PARA DESBLOQUEAR EL 400:
#    Aceptar todos los hosts temporalmente.
#    Cuando confirmemos que todo funciona, lo cambiamos a una lista específica.
ALLOWED_HOSTS = ['*']

# Logging para debug - siempre mostrar en producción para diagnosticar
print(f"🔵 ALLOWED_HOSTS configurado: {ALLOWED_HOSTS}")
print(f"🔵 DEBUG: {DEBUG}")


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core',
    'crispy_forms',
    'crispy_bootstrap5',
]

# Agregar Cloudinary solo si está configurado (producción)
# IMPORTANTE: cloudinary_storage debe ir ANTES de django.contrib.staticfiles
CLOUDINARY_URL_ENV = os.environ.get('CLOUDINARY_URL')
if CLOUDINARY_URL_ENV:
    INSTALLED_APPS.insert(0, 'cloudinary_storage')  # Debe ir primero
    INSTALLED_APPS.append('cloudinary')
    print("✅ Cloudinary configurado correctamente")
else:
    print("⚠️ Cloudinary no configurado - usando almacenamiento local")

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Para servir archivos estáticos en producción
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Configuración para proxies (Railway)
USE_TZ = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

ROOT_URLCONF = 'alloffers_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'core' / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',
                'core.context_processors.google_maps_api_key',
            ],
        },
    },
]

WSGI_APPLICATION = 'alloffers_project.wsgi.application'


# Database
# Usar PostgreSQL si DATABASE_URL está disponible (Railway), sino usar SQLite para desarrollo local
import dj_database_url

# Obtener DATABASE_URL de las variables de entorno
DATABASE_URL = os.environ.get('DATABASE_URL')

# Debug: Log qué base de datos se está usando (solo en desarrollo)
if DEBUG:
    if DATABASE_URL:
        print(f"🔵 Usando PostgreSQL: {DATABASE_URL[:50]}...")
    else:
        print("🟡 Usando SQLite (desarrollo local)")

if DATABASE_URL:
    # Usar PostgreSQL en producción (Railway)
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
    # Forzar que use PostgreSQL
    if 'sqlite' in DATABASE_URL.lower():
        # Si por alguna razón DATABASE_URL apunta a SQLite, usar SQLite local
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': BASE_DIR / 'db.sqlite3',
            }
        }
else:
    # Usar SQLite para desarrollo local
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
LANGUAGE_CODE = 'es-es'

TIME_ZONE = 'America/Panama'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATICFILES_DIRS = [
    BASE_DIR / 'core' / 'static',
]
STATIC_ROOT = BASE_DIR / 'staticfiles'

# WhiteNoise configuration for static files
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files
# Usar Cloudinary en producción si está configurado, sino usar sistema local
if CLOUDINARY_URL_ENV:
    # Configuración de Cloudinary
    # django-cloudinary-storage puede leer directamente de CLOUDINARY_URL
    # Pero también podemos configurar manualmente si se prefiere
    cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME')
    api_key = os.environ.get('CLOUDINARY_API_KEY')
    api_secret = os.environ.get('CLOUDINARY_API_SECRET')
    
    if cloud_name and api_key and api_secret:
        # Si hay variables separadas, usarlas
        CLOUDINARY_STORAGE = {
            'CLOUD_NAME': cloud_name,
            'API_KEY': api_key,
            'API_SECRET': api_secret,
        }
        print(f"✅ Cloudinary configurado con variables separadas - Cloud: {cloud_name}")
    else:
        # Si solo hay CLOUDINARY_URL, django-cloudinary-storage la leerá automáticamente
        print("✅ Cloudinary configurado con CLOUDINARY_URL")
    
    DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'
    MEDIA_URL = '/media/'
    MEDIA_ROOT = ''  # No se usa en Cloudinary
else:
    # Sistema local para desarrollo
    MEDIA_URL = '/media/'
    MEDIA_ROOT = BASE_DIR / 'media'
    print("⚠️ Usando almacenamiento local para archivos media")

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom User Model
AUTH_USER_MODEL = 'core.User'

# Login URLs
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = 'home'

# Crispy Forms
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# Google Maps API Key
# Puedes configurarla directamente aquí o usar una variable de entorno
# Para usar variable de entorno: export GOOGLE_MAPS_API_KEY='tu-api-key' (Linux/Mac)
# o set GOOGLE_MAPS_API_KEY=tu-api-key (Windows)
GOOGLE_MAPS_API_KEY = os.environ.get('GOOGLE_MAPS_API_KEY', '')
