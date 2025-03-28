'''
Django settings for tms project.

Generated by 'django-admin startproject' using Django 5.0.2.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.0/ref/settings/
'''

from pathlib import Path
from celery.schedules import crontab
# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-#3n%fp!%=gpgtc_wex&s=o&@mss02swzs=7avd)4-mtq%l)g!1'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'staff_user',
    'equipment',
    'finance',
    'autoslug',
    'pro',
    'vacation',
    
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'tms.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'tms.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        # 'NAME': BASE_DIR / 'db.sqlite3',  # This will create a SQLite database file in your project directory
        'NAME':'tamc_db',
        'USER':'root',
        'PASSWORD': '1',
        'HOST': '127.0.0.1',
        'PORT':'3306',
    #     'OPTIONS': {
    #         'ssl': {'ca': None} 
    #     }
        
     }
}




# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Africa/Dar_es_Salaam'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = '/static/' 
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_ROOT = BASE_DIR / 'media'  
MEDIA_URL = '/media/'

 

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# AbstractUser 
# AUTH_USER_MODEL = 'staff_user.MyUser'


# Session 
SESSION_EXPIRE_SECONDS = 60  # Sessions expire after 1 hour of inactivity
SESSION_EXPIRE_AT_BROWSER_CLOSE = False  # Sessions expire after SESSION_COOKIE_AGE seconds of inactivity


# Add these settings at the bottom of your settings.py file

# Email settings
import os

# Email settings


# settings.py

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

# Gmail account credentials (replace with your own)
EMAIL_HOST_USER = 'allyidrisaally@gmail.com'
EMAIL_HOST_PASSWORD = 'ureflivjkyecijwu'


# settings.py


# Celery Configuration
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'

# Optional: Configure timezone
CELERY_TIMEZONE = 'Africa/Dar_es_Salaam'

# Configure Celery to use the Django settings module
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'send-weekly-program-email': {
        'task': 'pro.tasks.scheduled_weekly_report',
        'schedule': crontab(hour=15, minute=3, day_of_week='Wednesday'),  # Adjust timing as needed
    },
}

# settings.py

# Celery settings
CELERY_BROKER_URL = 'redis://192.168.137.143:6379/0'
CELERY_RESULT_BACKEND = 'redis://192.168.137.143:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_TIMEZONE = 'Africa/Dar_es_Salaam'

# Optional settings for retries and time limits
CELERY_TASK_TIME_LIMIT = 300  # 5 minutes time limit for each task
CELERY_TASK_SOFT_TIME_LIMIT = 240  # 4 minutes for soft time limit
CELERY_RESULT_EXPIRES = 3600  # Results expire after 1 hour
