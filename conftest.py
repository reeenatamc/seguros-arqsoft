"""
Configuración de pytest para el proyecto.
"""

import os

import django
from django.conf import settings

# Configurar Django antes de importar modelos
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "seguros.settings")

# Setup Django
django.setup()


def pytest_configure(config):
    """Configuración inicial de pytest."""
    # Configurar Django si aún no está configurado
    if not settings.configured:
        settings.configure(
            DEBUG=True,
            DATABASES={
                "default": {
                    "ENGINE": "django.db.backends.sqlite3",
                    "NAME": ":memory:",
                }
            },
            INSTALLED_APPS=[
                "django.contrib.admin",
                "django.contrib.auth",
                "django.contrib.contenttypes",
                "django.contrib.sessions",
                "django.contrib.messages",
                "django.contrib.staticfiles",
                "app",
            ],
        )
        django.setup()
