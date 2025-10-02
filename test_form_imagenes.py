#!/usr/bin/env python
"""
Test script para verificar que el formulario de producto guarda imágenes correctamente.
"""
import os
import sys
import django
from django.conf import settings
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from io import BytesIO
from PIL import Image

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_project.settings')
django.setup()

from tienda.forms import ProductoAdminForm
from tienda.models import Producto, ProductoImagen


def create_test_image():
    """Crear una imagen de prueba en memoria"""
    img = Image.new('RGB', (100, 100), color='red')
    img_io = BytesIO()
    img.save(img_io, format='JPEG')
    img_io.seek(0)
    return img_io


def test_form_with_images():
    """Test que verifica que el formulario guarda imágenes correctamente"""
    print("=== TEST: Formulario con imágenes ===")

    # Crear imagen de prueba
    img_io = create_test_image()
    uploaded_file = SimpleUploadedFile(
        "test_image.jpg",
        img_io.getvalue(),
        content_type="image/jpeg"
    )

    # Crear datos del formulario
    form_data = {
        'nombre': 'Producto de prueba',
        'descripcion': 'Descripción de prueba',
        'precio': '100.00',
        'categoria': 'Electrónica',
        'stock': '10',
        'stock_minimo': '1',
        'estado': 'activo',
    }

    # Crear archivos del formulario
    form_files = {
        'imagenes_files': [uploaded_file]
    }

    # Crear formulario
    form = ProductoAdminForm(data=form_data, files=form_files)

    print(f"Formulario válido: {form.is_valid()}")
    if not form.is_valid():
        print(f"Errores del formulario: {form.errors}")
        return False

    # Guardar el formulario
    try:
        producto = form.save()
        print(f"Producto guardado: {producto.nombre} (ID: {producto.id})")

        # Verificar que se creó la imagen
        imagenes = producto.imagenes.all()
        print(f"Número de imágenes guardadas: {imagenes.count()}")

        if imagenes.count() > 0:
            img = imagenes.first()
            print(f"Imagen guardada: {img.imagen_nombre} (ID: {img.id})")
            print(f"Tamaño del blob: {len(img.imagen_blob)} bytes")
            print("✅ Test PASADO: Imagen guardada correctamente")
            return True
        else:
            print("❌ Test FALLADO: No se guardaron imágenes")
            return False

    except Exception as e:
        print(f"❌ Error al guardar: {e}")
        return False


def test_form_editing_existing_product():
    """Test que verifica la edición de un producto existente con imágenes"""
    print("\n=== TEST: Edición de producto existente ===")

    # Crear producto con imagen existente
    producto = Producto.objects.create(
        nombre='Producto existente',
        descripcion='Descripción existente',
        precio=50.00,
        categoria='Prueba',
        stock=5,
        estado='activo'
    )

    # Crear imagen existente
    img_io = create_test_image()
    imagen_existente = ProductoImagen.objects.create(
        producto=producto,
        imagen_blob=img_io.getvalue(),
        imagen_nombre='imagen_existente.jpg',
        imagen_tipo_mime='image/jpeg',
        orden=0,
        es_principal=True
    )

    print(f"Producto creado: {producto.nombre} (ID: {producto.id})")
    print(f"Imagen existente: {imagen_existente.imagen_nombre} (ID: {imagen_existente.id})")

    # Crear nueva imagen para subir
    img_io2 = create_test_image()
    uploaded_file = SimpleUploadedFile(
        "nueva_imagen.jpg",
        img_io2.getvalue(),
        content_type="image/jpeg"
    )

    # Datos del formulario para edición
    form_data = {
        'nombre': 'Producto editado',
        'descripcion': 'Descripción editada',
        'precio': '75.00',
        'categoria': 'Electrónica',
        'stock': '15',
        'stock_minimo': '2',
        'estado': 'activo',
    }

    form_files = {
        'imagenes_files': [uploaded_file]
    }

    # Crear formulario con instancia existente
    form = ProductoAdminForm(data=form_data, files=form_files, instance=producto)

    print(f"Formulario válido: {form.is_valid()}")
    if not form.is_valid():
        print(f"Errores del formulario: {form.errors}")
        return False

    # Guardar cambios
    try:
        producto_editado = form.save()
        print(f"Producto editado: {producto_editado.nombre}")

        # Verificar imágenes
        imagenes = producto_editado.imagenes.all().order_by('orden')
        print(f"Total imágenes después de edición: {imagenes.count()}")

        for i, img in enumerate(imagenes):
            print(f"  Imagen {i+1}: {img.imagen_nombre} (orden: {img.orden}, principal: {img.es_principal})")

        if imagenes.count() == 2:
            print("✅ Test PASADO: Producto editado correctamente con nueva imagen")
            return True
        else:
            print("❌ Test FALLADO: Número incorrecto de imágenes")
            return False

    except Exception as e:
        print(f"❌ Error al editar: {e}")
        return False


if __name__ == '__main__':
    print("Iniciando tests del formulario de productos...")

    # Limpiar datos de prueba previos
    ProductoImagen.objects.all().delete()
    Producto.objects.all().delete()

    # Ejecutar tests
    test1_passed = test_form_with_images()
    test2_passed = test_form_editing_existing_product()

    print("\n=== RESULTADOS ===")
    print(f"Test 1 (Nuevo producto): {'PASADO' if test1_passed else 'FALLADO'}")
    print(f"Test 2 (Edición producto): {'PASADO' if test2_passed else 'FALLADO'}")

    if test1_passed and test2_passed:
        print("🎉 Todos los tests pasaron correctamente!")
        sys.exit(0)
    else:
        print("💥 Algunos tests fallaron")
        sys.exit(1)