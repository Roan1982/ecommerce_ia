"""
Management command para procesar campañas de newsletter automatizadas
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
from datetime import timedelta, datetime
from tienda.models import NewsletterCampaign, NewsletterSubscription, NewsletterLog
from tienda.services.email_service import EmailService


class Command(BaseCommand):
    help = 'Procesa campañas de newsletter programadas y envía emails'

    def add_arguments(self, parser):
        parser.add_argument(
            '--max-emails',
            type=int,
            default=50,
            help='Máximo número de emails a enviar por ejecución (default: 50)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Ejecutar sin enviar emails (solo mostrar qué se haría)'
        )
        parser.add_argument(
            '--campana',
            type=int,
            help='Procesar solo una campaña específica (ID)'
        )

    def handle(self, *args, **options):
        max_emails = options['max_emails']
        dry_run = options['dry_run']
        campana_id = options['campana']

        self.stdout.write(
            self.style.SUCCESS(f'Procesando campañas de newsletter (máx. {max_emails} emails por campaña)')
        )

        # Obtener campañas programadas para envío
        now = timezone.now()
        campanas_programadas = NewsletterCampaign.objects.filter(
            estado='programado',
            fecha_programada__lte=now
        )

        if campana_id:
            campanas_programadas = campanas_programadas.filter(id=campana_id)

        if not campanas_programadas.exists():
            self.stdout.write(self.style.WARNING('No hay campañas programadas para envío'))
            return

        total_campanas = campanas_programadas.count()
        self.stdout.write(
            self.style.SUCCESS(f'Encontradas {total_campanas} campañas para procesar')
        )

        # Procesar cada campaña
        for campana in campanas_programadas:
            try:
                self.stdout.write(f'\n--- Procesando campaña: {campana.titulo} ---')

                # Iniciar envío si no está iniciado
                if campana.estado == 'programado':
                    campana.iniciar_envio()
                    self.stdout.write(
                        self.style.SUCCESS(f'✓ Iniciado envío de campaña "{campana.titulo}"')
                    )

                # Obtener suscriptores objetivo
                suscriptores = campana.obtener_suscriptores_target()

                # Filtrar suscriptores que no han recibido esta campaña
                suscriptores_pendientes = []
                for suscriptor in suscriptores:
                    # Verificar si ya recibió esta campaña
                    ya_recibido = NewsletterLog.objects.filter(
                        campaign=campana,
                        suscriptor=suscriptor,
                        tipo='envio'
                    ).exists()

                    if not ya_recibido:
                        suscriptores_pendientes.append(suscriptor)

                emails_enviados = 0
                emails_restantes = len(suscriptores_pendientes)

                self.stdout.write(f'  Suscriptores objetivo: {suscriptores.count()}')
                self.stdout.write(f'  Pendientes de envío: {emails_restantes}')

                if dry_run:
                    self.stdout.write(self.style.WARNING('  DRY RUN - No se enviarán emails'))
                    continue

                # Enviar emails por lotes
                for suscriptor in suscriptores_pendientes[:max_emails]:
                    try:
                        # Crear log de envío
                        log = NewsletterLog.objects.create(
                            campaign=campana,
                            suscriptor=suscriptor,
                            tipo='envio'
                        )

                        # Enviar email usando el servicio de email
                        contexto = {
                            'campaign': campana,
                            'subscription': suscriptor,
                            'log_id': log.id,
                        }

                        # Usar EmailService para enviar newsletter
                        email_service = EmailService()
                        # Crear notificación especial para newsletter
                        notificacion = email_service.crear_notificacion(
                            'newsletter_bienvenida',  # Reutilizar template
                            suscriptor.usuario if hasattr(suscriptor, 'usuario') else None,
                            contexto,
                            'normal'
                        )

                        # Enviar la notificación
                        exito = email_service.enviar_notificacion(notificacion)

                        if exito:
                            emails_enviados += 1
                            campana.enviados += 1
                            campana.save()

                            # Actualizar log
                            log.fecha = timezone.now()
                            log.save()

                            self.stdout.write(
                                f'  ✓ Email enviado a {suscriptor.email}'
                            )
                        else:
                            # Marcar como error
                            NewsletterLog.objects.create(
                                campaign=campana,
                                suscriptor=suscriptor,
                                tipo='rebote'
                            )

                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f'  ✗ Error enviando a {suscriptor.email}: {str(e)}')
                        )
                        # Crear log de error
                        NewsletterLog.objects.create(
                            campaign=campana,
                            suscriptor=suscriptor,
                            tipo='rebote'
                        )

                # Verificar si la campaña está completa
                total_enviados = campana.enviados
                total_objetivo = campana.total_suscriptores

                if total_enviados >= total_objetivo:
                    campana.completar_envio()
                    self.stdout.write(
                        self.style.SUCCESS(f'✓ Campaña "{campana.titulo}" completada')
                    )
                else:
                    self.stdout.write(
                        f'  Progreso: {total_enviados}/{total_objetivo} emails enviados'
                    )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'✗ Error procesando campaña "{campana.titulo}": {str(e)}')
                )

        # Resumen final
        self.stdout.write(self.style.SUCCESS(f'\n=== RESUMEN ==='))
        campanas_activas = NewsletterCampaign.objects.filter(estado='enviando').count()
        campanas_completadas = NewsletterCampaign.objects.filter(
            estado='enviado',
            fecha_envio__date=timezone.now().date()
        ).count()

        self.stdout.write(f'Campañas activas: {campanas_activas}')
        self.stdout.write(f'Campañas completadas hoy: {campanas_completadas}')

        # Sugerencias para automatización
        self.stdout.write(self.style.SUCCESS(f'\nPara automatizar:'))
        self.stdout.write(f'  Agregar a crontab: */10 * * * * cd {settings.BASE_DIR} && python manage.py send_newsletter_campaigns --max-emails=25')
        self.stdout.write(f'  (Ejecuta cada 10 minutos, máximo 25 emails por ejecución)')