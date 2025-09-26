#!/usr/bin/env python
"""
Script para probar la funcionalidad de gestión de usuarios en el admin de Django
"""
import os
import sys
import django
import re
from django.conf import settings

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_project.settings')
django.setup()

from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

def test_user_management():
    """Prueba la funcionalidad de gestión de usuarios"""
    print("=== PRUEBA DE GESTIÓN DE USUARIOS ===\n")

    # Crear cliente para simular requests
    client = Client()

    # 1. Verificar que podemos acceder al admin
    print("1. Verificando acceso al admin...")
    response = client.get('/admin/')
    print(f"   Status code: {response.status_code}")
    if response.status_code == 302:  # Redirect to login
        print("   ✓ Redirección a login correcta")
    else:
        print("   ✗ Error en redirección")

    # 2. Login como admin
    print("\n2. Iniciando sesión como admin...")
    login_data = {
        'username': 'admin',
        'password': 'admin123'  # Asumiendo que es la contraseña
    }
    response = client.post('/admin/login/', login_data, follow=True)
    print(f"   Status code: {response.status_code}")
    if 'admin' in str(response.content):
        print("   ✓ Login exitoso")
    else:
        print("   ✗ Error en login - verificar contraseña")

    # 3. Acceder a la lista de usuarios
    print("\n3. Accediendo a la lista de usuarios...")
    response = client.get('/admin/auth/user/')
    print(f"   Status code: {response.status_code}")
    if response.status_code == 200:
        print("   ✓ Acceso a lista de usuarios exitoso")
        if b'admin' in response.content:
            print("   ✓ Usuario admin visible en la lista")
        else:
            print("   ✗ Usuario admin no encontrado en la lista")
    else:
        print("   ✗ Error accediendo a lista de usuarios")

    # 4. Verificar que podemos acceder al formulario de creación
    print("\n4. Verificando acceso al formulario de creación...")
    response = client.get('/admin/auth/user/add/')
    print(f"   Status code: {response.status_code}")
    if response.status_code == 200:
        print("   ✓ Acceso al formulario de creación exitoso")
        if b'Add user' in response.content or b'Agregar usuario' in response.content:
            print("   ✓ Formulario de creación visible")
        else:
            print("   ✗ Formulario de creación no encontrado")
    else:
        print("   ✗ Error accediendo al formulario de creación")

    # 5. Crear un usuario de prueba usando el formulario del admin
    print("\n5. Creando usuario de prueba usando formulario del admin...")
    user_data = {
        'username': 'testuser3',
        'password1': 'testpass123',
        'password2': 'testpass123',
        # Solo estos campos son válidos en el formulario de agregar
    }

    response = client.post('/admin/auth/user/add/', user_data, follow=True)
    print(f"   Status code: {response.status_code}")
    if response.status_code == 200:
        # Verificar si el usuario fue creado
        try:
            test_user = User.objects.get(username='testuser3')
            print("   ✓ Usuario de prueba creado exitosamente")
            print(f"   ✓ Usuario: {test_user.username}, Email: {test_user.email}, Staff: {test_user.is_staff}, Active: {test_user.is_active}")
        except User.DoesNotExist:
            print("   ✗ Error: Usuario de prueba no fue creado")
            print(f"   Contenido de respuesta: {response.content[:1000].decode('utf-8', errors='ignore')}")
    else:
        print("   ✗ Error creando usuario")
        print(f"   Contenido de respuesta: {response.content[:1000].decode('utf-8', errors='ignore')}")

    # 6. Verificar edición de usuario
    print("\n6. Verificando edición de usuario...")
    try:
        test_user = User.objects.get(username='testuser3')
        response = client.get(f'/admin/auth/user/{test_user.id}/change/')
        print(f"   Status code: {response.status_code}")
        if response.status_code == 200:
            print("   ✓ Acceso al formulario de edición exitoso")

            # Extraer el token CSRF del formulario
            content = response.content.decode('utf-8')
            import re
            csrf_match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', content)
            csrf_token = csrf_match.group(1) if csrf_match else ''

            if not csrf_token:
                print("   ✗ No se pudo encontrar el token CSRF")
            else:
                print("   ✓ Token CSRF encontrado")

                # Editar el usuario con token CSRF
                edit_data = {
                    'csrfmiddlewaretoken': csrf_token,
                    'username': 'testuser3',
                    'email': 'testedited@example.com',
                    'first_name': 'Test',
                    'last_name': 'User Edited',
                    'is_active': 'on',
                    'is_staff': 'on',
                    'is_superuser': 'off',
                    # Campos de contraseña - usar la opción de no cambiar
                    'password': '',  # No cambiar contraseña
                    # Campos de grupos y permisos como arrays vacíos
                    'groups': [],
                    'user_permissions': [],
                    # Campos adicionales que Django podría esperar
                    'date_joined_0': '2024-01-01',  # Fecha
                    'date_joined_1': '00:00:00',    # Hora
                    'last_login_0': '',  # Fecha último login
                    'last_login_1': '',  # Hora último login
                }

                response = client.post(f'/admin/auth/user/{test_user.id}/change/', edit_data, follow=True)
                print(f"   Status code edición: {response.status_code}")
                if response.status_code == 200:
                    test_user.refresh_from_db()
                    print(f"   Email después de edición: '{test_user.email}'")
                    print(f"   First name después de edición: '{test_user.first_name}'")
                    print(f"   Last name después de edición: '{test_user.last_name}'")
                    if test_user.email == 'testedited@example.com':
                        print("   ✓ Usuario editado exitosamente")
                    else:
                        print("   ✗ Error: Email no fue actualizado")
                else:
                    print("   ✗ Error editando usuario")
                    print(f"   Contenido de respuesta: {response.content[:1000].decode('utf-8', errors='ignore')}")
        else:
            print("   ✗ Error accediendo al formulario de edición")
    except User.DoesNotExist:
        print("   ✗ Usuario de prueba no existe para editar")

    # 7. Verificar desactivación de usuario
    print("\n7. Verificar desactivación de usuario...")
    try:
        test_user = User.objects.get(username='testuser3')
        # Obtener el formulario nuevamente para un token CSRF fresco
        response = client.get(f'/admin/auth/user/{test_user.id}/change/')
        content = response.content.decode('utf-8')
        csrf_match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', content)
        csrf_token = csrf_match.group(1) if csrf_match else ''

        # Usar exactamente los mismos datos que funcionaron en el script separado
        edit_data = {
            'csrfmiddlewaretoken': csrf_token,
            'username': 'testuser3',
            'email': 'testedited@example.com',
            'first_name': 'Test',
            'last_name': 'User Edited',
            'is_active': 'False',  # Desactivar
            'is_staff': 'on',
            'is_superuser': 'off',
            'groups': [],
            'user_permissions': [],
            'date_joined_0': '2024-01-01',
            'date_joined_1': '00:00:00',
            'last_login_0': '',
            'last_login_1': '',
        }

        response = client.post(f'/admin/auth/user/{test_user.id}/change/', edit_data, follow=True)
        print(f"   Status code desactivación: {response.status_code}")
        content = response.content.decode('utf-8', errors='ignore')
        if response.status_code == 200:
            test_user.refresh_from_db()
            print(f"   Is active después de desactivación: {test_user.is_active}")
            if not test_user.is_active:
                print("   ✓ Usuario desactivado exitosamente")
            else:
                print("   ✗ Error: Usuario no fue desactivado")
                # Verificar si hay errores en la respuesta
                if 'error' in content.lower() or 'alert-danger' in content:
                    print("   Posibles errores en la respuesta del formulario")
                    # Buscar mensajes de error específicos
                    import re
                    error_matches = re.findall(r'<ul class="errorlist">.*?</ul>', content, re.DOTALL)
                    if error_matches:
                        print("   Errores encontrados:")
                        for error in error_matches[:3]:  # Mostrar máximo 3 errores
                            print(f"     {error}")
        else:
            print("   ✗ Error desactivando usuario")
            print(f"   Contenido de respuesta: {content[:1000]}")
    except User.DoesNotExist:
        print("   ✗ Usuario de prueba no existe para desactivar")

    # 8. Limpiar usuario de prueba
    print("\n8. Limpiando usuario de prueba...")
    try:
        test_user = User.objects.get(username='testuser3')
        test_user.delete()
        print("   ✓ Usuario de prueba eliminado")
    except User.DoesNotExist:
        print("   ✓ Usuario de prueba ya no existe")

    print("\n=== PRUEBA COMPLETADA ===")

if __name__ == '__main__':
    test_user_management()