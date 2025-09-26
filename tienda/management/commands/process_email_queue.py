"""
Management command para procesar la cola de emails
"""
from django.core.management.base import BaseCommand
from tienda.services.email_service import EmailService


class Command(BaseCommand):
    help = 'Procesa la cola de emails pendientes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--max-emails',
            type=int,
            default=50,
            help='Número máximo de emails a procesar en esta ejecución'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Mostrar información detallada del procesamiento'
        )

    def handle(self, *args, **options):
        max_emails = options['max_emails']
        verbose = options['verbose']

        self.stdout.write(
            self.style.SUCCESS(f'Iniciando procesamiento de cola de emails (máximo: {max_emails})')
        )

        # Procesar emails
        emails_procesados = EmailService.procesar_cola()

        if verbose:
            self.stdout.write(f'Emails procesados: {emails_procesados}')

        if emails_procesados > 0:
            self.stdout.write(
                self.style.SUCCESS(f'✅ Procesamiento completado: {emails_procesados} emails enviados')
            )
        else:
            self.stdout.write(
                self.style.WARNING('⚠️ No hay emails pendientes para procesar')
            )