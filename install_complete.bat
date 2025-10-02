@echo off
echo ========================================
echo   INSTALACION COMPLETA DEL PROYECTO
echo ========================================

echo Ejecutando configuracion inicial...
call setup.bat

echo.
echo Creando superusuario...
call create_superuser.bat

echo.
echo ========================================
echo   INSTALACION COMPLETADA
echo ========================================
echo.
echo El proyecto esta completamente configurado y listo.
echo.
echo Para ejecutar el servidor en el futuro:
echo - Ejecuta: runserver.bat
echo - O manualmente: python manage.py runserver
echo.
echo Credenciales de admin:
echo Usuario: admin
echo Contrasena: admin123
echo.
pause