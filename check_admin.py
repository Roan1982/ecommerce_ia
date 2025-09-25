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

# Crear un usuario staff
user = User.objects.filter(is_staff=True).first()
if not user:
    user = User.objects.create_user('admin', 'admin@test.com', 'admin123', is_staff=True, is_superuser=True)

# Crear request
rf = RequestFactory()
request = rf.get('/admin/')
request.user = user

# Obtener app_list
app_list = admin_site.get_app_list(request)
print('App list:')
for app in app_list:
    print(f'  {app.get("name", "Unnamed")}: {app.get("app_label", "No label")}')
    if 'models' in app:
        print(f'    Models: {len(app["models"])}')
        for model in app['models'][:3]:  # Mostrar solo los primeros 3
            print(f'      - {model.get("name", "Unnamed model")}')

print(f'\nTotal apps: {len(app_list)}')