@echo off
echo ========================================
echo   CONFIGURACION DEL PROYECTO ECOMMERCE
echo ========================================

echo Creando entorno virtual...
python -m venv venv

echo Activando entorno virtual...
call venv\Scripts\activate

echo Instalando dependencias...
pip install -r requirements.txt

echo Creando migraciones...
python manage.py makemigrations

echo Aplicando migraciones...
python manage.py migrate

echo Creando superusuario...
echo from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.filter(username='admin').exists() or User.objects.create_superuser('admin', 'admin@example.com', 'admin') | python manage.py shell

echo ========================================
echo   CONFIGURACION COMPLETADA
echo ========================================
echo.
echo Credenciales de superusuario:
echo Usuario: admin
echo Contrasena: admin
echo.
echo Iniciando servidor de desarrollo...
echo.
echo El servidor estara disponible en:
echo http://127.0.0.1:8000/
echo.
echo Panel de administracion:
echo http://127.0.0.1:8000/admin/
echo Usuario: admin
echo Contrasena: admin
echo.
echo Presiona Ctrl+C para detener el servidor
echo.

python manage.py runserver