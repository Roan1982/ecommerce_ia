import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_project.settings')
django.setup()

from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.contrib.admin.sites import AdminSite

# Crear una instancia del admin
admin_site = AdminSite()
user_admin = UserAdmin(User, admin_site)

# Obtener el formulario para agregar usuario
add_form = user_admin.get_form(None)
print('Campos del formulario de agregar usuario:')
for field_name, field in add_form.base_fields.items():
    print(f'  {field_name}: {field.__class__.__name__} - Required: {field.required}')

print('\nFieldsets del UserAdmin:')
for fieldset_name, fieldset_options in user_admin.fieldsets:
    print(f'  {fieldset_name}: {fieldset_options.get("fields", [])}')