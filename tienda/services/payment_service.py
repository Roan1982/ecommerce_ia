"""
Servicios para el procesamiento de pagos de contribuciones
"""
import logging
import uuid
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from tienda.models import ContribucionWishlist
from tienda.services.email_service import EmailService

logger = logging.getLogger(__name__)


class PaymentService:
    """Servicio para manejar el procesamiento de pagos de contribuciones"""

    @staticmethod
    def procesar_contribucion(contribucion, datos_pago):
        """
        Procesa el pago de una contribución

        Args:
            contribucion: Instancia de ContribucionWishlist
            datos_pago: Diccionario con datos del pago (tarjeta, etc.)

        Returns:
            dict: Resultado del procesamiento
        """
        try:
            # Validar monto mínimo
            if contribucion.monto < Decimal('1.00'):
                return {
                    'success': False,
                    'error': 'El monto mínimo de contribución es $1.00'
                }

            # Simular procesamiento de pago (en producción usar Stripe, PayPal, etc.)
            resultado_pago = PaymentService._procesar_pago_simulado(contribucion, datos_pago)

            if resultado_pago['success']:
                # Actualizar contribución
                contribucion.estado = 'completado'  # Corregido: usar 'completado' en lugar de 'completada'
                contribucion.referencia_pago = resultado_pago['referencia']
                contribucion.fecha_pago = timezone.now()
                contribucion.save()

                # Verificar si se alcanzó la meta
                wishlist = contribucion.wishlist_item
                if wishlist.objetivo_alcanzado and not hasattr(wishlist, '_pedido_generado'):
                    # Generar pedido automáticamente si se alcanzó la meta
                    PaymentService._generar_pedido_automatico(wishlist)

                # Enviar notificaciones
                PaymentService._enviar_notificaciones_contribucion(contribucion)

                return {
                    'success': True,
                    'referencia': resultado_pago['referencia'],
                    'mensaje': 'Contribución procesada exitosamente'
                }
            else:
                contribucion.estado = 'fallida'
                contribucion.save()
                return resultado_pago

        except Exception as e:
            logger.error(f"Error procesando contribución {contribucion.id}: {str(e)}")
            contribucion.estado = 'fallida'
            contribucion.save()
            return {
                'success': False,
                'error': 'Error interno del sistema'
            }

    @staticmethod
    def _procesar_pago_simulado(contribucion, datos_pago):
        """
        Simula el procesamiento de un pago
        En producción, reemplazar con integración real (Stripe, PayPal, etc.)
        """
        # Simular diferentes escenarios para testing
        importe = float(contribucion.monto)

        # Simular fallo para montos específicos (para testing)
        if importe == 999.99:
            return {
                'success': False,
                'error': 'Pago rechazado por la entidad bancaria'
            }

        # Simular procesamiento exitoso
        referencia = f"SIM_{uuid.uuid4().hex[:12].upper()}"

        # Simular tiempo de procesamiento
        import time
        time.sleep(0.5)  # Simular delay de red

        return {
            'success': True,
            'referencia': referencia,
            'mensaje': 'Pago procesado exitosamente'
        }

    @staticmethod
    def _generar_pedido_automatico(wishlist):
        """
        Genera un pedido automático cuando se alcanza la meta de contribución
        """
        try:
            # Usar el método del modelo Wishlist que ya está implementado correctamente
            pedido = wishlist.convertir_a_pedido()

            logger.info(f"Pedido automático generado para wishlist {wishlist.id}: {pedido.id}")

        except Exception as e:
            logger.error(f"Error generando pedido automático para wishlist {wishlist.id}: {str(e)}")

    @staticmethod
    def _enviar_notificaciones_contribucion(contribucion):
        """
        Envía notificaciones por email relacionadas con la contribución
        """
        try:
            # Notificación al contribuyente
            EmailService.crear_notificacion(
                tipo='contribucion_confirmada',
                usuario=contribucion.usuario_contribuyente,
                contexto={
                    'contribucion': contribucion,
                    'wishlist': contribucion.wishlist_item,
                }
            )

            # Notificación al propietario de la wishlist
            EmailService.crear_notificacion(
                tipo='nueva_contribucion',
                usuario=contribucion.wishlist_item.usuario,
                contexto={
                    'contribucion': contribucion,
                    'wishlist': contribucion.wishlist_item,
                }
            )

        except Exception as e:
            logger.error(f"Error enviando notificaciones de contribución {contribucion.id}: {str(e)}")

    @staticmethod
    def _enviar_notificacion_meta_alcanzada(wishlist, pedido):
        """
        Envía notificación cuando se alcanza la meta de contribución
        """
        try:
            EmailService.crear_notificacion(
                tipo='meta_contribucion_alcanzada',
                usuario=wishlist.usuario,
                contexto={
                    'wishlist': wishlist,
                    'pedido': pedido,
                }
            )
        except Exception as e:
            logger.error(f"Error enviando notificación de meta alcanzada para wishlist {wishlist.id}: {str(e)}")

    @staticmethod
    def reembolsar_contribucion(contribucion, motivo='Cancelación por usuario'):
        """
        Procesa el reembolso de una contribución

        Args:
            contribucion: Instancia de ContribucionWishlist
            motivo: Motivo del reembolso

        Returns:
            bool: True si el reembolso fue exitoso
        """
        try:
            if contribucion.estado != 'completada':
                return False

            # Simular reembolso (en producción usar API del gateway)
            contribucion.estado = 'reembolsada'
            contribucion.notas = f"Reembolsado: {motivo}"
            contribucion.save()

            # Enviar notificación de reembolso
            EmailService.crear_notificacion(
                tipo='contribucion_reembolsada',
                usuario=contribucion.usuario_contribuyente,
                contexto={
                    'contribucion': contribucion,
                    'wishlist': contribucion.wishlist_item,
                    'motivo': motivo,
                }
            )

            logger.info(f"Contribución {contribucion.id} reembolsada: {motivo}")
            return True

        except Exception as e:
            logger.error(f"Error reembolsando contribución {contribucion.id}: {str(e)}")
            return False

    @staticmethod
    def validar_datos_pago(datos_pago):
        """
        Valida los datos de pago proporcionados

        Args:
            datos_pago: Diccionario con datos del pago

        Returns:
            dict: Resultado de la validación
        """
        errores = []

        # Validar campos requeridos (simulado)
        campos_requeridos = ['numero_tarjeta', 'fecha_expiracion', 'cvv', 'nombre_titular']
        for campo in campos_requeridos:
            if not datos_pago.get(campo):
                errores.append(f"El campo {campo} es requerido")

        # Validar formato de tarjeta (simulado)
        numero_tarjeta = datos_pago.get('numero_tarjeta', '').replace(' ', '')
        if numero_tarjeta and not numero_tarjeta.isdigit():
            errores.append("El número de tarjeta debe contener solo dígitos")

        if numero_tarjeta and len(numero_tarjeta) < 13:
            errores.append("El número de tarjeta es demasiado corto")

        return {
            'valido': len(errores) == 0,
            'errores': errores
        }