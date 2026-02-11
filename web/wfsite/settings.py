"""
Django Settings for WorkFlow Web Frontend

Reads database configuration from the shared etc/global.json
so credentials are not duplicated.
"""

## import buildin pkgs
import os
import json5
from pathlib import Path


## =============================================================
## Path Configuration
## =============================================================

## web/ directory
BASE_DIR = Path(__file__).resolve().parent.parent

## WorkFlow project root (parent of web/)
PROJ_PATH = BASE_DIR.parent

## =============================================================
## Load WorkFlow Global Configuration
## =============================================================

with open(PROJ_PATH / 'etc' / 'global.json') as f:
    WF_CONFIG = json5.load(f)

## =============================================================
## Core Settings
## =============================================================

SECRET_KEY = WF_CONFIG.get('web', {}).get('secret_key', 'change-me-in-production')

DEBUG = WF_CONFIG.get('web', {}).get('debug', True)

ALLOWED_HOSTS = ['*']

## =============================================================
## Application Definition
## =============================================================

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    ## project apps
    'dashboard',
    'accounts',
    'audit',
    'syslog_viewer',
    'workflows',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    ## audit middleware
    'audit.middleware.AuditMiddleware',
]

ROOT_URLCONF = 'wfsite.urls'

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

WSGI_APPLICATION = 'wfsite.wsgi.application'

## =============================================================
## Database
## =============================================================

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'HOST': WF_CONFIG['db']['host'],
        'PORT': WF_CONFIG['db']['port'],
        'USER': WF_CONFIG['db']['username'],
        'PASSWORD': WF_CONFIG['db']['password'],
        'NAME': WF_CONFIG['db']['database'],
        'OPTIONS': {
            'charset': WF_CONFIG['db']['charset'],
        },
    }
}

## =============================================================
## Authentication
## =============================================================

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

## =============================================================
## Internationalization
## =============================================================

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

## =============================================================
## Static Files
## =============================================================

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']

## =============================================================
## Default Primary Key Field Type
## =============================================================

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

## =============================================================
## WorkFlow API Configuration
## =============================================================

WF_API_HOST = WF_CONFIG.get('api', {}).get('host', '127.0.0.1')
WF_API_PORT = WF_CONFIG.get('api', {}).get('port', 5000)
WF_API_BASE_URL = 'http://%s:%s' % (WF_API_HOST, WF_API_PORT)
