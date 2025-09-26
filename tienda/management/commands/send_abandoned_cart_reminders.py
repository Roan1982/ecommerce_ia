"""
Management command para detectar y enviar recordatorios de carritos abandonados
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
from datetime import timedelta
from tienda.models import Carrito, CarritoProducto, User
from tienda.services.email_service import EmailService


class Command(BaseCommand):
    help = 'Detecta carritos abandonados y envía recordatorios por email'

    def add_arguments(self, parser):
        parser.add_argument(
            '--horas',
            type=int,
            default=24,
            help='Horas de inactividad para considerar un carrito abandonado (default: 24)'
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
        horas_inactividad = options['horas']
        dry_run = options['dry_run']
        usuario_especifico = options['usuario']

        # Calcular fecha límite
        fecha_limite = timezone.now() - timedelta(hours=horas_inactividad)

        self.stdout.write(
            self.style.SUCCESS(f'Detectando carritos abandonados desde: {fecha_limite}')
        )

        # Obtener carritos abandonados
        carritos_abandonados = Carrito.objects.filter(
            fecha_actualizacion__lt=fecha_limite,
            usuario__is_active=True
        ).exclude(
            carritoproducto__isnull=True  # Solo carritos con productos
        ).select_related('usuario').prefetch_related('carritoproducto_set__producto')

        if usuario_especifico:
            carritos_abandonados = carritos_abandonados.filter(usuario__email=usuario_especifico)

        # Filtrar carritos que ya tuvieron recordatorio reciente (últimas 7 días)
        from tienda.models import EmailNotification
        hace_7_dias = timezone.now() - timedelta(days=7)

        carritos_para_recordar = []
        for carrito in carritos_abandonados:
            # Verificar si ya se envió recordatorio reciente
            ultimo_recordatorio = EmailNotification.objects.filter(
                usuario=carrito.usuario,
                tipo='carrito_abandonado',
                fecha_creacion__gt=hace_7_dias
            ).exists()

            if not ultimo_recordatorio:
                carritos_para_recordar.append(carrito)

        self.stdout.write(
            self.style.SUCCESS(f'Encontrados {len(carritos_para_recordar)} carritos para recordar')
        )

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No se enviarán emails'))
            for carrito in carritos_para_recordar[:5]:  # Mostrar solo primeros 5
                productos = carrito.carritoproducto_set.all()
                self.stdout.write(
                    f'  Usuario: {carrito.usuario.email} - Productos: {productos.count()} - Total: ${carrito.total_precio}'
                )
            return

        # Enviar recordatorios
        enviados = 0
        errores = 0

        for carrito in carritos_para_recordar:
            try:
                # Obtener productos del carrito
                productos_carrito = list(carrito.carritoproducto_set.all())

                # Obtener recomendaciones (productos populares)
                from tienda.models import Producto
                recomendaciones = Producto.objects.filter(
                    stock__gt=0,
                    estado='activo'
                ).order_by('-stock')[:3]  # Productos más vendidos

                # Enviar email
                email_service = EmailService()
                notificacion = email_service.enviar_carrito_abandonado(
                    carrito.usuario,
                    productos_carrito,
                    recomendaciones
                )

                enviados += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Recordatorio enviado a {carrito.usuario.email}')
                )

            except Exception as e:
                errores += 1
                self.stdout.write(
                    self.style.ERROR(f'✗ Error enviando a {carrito.usuario.email}: {str(e)}')
                )

        # Resumen final
        self.stdout.write(self.style.SUCCESS(f'\nResumen:'))
        self.stdout.write(f'  Recordatorios enviados: {enviados}')
        if errores > 0:
            self.stdout.write(self.style.ERROR(f'  Errores: {errores}'))

        # Sugerencias para automatización
        if enviados > 0:
            self.stdout.write(self.style.SUCCESS(f'\nPara automatizar:'))
            self.stdout.write(f'  Agregar a crontab: 0 */6 * * * cd {settings.BASE_DIR} && python manage.py send_abandoned_cart_reminders')
            self.stdout.write(f'  (Ejecuta cada 6 horas)')