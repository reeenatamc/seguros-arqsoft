"""Configuración de pytest para Django."""

import os

import django

# Configurar Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "seguros.settings")
django.setup()
