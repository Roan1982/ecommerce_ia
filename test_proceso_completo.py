#!/usr/bin/env python
"""
Test para simular el proceso completo de subida de imágenes desde el navegador
"""
import os
import sys
import django
from django.conf import settings
from django.test import TestCase, RequestFactory
from django.core.files.uploadedfile import SimpleUploadedFile
from io import BytesIO
from PIL import Image

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_project.settings')
django.setup()

from tienda.forms import ProductoAdminForm
from tienda.models import Producto, ProductoImagen
from tienda.views import admin_editar_producto


def create_test_image(name="test.jpg", size=(100, 100), color='red'):
    """Crear una imagen de prueba"""
    img = Image.new('RGB', size, color=color)
    img_io = BytesIO()
    img.save(img_io, format='JPEG')
    img_io.seek(0)
    return SimpleUploadedFile(name, img_io.getvalue(), content_type="image/jpeg")


def test_complete_image_upload_process():
    """Test que simula el proceso completo de subida de imágenes"""
    print("=== TEST: Proceso completo de subida de imágenes ===")

    # Paso 1: Crear producto existente
    producto = Producto.objects.create(
        nombre='Producto para test completo',
        descripcion='Descripción de prueba',
        precio=100.00,
        categoria='Prueba',
        stock=10,
        estado='activo'
    )

    print(f"Producto creado: {producto.nombre} (ID: {producto.id})")

    # Paso 2: Simular envío de formulario con nuevas imágenes
    # Crear archivos como si vinieran del navegador
    imagen1 = create_test_image("imagen_desde_navegador_1.jpg", color='blue')
    imagen2 = create_test_image("imagen_desde_navegador_2.jpg", color='green')

    # Datos del formulario POST
    post_data = {
        'nombre': 'Producto actualizado',
        'descripcion': 'Descripción actualizada',
        'precio': '150.00',
        'categoria': 'Electrónica',
        'stock': '20',
        'stock_minimo': '5',
        'estado': 'activo',
        'images_to_delete': '',  # No eliminar imágenes
        'existing_images_order': '',  # No reordenar
    }

    # Archivos del formulario
    files_data = {
        'imagenes_files': [imagen1, imagen2]
    }

    print(f"Archivos a subir: {[f.name for f in files_data['imagenes_files']]}")

    # Paso 3: Crear formulario con datos POST y archivos
    form = ProductoAdminForm(data=post_data, files=files_data, instance=producto)

    print(f"Formulario válido: {form.is_valid()}")
    if not form.is_valid():
        print(f"Errores del formulario: {form.errors}")
        return False

    # Paso 4: Guardar el formulario (simulando el submit)
    try:
        producto_actualizado = form.save()
        print(f"Producto guardado: {producto_actualizado.nombre}")

        # Verificar imágenes guardadas
        imagenes = producto_actualizado.imagenes.all().order_by('orden')
        print(f"Total imágenes después del guardado: {imagenes.count()}")

        for i, img in enumerate(imagenes):
            print(f"  Imagen {i+1}: {img.imagen_nombre} (ID: {img.id}, tamaño: {len(img.imagen_blob)} bytes, principal: {img.es_principal})")

        # Verificar que se guardaron 2 imágenes nuevas
        if imagenes.count() == 2:
            print("✅ Test PASADO: Imágenes guardadas correctamente")
            return True
        else:
            print(f"❌ Test FALLADO: Se esperaban 2 imágenes, se encontraron {imagenes.count()}")
            return False

    except Exception as e:
        print(f"❌ Error al guardar: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_view_level_simulation():
    """Test que simula el proceso a nivel de vista"""
    print("\n=== TEST: Simulación a nivel de vista ===")

    # Crear producto
    producto = Producto.objects.create(
        nombre='Producto para vista test',
        descripcion='Descripción',
        precio=100.00,
        categoria='Test',
        stock=5,
        estado='activo'
    )

    # Simular request POST con archivos
    factory = RequestFactory()
    imagen = create_test_image("vista_test.jpg")

    # Crear POST data como vendría del navegador
    post_data = {
        'nombre': producto.nombre,
        'descripcion': producto.descripcion,
        'precio': str(producto.precio),
        'categoria': producto.categoria,
        'stock': str(producto.stock),
        'estado': producto.estado,
        'csrfmiddlewaretoken': 'fake_token',  # Simular token CSRF
    }

    files_data = {
        'imagenes_files': imagen
    }

    # Crear request POST
    request = factory.post(f'/admin/producto/editar/{producto.id}/', data=post_data, files=files_data)
    request.user = type('User', (), {'is_authenticated': True, 'is_staff': True})()  # Mock user

    print("Simulando llamada a la vista admin_editar_producto...")

    try:
        # Llamar a la vista directamente
        from tienda.views import admin_editar_producto
        response = admin_editar_producto(request, producto_id=producto.id)

        print(f"Respuesta de la vista: {response.status_code}")

        # Verificar si se guardaron imágenes
        imagenes_despues = producto.imagenes.count()
        print(f"Imágenes después de la vista: {imagenes_despues}")

        if imagenes_despues > 0:
            print("✅ Test PASADO: Vista procesó imágenes correctamente")
            return True
        else:
            print("❌ Test FALLADO: Vista no procesó imágenes")
            return False

    except Exception as e:
        print(f"❌ Error en vista: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    print("Iniciando tests del proceso completo de subida de imágenes...")

    # Limpiar datos de prueba
    ProductoImagen.objects.all().delete()
    Producto.objects.all().delete()

    # Ejecutar tests
    test1_passed = test_complete_image_upload_process()
    test2_passed = test_view_level_simulation()

    print("\n=== RESULTADOS ===")
    print(f"Test 1 (Proceso completo): {'PASADO' if test1_passed else 'FALLADO'}")
    print(f"Test 2 (Nivel de vista): {'PASADO' if test2_passed else 'FALLADO'}")

    if test1_passed and test2_passed:
        print("🎉 Todos los tests pasaron correctamente!")
        print("\n💡 Si los tests pasan pero el navegador no funciona, el problema está en:")
        print("   1. JavaScript no agrega archivos al input correctamente")
        print("   2. Formulario no se envía con enctype='multipart/form-data'")
        print("   3. Navegador cachea JavaScript/CSS antiguos")
        sys.exit(0)
    else:
        print("💥 Algunos tests fallaron")
        sys.exit(1)