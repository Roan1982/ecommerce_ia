import os
import django
from django.conf import settings

# Configurar Django ANTES de cualquier import
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_project.settings')
django.setup()

from django.test import RequestFactory, TestCase
from django.contrib.auth.models import User
from django.contrib.admin.sites import AdminSite
from django.contrib.messages.storage import default_storage
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.auth.middleware import AuthenticationMiddleware
from django.middleware.csrf import CsrfViewMiddleware, get_token
from django.template.loader import get_template
from django.template import Context
from tienda.admin import ProductoAdmin
from tienda.models import Producto
from tienda.forms import ProductoAdminForm
from django.contrib.admin.sites import AdminSite
from django.utils.datastructures import MultiValueDict
from django.core.files.uploadedfile import SimpleUploadedFile
from io import BytesIO
from PIL import Image
import tempfile

def create_test_image():
    """Crear una imagen de prueba como SimpleUploadedFile"""
    img = Image.new('RGB', (100, 100), color='red')
    img_io = BytesIO()
    img.save(img_io, format='JPEG')
    img_io.seek(0)
    return SimpleUploadedFile(
        name='test_image.jpg',
        content=img_io.getvalue(),
        content_type='image/jpeg'
    )

def test_admin_form_with_errors():
    """Test que simula errores de validación en el admin"""

    # Crear usuario admin
    try:
        admin_user = User.objects.get(username='admin')
    except User.DoesNotExist:
        admin_user = User.objects.create_superuser('admin', 'admin@test.com', 'admin123')

    # Crear producto existente para probar SKU duplicado
    Producto.objects.create(
        nombre='Producto Existente',
        precio=50.00,
        categoria='test',
        sku='SKU-DUPLICADO'
    )

    # Crear RequestFactory
    factory = RequestFactory()

    # Crear imagen de prueba
    test_image = create_test_image()

    # Crear datos del formulario CON SKU DUPLICADO
    form_data = {
        'nombre': 'Producto con SKU Duplicado',
        'precio': '100.00',
        'categoria': 'prueba',
        'descripcion': 'Descripción de prueba',
        'stock': '10',
        'stock_minimo': '5',
        'sku': 'SKU-DUPLICADO',  # SKU duplicado
        'peso': '1.5',
        'dimensiones': '10x20x5',
        'estado': 'activo',
    }

    # Crear archivos usando MultiValueDict
    files = MultiValueDict({
        'imagenes_files': [test_image],
    })

    print("=== Probando formulario con errores de validación ===")

    # Probar el formulario directamente
    form = ProductoAdminForm(data=form_data, files=files)
    print(f"Formulario válido: {form.is_valid()}")
    if not form.is_valid():
        print("Errores del formulario:")
        for field, errors in form.errors.items():
            print(f"  {field}: {errors}")
        print("Errores no asociados a campos:")
        for error in form.non_field_errors():
            print(f"  Non-field: {error}")

        # Simular cómo se mostrarían en el admin
        print("\n=== Simulando display en admin ===")
        print("Mensaje genérico que aparecería:")
        error_count = len(form.errors)
        if error_count == 1:
            print("Please correct the error below.")
        else:
            print(f"Please correct the errors below. ({error_count})")

        print("\nErrores no asociados a campos (adminform.form.non_field_errors):")
        for error in form.non_field_errors():
            print(f"  {error}")

        print("\nErrores de campo que deberían aparecer en cada fieldset:")
        for field_name, field_errors in form.errors.items():
            if field_name != '__all__':  # No es un error no asociado a campo
                print(f"  Campo '{field_name}': {field_errors}")

    # Limpiar
    Producto.objects.filter(sku='SKU-DUPLICADO').delete()

