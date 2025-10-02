import os
import sys
import django

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure Django settings FIRST
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_project.settings')
django.setup()

# Now import Django modules
from django.contrib.auth.models import User
from django.test import Client
from django.core.files.uploadedfile import SimpleUploadedFile
from tienda.models import Producto

def test_admin_form_post():
    """Test simulating a browser POST to the admin form"""

    # Create a test user with admin permissions
    try:
        admin_user = User.objects.get(username='admin')
    except User.DoesNotExist:
        admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='admin123'
        )

    # Create a test product
    producto = Producto.objects.create(
        nombre="Test Product",
        descripcion="Test Description",
        precio=100.00,
        sku="TEST123-ADMIN",
        stock=10,
        stock_minimo=5,
        peso=1.5,
        categoria="Test Category",
        estado='activo'
    )

    # Create test client
    client = Client()

    # Log in as admin
    login_success = client.login(username='admin', password='admin123')
    print(f"Admin login successful: {login_success}")

    # Create test image file
    image_content = b'fake image content for admin test'
    uploaded_file = SimpleUploadedFile(
        "admin_test_image.jpg",
        image_content,
        content_type="image/jpeg"
    )

    # Make POST request to admin change form
    url = f'/admin/tienda/producto/{producto.id}/change/'

    # Prepare form data exactly as the admin form would send it
    form_data = {
        'nombre': 'Test Product Updated Admin',
        'descripcion': 'Test Description Updated Admin',
        'precio': '200.00',
        'sku': 'TEST123-ADMIN-UPDATED',
        'stock': '20',
        'stock_minimo': '10',
        'peso': '2.0',
        'categoria': 'Updated Category',
        'estado': 'activo',
        'csrfmiddlewaretoken': 'dummy_token',  # This would be provided by Django
    }

    # Create files data - simulate what happens when files are selected
    # Instead of using QueryDict, let's try sending files directly
    files_data = {
        'imagenes_files': uploaded_file
    }

    print("Sending POST request to admin form...")
    print(f"Form data: {form_data}")
    print(f"Files: {list(files_data.keys())}")

    # Try a different approach - let's check what the admin form actually expects
    # First, let's see what happens if we don't send any files
    print("\n--- Testing without files first ---")
    response_no_files = client.post(url, {'csrfmiddlewaretoken': 'dummy_token'}, follow=True)
    print(f"Response without files - Status: {response_no_files.status_code}")

    # Now try with files
    print("\n--- Testing with files ---")
    response = client.post(url, data=form_data, files=files_data, follow=True)

    print(f"Response status: {response.status_code}")
    print(f"Response redirect: {response.redirect_chain}")

    if response.status_code == 200:
        print("Form submission successful")

        # Check if product was updated
        updated_product = Producto.objects.get(id=producto.id)
        print(f"Updated product name: {updated_product.nombre}")
        print(f"Updated product SKU: {updated_product.sku}")

        # Check if images were saved
        image_count = updated_product.imagenes.count()
        print(f"Number of images: {image_count}")

        if image_count > 0:
            print("SUCCESS: Images were saved via admin form!")
            for img in updated_product.imagenes.all():
                print(f"Image: {img.imagen_nombre}, Size: {len(img.imagen_blob)} bytes")
        else:
            print("FAILURE: No images were saved via admin form")

    else:
        print(f"Form submission failed with status {response.status_code}")
        print("Response content:")
        print(response.content.decode()[:1000])  # First 1000 chars

    # Clean up
    producto.delete()
    try:
        admin_user.delete()
    except:
        pass

if __name__ == '__main__':
    test_admin_form_post()