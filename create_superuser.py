#!/usr/bin/env python
"""Script para crear superusuario en Docker."""
import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "seguros.settings")
django.setup()

from django.contrib.auth import get_user_model  # noqa: E402

User = get_user_model()

username = "admin"
email = "admin@utpl.edu.ec"
password = "admin123"

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username, email, password)
    print(f"✓ Superusuario creado: {username}")
    print(f"  Email: {email}")
    print(f"  Password: {password}")
else:
    print(f"✓ Superusuario '{username}' ya existe")
