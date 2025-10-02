#!/usr/bin/env python3
"""
Test script to debug image upload issue in ProductoAdminForm
"""
import os
import sys
import django
from django.conf import settings
from django.test import TestCase, RequestFactory
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import QueryDict

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_project.settings')
django.setup()

from tienda.forms import ProductoAdminForm
from tienda.models import Producto

def test_image_upload():
    """Test if images are being processed correctly in the form"""

    # Create a test product instance
    producto = Producto.objects.create(
        nombre="Test Product",
        descripcion="Test Description",
        precio=100.00,
        sku="TEST123-UNIQUE",
        stock=10
    )

    # Create a test image file
    image_content = b'fake image content'
    uploaded_file = SimpleUploadedFile(
        "test_image.jpg",
        image_content,
        content_type="image/jpeg"
    )

    # Create form data
    form_data = {
        'nombre': 'Test Product Updated',
        'descripcion': 'Test Description Updated',
        'precio': '150.00',
        'sku': 'TEST123-UPDATED',
        'stock': '15',
        'stock_minimo': '5',
        'peso': '1.5',
        'categoria': '1',  # Assuming category ID 1 exists
        'estado': 'activo',
    }

    # Create files data - this simulates what should come from the request
    # We need to create a QueryDict to properly simulate file uploads
    files_querydict = QueryDict('', mutable=True)
    files_querydict.update({'imagenes_files': uploaded_file})

    print("Testing form with image upload...")
    print(f"Form data: {form_data}")
    print(f"Files data keys: {list(files_querydict.keys())}")

    # Create the form
    form = ProductoAdminForm(data=form_data, files=files_querydict, instance=producto)

    print(f"Form is valid: {form.is_valid()}")

    if not form.is_valid():
        print(f"Form errors: {form.errors}")
        print(f"Non-field errors: {form.non_field_errors()}")

        # Check if there are file-specific errors
        if 'imagenes_files' in form.errors:
            print(f"Image files errors: {form.errors['imagenes_files']}")

    else:
        print("Form is valid, attempting to save...")

        try:
            saved_product = form.save()
            print(f"Product saved successfully: {saved_product.nombre}")

            # Check if images were created
            image_count = saved_product.imagenes.count()
            print(f"Number of images associated with product: {image_count}")

            if image_count > 0:
                print("Images were saved successfully!")
                for img in saved_product.imagenes.all():
                    print(f"Image: {img.imagen_nombre}, Size: {len(img.imagen_blob)} bytes, Type: {img.imagen_tipo_mime}")
            else:
                print("No images were saved!")

        except Exception as e:
            print(f"Error saving form: {e}")
            import traceback
            traceback.print_exc()

    # Clean up
    producto.delete()

if __name__ == '__main__':
    test_image_upload()