#!/usr/bin/env python
"""
Test para verificar que las imágenes se guarden correctamente desde el admin
"""
import os
import sys
import django
from django.conf import settings
from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_project.settings')
django.setup()

from tienda.models import Producto, ProductoImagen
from tienda.forms import ProductoAdminForm
from tienda.admin import ProductoAdmin, admin_site


class TestAdminImageSaving(TestCase):
    def setUp(self):
        # Crear usuario admin
        self.user = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='admin123'
        )

        # Crear request factory
        self.factory = RequestFactory()

    def test_admin_form_saves_images(self):
        """Test que verifica que el admin guarde las imágenes correctamente"""

        # Crear imagen de prueba
        image_content = b'fake image content'
        uploaded_file = SimpleUploadedFile(
            name='test_image.jpg',
            content=image_content,
            content_type='image/jpeg'
        )

        # Crear datos del formulario
        form_data = {
            'nombre': 'Producto de Prueba',
            'descripcion': 'Descripción de prueba',
            'precio': '100.00',
            'categoria': 'electronica',
            'stock': 10,
            'stock_minimo': 5,
            'sku': 'TEST123',
            'estado': 'activo',
            'peso': '1.5',
            'dimensiones': '10x10x10',
        }

        # Crear QueryDict con archivos
        from django.utils.datastructures import MultiValueDict
        files_data = MultiValueDict()
        files_data.appendlist('imagenes_files', uploaded_file)

        # Crear producto vacío para simular edición
        producto = Producto.objects.create(
            nombre='Temporal',
            precio=50.00,
            categoria='temporal'
        )

        # Crear formulario con la instancia existente
        form = ProductoAdminForm(data=form_data, files=files_data, instance=producto)

        # Verificar que el formulario sea válido
        self.assertTrue(form.is_valid(), f"Errores del formulario: {form.errors}")

        # Crear request mock
        request = self.factory.post('/admin/tienda/producto/add/')
        request.user = self.user

        # Crear instancia del admin
        admin_instance = ProductoAdmin(Producto, admin_site)

        # Llamar a save_model como lo haría el admin
        admin_instance.save_model(request, producto, form, change=True)

        # Verificar que el producto se actualizó
        producto.refresh_from_db()
        self.assertEqual(producto.nombre, 'Producto de Prueba')

        # Verificar que se creó la imagen
        imagenes = ProductoImagen.objects.filter(producto=producto)
        self.assertEqual(imagenes.count(), 1)

        imagen = imagenes.first()
        self.assertEqual(imagen.imagen_nombre, 'test_image.jpg')
        self.assertTrue(imagen.es_principal)  # Debería ser la primera imagen

        print("✅ Test completado: Las imágenes se guardan correctamente desde el admin")


if __name__ == '__main__':
    # Ejecutar el test
    import unittest
    unittest.main()