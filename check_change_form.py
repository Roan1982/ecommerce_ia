import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_project.settings')
django.setup()

from tienda.admin import CustomUserAdmin
from django.contrib.auth.models import User

# Crear instancia del admin
admin_instance = CustomUserAdmin(User, None)

# Obtener el formulario para cambiar usuario
change_form = admin_instance.get_form(None, instance=User(username='test'))
print('Campos del formulario de cambiar usuario:')
for field_name, field in change_form.base_fields.items():
    print(f'  {field_name}: {field.__class__.__name__} - Required: {field.required} - Initial: {getattr(field, "initial", None)}')