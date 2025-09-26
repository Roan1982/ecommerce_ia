"""
Servicios para el sistema de notificaciones por email
"""
import logging
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from tienda.models import EmailNotification, EmailQueue, EmailTemplate, Profile

logger = logging.getLogger(__name__)


class EmailService:
    """Servicio para manejar el envío de emails del sistema"""

    @staticmethod
    def crear_notificacion(tipo, usuario, contexto=None, prioridad='normal', programar_para=None):
        """
        Crea una notificación de email

        Args:
            tipo: Tipo de notificación (registro, recuperacion, pedido_confirmacion, etc.)
            usuario: Usuario destinatario
            contexto: Diccionario con variables para la plantilla
            prioridad: Prioridad del email (baja, normal, alta, urgente)
            programar_para: Fecha para envío programado
        """
        if contexto is None:
            contexto = {}

        try:
            # Obtener plantilla
            plantilla = EmailTemplate.objects.get(tipo=tipo, activo=True)

            # Renderizar contenido
            contexto.update({
                'user': usuario,
                'SITE_URL': settings.SITE_URL,
                'fecha_envio': timezone.now(),
            })

            asunto = plantilla.render_asunto(contexto)
            contenido_html = plantilla.render_contenido(contexto)

            # Crear notificación
            notificacion = EmailNotification.objects.create(
                usuario=usuario,
                tipo=tipo,
                email_destino=usuario.email,
                asunto=asunto,
                contenido_html=contenido_html,
                prioridad=prioridad,
                fecha_programada=programar_para,
            )

            # Agregar a cola si no está programada
            if not programar_para:
                EmailQueue.objects.create(
                    notificacion=notificacion,
                    prioridad=EmailService._get_prioridad_numero(prioridad)
                )

            logger.info(f"Notificación creada: {tipo} para {usuario.email}")
            return notificacion

        except EmailTemplate.DoesNotExist:
            logger.error(f"Plantilla de email no encontrada: {tipo}")
            raise ValueError(f"Plantilla de email '{tipo}' no encontrada")
        except Exception as e:
            logger.error(f"Error creando notificación: {str(e)}")
            raise

    @staticmethod
    def enviar_notificacion(notificacion):
        """
        Envía una notificación específica

        Args:
            notificacion: Instancia de EmailNotification
        """
        try:
            # Enviar email
            email = EmailMultiAlternatives(
                subject=notificacion.asunto,
                body=notificacion.contenido_texto or '',
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[notificacion.email_destino]
            )

            email.attach_alternative(notificacion.contenido_html, "text/html")
            email.send()

            # Marcar como enviada
            notificacion.marcar_enviado()
            logger.info(f"Email enviado: {notificacion.asunto} a {notificacion.email_destino}")

            return True

        except Exception as e:
            logger.error(f"Error enviando email: {str(e)}")
            notificacion.marcar_fallido(str(e))
            return False

    @staticmethod
    def procesar_cola():
        """
        Procesa la cola de emails pendientes
        """
        emails_procesados = 0

        # Obtener emails que se pueden procesar
        emails_pendientes = EmailQueue.objects.filter(
            estado='pendiente',
            notificacion__estado='pendiente'
        ).select_related('notificacion').order_by('-prioridad', 'fecha_creacion')[:10]

        for email_queue in emails_pendientes:
            try:
                with transaction.atomic():
                    # Marcar como procesando
                    email_queue.marcar_procesando()

                    # Enviar email
                    exito = EmailService.enviar_notificacion(email_queue.notificacion)

                    if exito:
                        email_queue.marcar_enviado()
                        emails_procesados += 1
                    else:
                        email_queue.marcar_fallido()

            except Exception as e:
                logger.error(f"Error procesando email en cola: {str(e)}")
                email_queue.marcar_fallido(str(e))

        return emails_procesados

    @staticmethod
    def _get_prioridad_numero(prioridad):
        """Convierte prioridad string a número"""
        prioridades = {
            'baja': 0,
            'normal': 1,
            'alta': 2,
            'urgente': 3,
        }
        return prioridades.get(prioridad, 1)

    # ===== MÉTODOS ESPECÍFICOS PARA TIPOS DE EMAIL =====

    @staticmethod
    def enviar_bienvenida_registro(usuario):
        """Envía email de bienvenida tras registro"""
        contexto = {
            'user': usuario,
        }
        return EmailService.crear_notificacion('registro', usuario, contexto, 'alta')

    @staticmethod
    def enviar_recuperacion_password(usuario, reset_url):
        """Envía email de recuperación de contraseña"""
        contexto = {
            'user': usuario,
            'reset_url': reset_url,
        }
        return EmailService.crear_notificacion('recuperacion', usuario, contexto, 'urgente')

    @staticmethod
    def enviar_confirmacion_pedido(pedido):
        """Envía confirmación de pedido"""
        contexto = {
            'user': pedido.usuario,
            'pedido': pedido,
        }
        return EmailService.crear_notificacion('pedido_confirmacion', pedido.usuario, contexto, 'alta')

    @staticmethod
    def enviar_actualizacion_pedido(pedido, numero_seguimiento=None, empresa_envio=None, tiempo_entrega=None):
        """Envía actualización de estado de pedido"""
        contexto = {
            'user': pedido.usuario,
            'pedido': pedido,
            'numero_seguimiento': numero_seguimiento,
            'empresa_envio': empresa_envio,
            'tiempo_entrega': tiempo_entrega,
            'fecha_actualizacion': timezone.now(),
        }
        return EmailService.crear_notificacion('pedido_actualizacion', pedido.usuario, contexto, 'alta')

    @staticmethod
    def enviar_carrito_abandonado(usuario, carrito_items, recomendaciones=None):
        """Envía recordatorio de carrito abandonado"""
        total = sum(item.subtotal for item in carrito_items)

        contexto = {
            'user': usuario,
            'carrito_items': carrito_items,
            'total_carrito': total,
            'recomendaciones': recomendaciones or [],
        }
        return EmailService.crear_notificacion('carrito_abandonado', usuario, contexto, 'normal')

    @staticmethod
    def enviar_oferta_productos_wishlist(usuario, productos_descuento):
        """Envía ofertas de productos en wishlist"""
        contexto = {
            'user': usuario,
            'productos_descuento': productos_descuento,
            'descuento': '20',  # Porcentaje genérico, se puede calcular
        }
        return EmailService.crear_notificacion('producto_descuento', usuario, contexto, 'normal')

    @staticmethod
    def enviar_notificacion_puntos(usuario, puntos_ganados, razon):
        """Envía notificación de puntos acumulados"""
        try:
            perfil = Profile.objects.get(usuario=usuario)
        except Profile.DoesNotExist:
            perfil = None

        contexto = {
            'user': usuario,
            'perfil': perfil,
            'puntos_ganados': puntos_ganados,
            'razon_puntos': razon,
        }
        return EmailService.crear_notificacion('puntos_acumulados', usuario, contexto, 'normal')

    @staticmethod
    def enviar_newsletter_bienvenida(suscriptor):
        """Envía bienvenida al newsletter"""
        contexto = {
            'subscription': suscriptor,
        }
        # Crear notificación especial para newsletter
        notificacion = EmailNotification.objects.create(
            usuario=suscriptor.usuario if hasattr(suscriptor, 'usuario') else None,
            tipo='newsletter_bienvenida',
            email_destino=suscriptor.email,
            asunto='¡Bienvenido a nuestro Newsletter!',
            contenido_html=render_to_string('tienda/emails/newsletter_confirmacion.html', contexto),
            prioridad='normal',
        )
        EmailQueue.objects.create(
            notificacion=notificacion,
            prioridad=1
        )
        return notificacion