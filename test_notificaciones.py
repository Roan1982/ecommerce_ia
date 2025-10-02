#!/usr/bin/env python3
"""
Script de prueba para verificar el funcionamiento de las notificaciones
en el carrito de compras y que no interfieran con el layout del navbar.
"""

import os
import sys
import django
from django.conf import settings

# Configurar Django antes de cualquier import
if not settings.configured:
    settings.configure(
        DEBUG=True,
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': 'db.sqlite3',
            }
        },
        INSTALLED_APPS=[
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'django.contrib.sessions',
            'django.contrib.messages',
            'tienda',
        ],
        SECRET_KEY='test-secret-key',
        USE_TZ=True,
    )

django.setup()

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse

from tienda.models import Producto, Carrito, CarritoProducto

def test_notificaciones_carrito():
    """Prueba las notificaciones del carrito"""
    print("🧪 Probando notificaciones del carrito...")

    # Crear cliente de prueba
    client = Client()

    # Crear usuario de prueba con nombre único
    import time
    username = f'testuser_{int(time.time())}'
    user = User.objects.create_user(
        username=username,
        email=f'{username}@example.com',
        password='testpass123'
    )

    # Crear producto de prueba
    producto = Producto.objects.create(
        nombre='Producto de Prueba',
        descripcion='Descripción de prueba',
        precio=100.00,
        stock=10,
        categoria='Electrónica',
        sku='TEST001'
    )

    # Iniciar sesión
    client.login(username='testuser', password='testpass123')

    # Agregar producto al carrito
    response = client.post(reverse('agregar_al_carrito', args=[producto.id]), {
        'cantidad': 1
    })

    print(f"✅ Producto agregado al carrito: {response.status_code}")

    # Ver carrito
    response = client.get(reverse('ver_carrito'))
    print(f"✅ Página del carrito cargada: {response.status_code}")

    # Verificar que contiene la función showMessage
    if 'showMessage' in response.content.decode():
        print("✅ Función showMessage encontrada en el template")
    else:
        print("❌ Función showMessage NO encontrada en el template")

    # Verificar que usa Bootstrap Toast
    if 'bootstrap.Toast' in response.content.decode():
        print("✅ Bootstrap Toast implementado correctamente")
    else:
        print("❌ Bootstrap Toast NO implementado")

    # Verificar que no usa alert() nativo
    if 'alert(' in response.content.decode():
        print("❌ Todavía usa alert() nativo - debe ser removido")
    else:
        print("✅ No usa alert() nativo")

    # Probar actualización de cantidad (simular AJAX)
    carrito = Carrito.objects.get(usuario=user)
    item = CarritoProducto.objects.get(carrito=carrito, producto=producto)

    response = client.post(
        reverse('actualizar_carrito', args=[item.id]),
        {'cantidad': 2},
        HTTP_X_REQUESTED_WITH='XMLHttpRequest'
    )

    print(f"✅ Actualización de cantidad (AJAX): {response.status_code}")

    # Verificar respuesta JSON
    import json
    try:
        data = json.loads(response.content.decode())
        if data.get('success'):
            print("✅ Respuesta AJAX correcta")
        else:
            print(f"❌ Error en respuesta AJAX: {data}")
    except:
        print("❌ Respuesta AJAX no es JSON válido")

    # Limpiar datos de prueba
    user.delete()
    producto.delete()

    print("🎉 Prueba completada!")

if __name__ == '__main__':
    test_notificaciones_carrito()