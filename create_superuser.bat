@echo off
echo ========================================
echo    CREAR SUPERUSUARIO DJANGO
echo ========================================

echo Activando entorno virtual...
call venv\Scripts\activate

echo Creando superusuario...
echo.
echo Usuario: admin
echo Email: admin@example.com
echo Contrasena: admin
echo.

echo from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.filter(username='admin').exists() or User.objects.create_superuser('admin', 'admin@example.com', 'admin') | python manage.py shell

echo.
echo ========================================
echo    SUPERUSUARIO CREADO
echo ========================================
echo.
echo Puedes acceder al panel de administracion con:
echo Usuario: admin
echo Contrasena: admin
echo URL: http://127.0.0.1:8000/admin/
echo.
pause