def test_admin_template_rendering():
    """Test que verifica cómo se renderiza el template del admin con errores"""

    # Crear usuario admin
    try:
        admin_user = User.objects.get(username='admin')
    except User.DoesNotExist:
        admin_user = User.objects.create_superuser('admin', 'admin@test.com', 'admin123')

    # Crear producto existente para probar SKU duplicado
    Producto.objects.create(
        nombre='Producto Existente',
        precio=50.00,
        categoria='test',
        sku='SKU-DUPLICADO'
    )

    # Crear RequestFactory
    factory = RequestFactory()

    # Crear imagen de prueba
    test_image = create_test_image()

    # Crear datos del formulario CON SKU DUPLICADO
    form_data = {
        'nombre': 'Producto con SKU Duplicado',
        'precio': '100.00',
        'categoria': 'prueba',
        'descripcion': 'Descripción de prueba',
        'stock': '10',
        'stock_minimo': '5',
        'sku': 'SKU-DUPLICADO',  # SKU duplicado
        'peso': '1.5',
        'dimensiones': '10x20x5',
        'estado': 'activo',
    }

    # Crear archivos usando MultiValueDict
    files = MultiValueDict({
        'imagenes_files': [test_image],
    })

    # Crear request POST simulando el admin
    request = factory.post('/admin/tienda/producto/add/', data=form_data, files=files)
    request.user = admin_user
    request.session = {}
    request._messages = default_storage(request)

    # Agregar middleware
    middleware = SessionMiddleware(lambda x: None)
    middleware.process_request(request)
    request.session.save()

    auth_middleware = AuthenticationMiddleware(lambda x: None)
    auth_middleware.process_request(request)

    csrf_middleware = CsrfViewMiddleware(lambda x: None)
    csrf_middleware.process_request(request)
    get_token(request)

    # Crear instancia del admin
    admin_site = AdminSite()
    producto_admin = ProductoAdmin(Producto, admin_site)

    # Crear el formulario con errores
    form = ProductoAdminForm(data=form_data, files=files)

    # Verificar que el formulario tiene errores
    assert not form.is_valid()
    print("Formulario tiene errores como esperado")

    # Simular el contexto que tendría el admin
    from django.contrib.admin.helpers import AdminForm
    admin_form = AdminForm(form, producto_admin.get_fieldsets(request), producto_admin.get_prepopulated_fields(request))

    context = {
        'adminform': admin_form,
        'original': None,
        'is_popup': False,
        'to_field': None,
        'save_on_top': False,
        'errors': form.errors,  # Esto es lo que activa el mensaje genérico
        'opts': Producto._meta,
        'app_label': 'tienda',
        'has_file_field': True,
        'form_url': None,
        'add': True,
        'change': False,
        'has_view_permission': True,
        'has_add_permission': True,
        'has_change_permission': True,
        'has_delete_permission': True,
        'has_editable_inline_admin_formsets': False,
        'inline_admin_formsets': [],
        'media': form.media,
        'request': request,
    }

    # Intentar renderizar el template
    try:
        template = get_template('admin/tienda/producto_change_form.html')
        rendered = template.render(context)
        print("Template renderizado exitosamente")

        # Buscar el mensaje de error genérico
        if 'Please correct the error' in rendered or 'Por favor, corrija' in rendered:
            print("✓ Mensaje genérico de error encontrado en el HTML renderizado")
        else:
            print("✗ Mensaje genérico de error NO encontrado en el HTML renderizado")

        # Buscar errores específicos
        if 'Ya existe Producto con este Sku' in rendered:
            print("✓ Error específico del SKU encontrado en el HTML renderizado")
        else:
            print("✗ Error específico del SKU NO encontrado en el HTML renderizado")

        # Mostrar una porción del HTML renderizado para debug
        print("\n=== Porción del HTML renderizado ===")
        # Buscar la sección de errores
        start = rendered.find('<p class="errornote">')
        if start != -1:
            end = rendered.find('</p>', start) + 4
            print(rendered[start:end])
        else:
            print("No se encontró la sección de errornote")

    except Exception as e:
        print(f"Error al renderizar template: {e}")
        import traceback
        traceback.print_exc()

    # Limpiar
    Producto.objects.filter(sku='SKU-DUPLICADO').delete()

if __name__ == '__main__':
    test_admin_template_rendering()