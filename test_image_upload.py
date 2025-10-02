import os
import django
from django.conf import settings

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_project.settings')
django.setup()

from tienda.models import Producto
from tienda.forms import ProductoAdminForm
from django.http import QueryDict
from django.core.files.uploadedfile import SimpleUploadedFile

# Obtener un producto existente
producto = Producto.objects.first()
print(f'Producto: {producto.nombre}')

# Simular datos POST
data = QueryDict('', mutable=True)
data.update({
    'nombre': producto.nombre,
    'precio': str(producto.precio),
    'categoria': producto.categoria,
    'stock': str(producto.stock),
    'stock_minimo': str(producto.stock_minimo),
    'estado': producto.estado,
    'csrfmiddlewaretoken': 'fake-token'
})

# Crear un archivo de imagen simulado
image_content = b'fake image content'
uploaded_file = SimpleUploadedFile('test_image.jpg', image_content, content_type='image/jpeg')

# Simular request.FILES con archivos (de manera correcta)
files = QueryDict('', mutable=True)
# Para simular múltiples archivos, necesitamos usar setlist en lugar de update
files.setlist('imagenes_files', [uploaded_file])

print(f'Data: {dict(data)}')
print(f'Files: {files}')
print(f'Files keys: {list(files.keys())}')
print(f'imagenes_files in files: {"imagenes_files" in files}')

form = ProductoAdminForm(data=data, files=files, instance=producto)
print(f'Formulario válido: {form.is_valid()}')
if not form.is_valid():
    print(f'Errores: {form.errors}')
    print(f'Files en form: {form.files}')
    print(f'Has files: {bool(form.files)}')
    print(f'Files type: {type(form.files)}')
else:
    print('Formulario válido, intentando guardar...')
    try:
        producto_guardado = form.save()
        print(f'Producto guardado exitosamente: {producto_guardado.nombre}')

        # Verificar si se guardaron imágenes
        imagenes_count = producto_guardado.imagenes.count()
        print(f'Imágenes guardadas: {imagenes_count}')

        if imagenes_count > 0:
            for img in producto_guardado.imagenes.all():
                print(f'Imagen: {img.imagen_nombre}, tamaño: {len(img.imagen_blob) if img.imagen_blob else 0} bytes, tipo: {img.imagen_tipo_mime}')

    except Exception as e:
        print(f'Error al guardar: {e}')
        import traceback
        traceback.print_exc()