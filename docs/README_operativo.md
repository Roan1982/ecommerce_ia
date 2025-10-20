# README operativo — ecommerce_ia

Este documento contiene la guía paso a paso para desplegar, operar y mantener el proyecto `ecommerce_ia` en PythonAnywhere (o entorno similar). Incluye comandos, variables de entorno, troubleshooting y una checklist para producción.

---

## Resumen rápido
1. Clona o actualiza el repo en PythonAnywhere.
2. Crea y activa el virtualenv.
3. Instala dependencias mínimas (Django, PyMySQL). Evita paquetes grandes si tienes cuota limitada.
4. Configura variables de entorno en la pestaña Web.
5. Ejecuta `makemigrations` y `migrate`.
6. Ejecuta `collectstatic` y configura mappings estáticos.
7. Coloca la ruta del virtualenv en la pestaña Web y pulsa Reload.

---

## Estructura de archivos relevante
- `ecommerce_project/settings.py` — configuración principal (DB, SECRET_KEY, STATIC_ROOT).
- `ecommerce_project/wsgi.py` — WSGI callable.
- `manage.py` — script de gestión de Django.
- `tienda/` — aplicación principal (views, models, recomendador).
- `requirements.txt` — lista de dependencias (cuidado con paquetes grandes en free-tier).
- `docs/architecture.mmd` — diagrama mermaid de arquitectura (renderizable).

---

## Comandos (PythonAnywhere — Bash)
A continuación está el flujo mínimo recomendado.

```bash
# 1. ir al directorio del proyecto
cd ~/ecommerce_ia

# 2. actualizar desde GitHub
git fetch origin
git pull origin main

# 3. crear y activar virtualenv (si no existe)
python3 -m venv ~/.virtualenvs/ecommerce_ia
source ~/.virtualenvs/ecommerce_ia/bin/activate

# 4. actualizar pip
pip install --upgrade pip

# 5. instalar paquetes mínimos
pip install "Django==5.2.6" PyMySQL
# si hay espacio y lo necesitas:
# pip install -r requirements.txt

# 6. configurar variables temporalmente para la sesión (mejor poner en Web tab)
export DJANGO_SETTINGS_MODULE='ecommerce_project.settings'
export PA_DB_NAME='RoanIaMusic$ecommerce'
export PA_DB_USER='RoanIaMusic'
export PA_DB_PASSWORD='Roan1982'
# export DJANGO_SECRET_KEY='...' etc.

# 7. ejecutar migraciones
python manage.py makemigrations
python manage.py migrate

# 8. collectstatic
mkdir -p ~/ecommerce_ia/staticfiles
python manage.py collectstatic --noinput

# 9. comprobar logs si hay errores
tail -n 200 /var/log/roaniamusic.pythonanywhere.com.error.log
```

### PowerShell (local)
```powershell
cd C:\Users\angel.steklein\Documents\desarrollo\ecommerce_ia
# activar venv local
.\venv\Scripts\Activate.ps1
pip install -r .\requirements.txt
python manage.py check
```

---

## Variables de entorno recomendadas (poner en Web tab)
- `DJANGO_SETTINGS_MODULE = ecommerce_project.settings`
- `DJANGO_SECRET_KEY = <your-secret-key>`
- `DJANGO_DEBUG = False`
- `PA_DB_NAME = RoanIaMusic$ecommerce`
- `PA_DB_USER = RoanIaMusic`
- `PA_DB_PASSWORD = Roan1982`
- `PA_DB_HOST = RoanIaMusic.mysql.pythonanywhere-services.com` (si aplica)
- Email settings: `EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_PORT`, `EMAIL_USE_TLS`
- Payment keys: `STRIPE_API_KEY` / other gateway creds

---

## Mapeo de archivos estáticos (Web tab)
- URL: `/static/` → Directory: `/home/RoanIaMusic/ecommerce_ia/staticfiles`
- (Si usas media/uploads) URL: `/media/` → Directory: `/home/RoanIaMusic/ecommerce_ia/media`

---

## Troubleshooting común

### 1) `ModuleNotFoundError: No module named 'pandas'` durante `migrate`
- Causa: import top-level de pandas en algún módulo (paquete no instalado en venv).
- Solución rápida: asegúrate de usar el venv correcto en VS Code / Bash; o eliminar importaciones top-level. Ya hemos movido el import en `tienda/views.py`.
- Si necesitas pandas en producción, instala `pip install pandas` (cuidado con la cuota).

### 2) `Disk quota exceeded` al instalar requisitos
- Instala solo lo esencial: `Django` y `PyMySQL`.
- Borra backups antiguos y archivos grandes en tu home para liberar espacio.
- Considera usar un servicio externo para paquetes pesados o cambiar a un plan de pago de PA.

### 3) Errores en WSGI / Module import
- Abre `/var/www/roaniamusic_pythonanywhere_com_wsgi.py` en el editor y verifica que `project_home` y `DJANGO_SETTINGS_MODULE` están correctos.

### 4) Errores 500 en producción
- Revisa `/var/log/roaniamusic.pythonanywhere.com.error.log` y `server.log`.
- Verifica variables de entorno en Web tab y que el venv está especificado.

---

## Backups y mantenimiento
- DB dump (si el host lo permite):
  ```bash
  mysqldump -u RoanIaMusic -pRoan1982 RoanIaMusic$ecommerce > /home/RoanIaMusic/backups/db_backup_$(date +%F).sql
  ```
- Código: `tar -czf ecommerce_ia_backup_$(date +%F).tar.gz ~/ecommerce_ia`
- Programa backups periódicos con cron (si tiene soporte en tu plan) o manualmente.

---

## Checklist pre-lanzamiento
- [ ] SECRET_KEY en Web tab
- [ ] DB credentials en Web tab
- [ ] Virtualenv path configurado en Web tab
- [ ] Static files mapping configurado
- [ ] `migrate` ejecutado con éxito
- [ ] `collectstatic` completado
- [ ] Logs limpios (sin errores críticos)

---

## Notas operativas y recomendaciones
- Mantén `recomendador.py` con lazy imports (ya implementado) para evitar fallos en arranque si faltan libs.
- Para tarea intensiva (recomendaciones), considera ejecutar procesos en background (Celery) y cachear resultados.
- Usar S3/Cloud storage para media y CDN para static mejora performance y reduce cuota local.

---

Si quieres, puedo:
- Generar un PNG del diagrama `docs/architecture.mmd` y añadirlo a `docs/`.
- Añadir un script de backup `scripts/backup.sh` y una entrada de ejemplo para cron.

Dime si quieres que genere el PNG y el script de backup ahora; los creo y añado al repo.  
