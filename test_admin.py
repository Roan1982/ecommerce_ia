#!/usr/bin/env python
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_project.settings')
django.setup()

from tienda.admin import admin_site
from django.test import RequestFactory
from django.contrib.auth.models import User

# Crear una request simulada
factory = RequestFactory()
request = factory.get('/admin/auth/')
request.user = User.objects.filter(is_superuser=True).first()

print(f"Usuario: {request.user}")
print(f"Es superusuario: {request.user.is_superuser}")
print(f"Es staff: {request.user.is_staff}")

# Obtener la lista de apps
app_list = admin_site.get_app_list(request)
print('\nAplicaciones encontradas:')
for app in app_list:
    print(f'  - {app.get("name", "Sin nombre")} ({app.get("app_label", "Sin label")})')

# Verificar el contexto
context = admin_site.each_context(request)
print(f'\nCurrent app: {context.get("current_app")}')
print(f'Title: {context.get("title")}')