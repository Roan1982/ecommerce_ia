"""
Management command para enviar notificaciones de productos con descuento en wishlist
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
from django.db import models
from datetime import timedelta
from tienda.models import Wishlist, Producto, User
from tienda.services.email_service import EmailService


class Command(BaseCommand):
    help = 'Envía notificaciones de productos con descuento a usuarios que los tienen en wishlist'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dias',
            type=int,
            default=7,
            help='Días desde la última notificación para reenviar (default: 7)'
        )
        parser.add_argument(
            '--descuento-minimo',
            type=int,
            default=10,
            help='Porcentaje mínimo de descuento para notificar (default: 10%)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Ejecutar sin enviar emails (solo mostrar qué se haría)'
        )
        parser.add_argument(
            '--usuario',
            type=str,
            help='Enviar solo para un usuario específico (email)'
        )

    def handle(self, *args, **options):
        dias_ultima_notif = options['dias']
        descuento_minimo = options['descuento_minimo']
        dry_run = options['dry_run']
        usuario_especifico = options['usuario']

        # Calcular fecha límite para notificaciones previas
        fecha_limite = timezone.now() - timedelta(days=dias_ultima_notif)

        self.stdout.write(
            self.style.SUCCESS(f'Buscando productos con descuento ≥{descuento_minimo}% en wishlists')
        )

        # Obtener productos con descuento activo
        productos_descuento = Producto.objects.filter(
            estado='activo',
            stock__gt=0
        ).exclude(
            precio_descuento__isnull=True
        ).filter(
            precio_descuento__lt=models.F('precio') * (100 - descuento_minimo) / 100
        )

        self.stdout.write(
            self.style.SUCCESS(f'Encontrados {productos_descuento.count()} productos con descuento')
        )

        if not productos_descuento.exists():
            self.stdout.write(self.style.WARNING('No hay productos con descuento para notificar'))
            return

        # Obtener usuarios con estos productos en wishlist
        usuarios_notificar = User.objects.filter(
            is_active=True,
            wishlist_items__producto__in=productos_descuento
        ).distinct()

        if usuario_especifico:
            usuarios_notificar = usuarios_notificar.filter(email=usuario_especifico)

        self.stdout.write(
            self.style.SUCCESS(f'Encontrados {usuarios_notificar.count()} usuarios para notificar')
        )

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No se enviarán emails'))
            for usuario in usuarios_notificar[:5]:  # Mostrar solo primeros 5
                productos_usuario = productos_descuento.filter(
                    wishlist_users__usuario=usuario
                )
                self.stdout.write(
                    f'  Usuario: {usuario.email} - Productos con descuento: {productos_usuario.count()}'
                )
            return

        # Enviar notificaciones
        enviados = 0
        errores = 0

        for usuario in usuarios_notificar:
            try:
                # Obtener productos con descuento en wishlist del usuario
                productos_usuario = productos_descuento.filter(
                    wishlist_users__usuario=usuario
                )

                # Filtrar productos que no tuvieron notificación reciente
                productos_para_notificar = []
                for producto in productos_usuario:
                    # Verificar si ya se envió notificación reciente para este producto
                    from tienda.models import EmailNotification
                    notificacion_reciente = EmailNotification.objects.filter(
                        usuario=usuario,
                        tipo='producto_descuento',
                        fecha_creacion__gt=fecha_limite,
                        producto=producto
                    ).exists()

                    if not notificacion_reciente:
                        productos_para_notificar.append(producto)

                if productos_para_notificar:
                    # Enviar email
                    email_service = EmailService()
                    notificacion = email_service.enviar_oferta_productos_wishlist(
                        usuario,
                        productos_para_notificar
                    )

                    enviados += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'✓ Notificación enviada a {usuario.email} ({len(productos_para_notificar)} productos)')
                    )

            except Exception as e:
                errores += 1
                self.stdout.write(
                    self.style.ERROR(f'✗ Error enviando a {usuario.email}: {str(e)}')
                )

        # Resumen final
        self.stdout.write(self.style.SUCCESS(f'\nResumen:'))
        self.stdout.write(f'  Notificaciones enviadas: {enviados}')
        if errores > 0:
            self.stdout.write(self.style.ERROR(f'  Errores: {errores}'))

        # Sugerencias para automatización
        if enviados > 0:
            self.stdout.write(self.style.SUCCESS(f'\nPara automatizar:'))
            self.stdout.write(f'  Agregar a crontab: 0 9 * * * cd {settings.BASE_DIR} && python manage.py send_wishlist_discount_notifications')
            self.stdout.write(f'  (Ejecuta diariamente a las 9 AM)')