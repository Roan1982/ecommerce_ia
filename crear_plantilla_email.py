#!/usr/bin/env python
"""
Script para crear la plantilla de email 'contribucion_confirmada'
"""
import os
import sys
import django

# Configurar Django
sys.path.append(os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_project.settings')
django.setup()

from tienda.models import EmailTemplate

def crear_plantilla_contribucion():
    """Crear la plantilla de email para confirmación de contribución"""

    # Verificar si ya existe
    if EmailTemplate.objects.filter(nombre='contribucion_confirmada').exists():
        print("La plantilla 'contribucion_confirmada' ya existe.")
        return

    # Crear la plantilla
    plantilla = EmailTemplate.objects.create(
        nombre='contribucion_confirmada',
        tipo='contribucion_confirmada',
        asunto='¡Contribución confirmada! - {{ contribucion.wishlist_item.producto.nombre }}',
        contenido_html="""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Contribución Confirmada</title>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background-color: #4CAF50; color: white; padding: 20px; text-align: center; }
                .content { padding: 20px; background-color: #f9f9f9; }
                .footer { background-color: #333; color: white; padding: 10px; text-align: center; font-size: 12px; }
                .highlight { background-color: #e8f5e8; padding: 15px; border-left: 4px solid #4CAF50; margin: 10px 0; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>¡Contribución Confirmada!</h1>
                </div>

                <div class="content">
                    <p>Hola <strong>{{ contribucion.usuario_contribuyente.first_name|default:contribucion.usuario_contribuyente.username }}</strong>,</p>

                    <div class="highlight">
                        <h3>✅ Tu contribución ha sido procesada exitosamente</h3>
                        <p><strong>Producto:</strong> {{ contribucion.wishlist_item.producto.nombre }}</p>
                        <p><strong>Monto contribuido:</strong> ${{ contribucion.monto }}</p>
                        <p><strong>Referencia de pago:</strong> {{ contribucion.referencia_pago|default:"N/A" }}</p>
                        <p><strong>Fecha:</strong> {{ contribucion.fecha_contribucion|date:"d/m/Y H:i" }}</p>
                    </div>

                    <p>Has contribuido al sueño de <strong>{{ contribucion.wishlist_item.usuario.first_name|default:contribucion.wishlist_item.usuario.username }}</strong> de conseguir <strong>{{ contribucion.wishlist_item.producto.nombre }}</strong>.</p>

                    {% if contribucion.mensaje %}
                    <div style="background-color: #f0f0f0; padding: 15px; margin: 10px 0; border-radius: 5px;">
                        <p><strong>Tu mensaje:</strong></p>
                        <p style="font-style: italic;">"{{ contribucion.mensaje }}"</p>
                    </div>
                    {% endif %}

                    <p>¡Muchas gracias por tu generosidad! Tu contribución hace posible que más personas puedan conseguir lo que desean.</p>

                    <p>Si tienes alguna pregunta, no dudes en contactarnos.</p>

                    <p>¡Saludos!<br>
                    El equipo de la tienda</p>
                </div>

                <div class="footer">
                    <p>Este es un email automático, por favor no respondas a esta dirección.</p>
                </div>
            </div>
        </body>
        </html>
        """,
        contenido_texto="""
        ¡Contribución Confirmada!

        Hola {{ contribucion.usuario_contribuyente.first_name|default:contribucion.usuario_contribuyente.username }},

        Tu contribución ha sido procesada exitosamente.

        Producto: {{ contribucion.wishlist_item.producto.nombre }}
        Monto contribuido: ${{ contribucion.monto }}
        Referencia de pago: {{ contribucion.referencia_pago|default:"N/A" }}
        Fecha: {{ contribucion.fecha_contribucion|date:"d/m/Y H:i" }}

        Has contribuido al sueño de {{ contribucion.wishlist_item.usuario.first_name|default:contribucion.wishlist_item.usuario.username }} de conseguir {{ contribucion.wishlist_item.producto.nombre }}.

        {% if contribucion.mensaje %}
        Tu mensaje: "{{ contribucion.mensaje }}"
        {% endif %}

        ¡Muchas gracias por tu generosidad!

        Saludos,
        El equipo de la tienda
        """,
        variables_disponibles={
            'contribucion': {
                'usuario_contribuyente': 'Usuario que realizó la contribución',
                'wishlist_item': {
                    'producto': {'nombre': 'Nombre del producto'},
                    'usuario': {'first_name': 'Nombre del propietario', 'username': 'Username del propietario'}
                },
                'monto': 'Monto de la contribución',
                'referencia_pago': 'Referencia del pago',
                'fecha_contribucion': 'Fecha de la contribución',
                'mensaje': 'Mensaje opcional del contribuyente'
            }
        },
        activo=True
    )

    print(f"Plantilla 'contribucion_confirmada' creada exitosamente con ID: {plantilla.id}")

if __name__ == '__main__':
    crear_plantilla_contribucion()