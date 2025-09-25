#!/usr/bin/env python
"""
Script para crear usuario administrador
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_project.settings')
django.setup()

from django.contrib.auth.models import User

def crear_admin():
    if User.objects.filter(username='admin').exists():
        print("Usuario admin ya existe")
        return

    User.objects.create_superuser(
        username='admin',
        email='admin@example.com',
        password='admin123'
    )
    print("✓ Usuario admin creado exitosamente")
    print("Usuario: admin")
    print("Contraseña: admin123")

if __name__ == '__main__':
    crear_admin()