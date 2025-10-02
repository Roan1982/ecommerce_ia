@echo off
echo ========================================
echo      SERVIDOR DE DESARROLLO DJANGO
echo ========================================

echo Activando entorno virtual...
call venv\Scripts\activate

echo Iniciando servidor de desarrollo...
echo.
echo El servidor estara disponible en:
echo http://127.0.0.1:8000/
echo.
echo Panel de administracion:
echo http://127.0.0.1:8000/admin/
echo.
echo Presiona Ctrl+C para detener el servidor
echo.

python manage.py runserver