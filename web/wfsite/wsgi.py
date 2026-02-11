"""
WSGI Configuration

Exposes the WSGI callable as a module-level variable named ``application``.
"""

## import buildin pkgs
import os

## django setup
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wfsite.settings')

application = get_wsgi_application()
