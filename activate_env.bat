@echo off
echo ========================================
echo     ENTORNO DE DESARROLLO ACTIVADO
echo ========================================

echo Activando entorno virtual...
call venv\Scripts\activate

echo.
echo Entorno virtual activado correctamente.
echo Ahora puedes ejecutar comandos de Django directamente.
echo.
echo Comandos utiles:
echo - python manage.py runserver    (Iniciar servidor)
echo - python manage.py shell        (Consola interactiva)
echo - python manage.py makemigrations (Crear migraciones)
echo - python manage.py migrate      (Aplicar migraciones)
echo - python manage.py test         (Ejecutar tests)
echo.
echo Presiona Ctrl+C para salir del entorno
echo.

cmd /k