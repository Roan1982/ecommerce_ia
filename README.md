# E-commerce con Recomendación de Productos

## Descripción
Sistema de e-commerce simple que incluye un módulo de IA para recomendaciones de productos basadas en compras previas. Ahora con frontend web usando Django.

## Requisitos
- Python 3.x
- Librerías: pandas, scikit-learn, django

## Configuración del Entorno
1. Crear entorno virtual: `python -m venv venv`
2. Activar entorno: `.\venv\Scripts\Activate.ps1` (Windows)
3. Instalar dependencias: `pip install -r requirements.txt`

## Configuración de Django
1. Aplicar migraciones: `python manage.py migrate`
2. Crear superusuario (opcional): `python manage.py createsuperuser`

## Cómo Ejecutar
1. Clona el repositorio.
2. Configura el entorno virtual.
3. Ejecuta `python manage.py runserver`.
4. Abre http://127.0.0.1:8000 en tu navegador.
5. Regístrate o inicia sesión.
6. Explora productos, compra y recibe recomendaciones.

## Probar la IA
- Registra usuarios y realiza compras.
- El módulo de IA usa filtrado colaborativo para recomendaciones.
- Accede a /recomendaciones/ para ver sugerencias.

## Funcionalidades
- Registro e inicio de sesión de usuarios.
- Visualización de productos.
- Sistema de compras.
- Recomendaciones personalizadas basadas en IA.