"""
Management command para crear plantillas de email por defecto
"""
from django.core.management.base import BaseCommand
from tienda.models import EmailTemplate


class Command(BaseCommand):
    help = 'Crea las plantillas de email por defecto del sistema'

    def handle(self, *args, **options):
        self.stdout.write('Creando plantillas de email por defecto...')

        plantillas = [
            {
                'nombre': 'Bienvenida Registro',
                'tipo': 'registro',
                'asunto': '¡Bienvenido a E-commerce IA!',
                'contenido_html': """
{% extends 'tienda/emails/base_email.html' %}
{% block content %}
<h1>¡Bienvenido a E-commerce IA!</h1>
<p>Hola {{ user.get_full_name|default:user.username }},</p>
<p>Gracias por registrarte. Tu cuenta ha sido creada exitosamente.</p>
<p>¿Qué puedes hacer ahora?</p>
<ul>
    <li>Comprar productos con recomendaciones IA</li>
    <li>Acumular puntos de fidelidad</li>
    <li>Guardar productos en wishlist</li>
    <li>Recibir ofertas exclusivas</li>
</ul>
<a href="{{ SITE_URL }}/productos/" class="email-button">Explorar Productos</a>
{% endblock %}
                """,
                'variables_disponibles': {'user': 'Usuario registrado'}
            },
            {
                'nombre': 'Recuperación Contraseña',
                'tipo': 'recuperacion',
                'asunto': 'Recupera tu contraseña - E-commerce IA',
                'contenido_html': """
{% extends 'tienda/emails/base_email.html' %}
{% block content %}
<h1>Recupera tu contraseña</h1>
<p>Hola {{ user.get_full_name|default:user.username }},</p>
<p>Haz clic en el enlace para restablecer tu contraseña:</p>
<a href="{{ reset_url }}" class="email-button">Restablecer Contraseña</a>
<p>Este enlace expira en 24 horas.</p>
{% endblock %}
                """,
                'variables_disponibles': {'user': 'Usuario', 'reset_url': 'URL de recuperación'}
            },
            {
                'nombre': 'Confirmación Pedido',
                'tipo': 'pedido_confirmacion',
                'asunto': 'Confirmación de Pedido #{{ pedido.id }}',
                'contenido_html': """
{% extends 'tienda/emails/base_email.html' %}
{% block content %}
<h1>¡Pedido Confirmado!</h1>
<p>Hola {{ user.get_full_name|default:user.username }},</p>
<p>Tu pedido #{{ pedido.id }} ha sido confirmado.</p>
<p>Total: ${{ pedido.total }}</p>
<a href="{{ SITE_URL }}/pedidos/{{ pedido.id }}/" class="email-button">Ver Detalles</a>
{% endblock %}
                """,
                'variables_disponibles': {'user': 'Usuario', 'pedido': 'Objeto Pedido'}
            },
            {
                'nombre': 'Actualización Pedido',
                'tipo': 'pedido_actualizacion',
                'asunto': 'Actualización de Pedido #{{ pedido.id }}',
                'contenido_html': """
{% extends 'tienda/emails/base_email.html' %}
{% block content %}
<h1>Actualización de tu Pedido</h1>
<p>Hola {{ user.get_full_name|default:user.username }},</p>
<p>Tu pedido #{{ pedido.id }} ha cambiado de estado a: {{ pedido.get_estado_display }}</p>
<a href="{{ SITE_URL }}/pedidos/{{ pedido.id }}/" class="email-button">Ver Detalles</a>
{% endblock %}
                """,
                'variables_disponibles': {'user': 'Usuario', 'pedido': 'Objeto Pedido'}
            },
            {
                'nombre': 'Carrito Abandonado',
                'tipo': 'carrito_abandonado',
                'asunto': 'No olvides completar tu compra',
                'contenido_html': """
{% extends 'tienda/emails/base_email.html' %}
{% block content %}
<h1>¿Olvidaste algo en tu carrito?</h1>
<p>Hola {{ user.get_full_name|default:user.username }},</p>
<p>Tienes productos esperando en tu carrito.</p>
<p>Total: ${{ total_carrito }}</p>
<a href="{{ SITE_URL }}/carrito/" class="email-button">Completar Compra</a>
{% endblock %}
                """,
                'variables_disponibles': {'user': 'Usuario', 'carrito_items': 'Items del carrito', 'total_carrito': 'Total del carrito'}
            },
            {
                'nombre': 'Producto con Descuento',
                'tipo': 'producto_descuento',
                'asunto': '¡Oferta especial en productos de tu wishlist!',
                'contenido_html': """
{% extends 'tienda/emails/base_email.html' %}
{% block content %}
<h1>¡Ofertas en tu Wishlist!</h1>
<p>Hola {{ user.get_full_name|default:user.username }},</p>
<p>Productos de tu wishlist tienen descuentos especiales.</p>
<a href="{{ SITE_URL }}/wishlist/" class="email-button">Ver Ofertas</a>
{% endblock %}
                """,
                'variables_disponibles': {'user': 'Usuario', 'productos_descuento': 'Lista de productos'}
            },
            {
                'nombre': 'Puntos Acumulados',
                'tipo': 'puntos_acumulados',
                'asunto': '¡Has ganado puntos de fidelidad!',
                'contenido_html': """
{% extends 'tienda/emails/base_email.html' %}
{% block content %}
<h1>¡Puntos Ganados!</h1>
<p>Hola {{ user.get_full_name|default:user.username }},</p>
<p>Has ganado {{ puntos_ganados }} puntos.</p>
<p>Total de puntos: {{ perfil.puntos_actuales }}</p>
<a href="{{ SITE_URL }}/puntos/" class="email-button">Ver Mis Puntos</a>
{% endblock %}
                """,
                'variables_disponibles': {'user': 'Usuario', 'perfil': 'Perfil de usuario', 'puntos_ganados': 'Puntos ganados', 'razon_puntos': 'Razón'}
            }
        ]

        creadas = 0
        actualizadas = 0

        for plantilla_data in plantillas:
            plantilla, created = EmailTemplate.objects.update_or_create(
                tipo=plantilla_data['tipo'],
                defaults={
                    'nombre': plantilla_data['nombre'],
                    'asunto': plantilla_data['asunto'],
                    'contenido_html': plantilla_data['contenido_html'].strip(),
                    'variables_disponibles': plantilla_data['variables_disponibles'],
                    'activo': True
                }
            )

            if created:
                creadas += 1
                self.stdout.write(f'  ✅ Creada: {plantilla.nombre}')
            else:
                actualizadas += 1
                self.stdout.write(f'  🔄 Actualizada: {plantilla.nombre}')

        self.stdout.write(
            self.style.SUCCESS(f'✅ Plantillas procesadas: {creadas} creadas, {actualizadas} actualizadas')
        )