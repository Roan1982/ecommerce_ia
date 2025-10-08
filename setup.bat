@echo off
echo ========================================
echo   CONFIGURACION DEL PROYECTO ECOMMERCE
echo ========================================

echo Creando entorno virtual (venv)...
python -m venv venv

echo Activando entorno virtual...
call venv\Scripts\activate

echo Instalando dependencias desde requirements.txt...
pip install --upgrade pip
pip install -r requirements.txt

echo Creando migraciones (si es necesario)...
python manage.py makemigrations --noinput

echo Aplicando migraciones...
python manage.py migrate --noinput

echo Verificando existencia de superusuario 'admin'...
python - <<PY
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
	User.objects.create_superuser('admin', 'admin@example.com', 'admin')
	print('Superusuario admin creado: admin / admin')
else:
	print('Superusuario admin ya existe')
PY

echo.
set /p POPULAR="Deseas poblar la base de datos con datos de prueba? (s/N): "
if /I "%POPULAR%"=="s" (
	echo Poblando BD con datos de prueba...
	python poblar_bd.py
	echo Asignando metas de wishlist basadas en precio...
	python scripts\asignar_metas_wishlist.py
) else (
	echo Saltando población de BD.
)

echo ========================================
echo   CONFIGURACION COMPLETADA
echo ========================================
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