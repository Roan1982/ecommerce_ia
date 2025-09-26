import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_project.settings')
import django
django.setup()

from django.test import Client
from django.contrib.auth.models import User

# Crear usuario admin si no existe
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')

# Crear cliente de prueba
client = Client()

# Hacer login como admin
login_success = client.login(username='admin', password='admin123')
print(f'Login successful: {login_success}')

# Hacer petición a la página de usuarios
response = client.get('/admin/auth/user/')
print(f'Status code: {response.status_code}')

# Decodificar el contenido de la respuesta
content = response.content.decode('utf-8')

# Buscar el botón 'Add user' en la respuesta (tanto en inglés como en español)
button_texts = ['Add user', 'Añadir usuario', 'Add User', 'AÑADIR USUARIO']
button_found = False
for text in button_texts:
    if text in content:
        print(f'SUCCESS: "{text}" button found in response!')
        button_found = True
        break

if not button_found:
    print('FAILURE: Add user button NOT found in response')

# Mostrar parte de la respuesta para debug
print("\n=== DEBUG INFO ===")
print(f"Content length: {len(content)}")

# Buscar posibles secciones de herramientas
tools_sections = ['object-tools', 'actions', 'toolbar', 'buttons']
for section in tools_sections:
    if f'<div class="{section}">' in content:
        start = content.find(f'<div class="{section}">')
        end = content.find('</div>', start) + 6 if start != -1 else -1
        if start != -1 and end != -1:
            print(f'\n{section} section found:')
            print(content[start:end][:500] + '...' if len(content[start:end]) > 500 else content[start:end])
            break

# Mostrar el inicio del contenido
print("\n=== START OF CONTENT ===")
print(content[:1000])

# Buscar cualquier mención de "user" o "add"
user_add_mentions = []
lines = content.split('\n')
for i, line in enumerate(lines):
    if 'user' in line.lower() and ('add' in line.lower() or 'btn' in line.lower()):
        user_add_mentions.append(f"Line {i}: {line.strip()}")

if user_add_mentions:
    print("\n=== USER/ADD MENTIONS ===")
    for mention in user_add_mentions[:10]:  # Mostrar máximo 10
        print(mention)

# Mostrar el contenido alrededor de la línea 275
print("\n=== CONTENT AROUND LINE 275 ===")
start_line = max(270, 0)
end_line = min(280, len(lines))
for i in range(start_line, end_line):
    if i < len(lines):
        marker = ">>>" if i == 275 else "   "
        print(f"{marker} Line {i}: {lines[i].strip()}")

# Buscar todos los enlaces que contengan "add" y "user"
import re
add_user_links = re.findall(r'<a[^>]*href="[^"]*add[^"]*user[^"]*"[^>]*>.*?</a>', content, re.IGNORECASE | re.DOTALL)
if add_user_links:
    print("\n=== ADD USER LINKS FOUND ===")
    for link in add_user_links:
        print(link)