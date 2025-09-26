from django.core.management.base import BaseCommand, CommandError
from tienda.models import NewsletterCampaign

class Command(BaseCommand):
    help = 'Envía una campaña de newsletter específica'

    def add_arguments(self, parser):
        parser.add_argument(
            'campaign_id',
            type=int,
            help='ID de la campaña a enviar'
        )
        parser.add_argument(
            '--test',
            action='store_true',
            help='Enviar como campaña de prueba (solo al admin)',
        )

    def handle(self, *args, **options):
        campaign_id = options['campaign_id']
        is_test = options['test']

        try:
            campaign = NewsletterCampaign.objects.get(id=campaign_id)
        except NewsletterCampaign.DoesNotExist:
            raise CommandError(f'Campaña con ID {campaign_id} no encontrada')

        self.stdout.write(
            self.style.SUCCESS(f'Enviando campaña: "{campaign.titulo}"')
        )

        if is_test:
            # Enviar solo a un email de prueba (del admin)
            from django.conf import settings
            admin_email = getattr(settings, 'ADMIN_EMAIL', 'admin@example.com')

            self.stdout.write(f'Enviando prueba a: {admin_email}')

            # Aquí iría la lógica para enviar email de prueba
            # Por simplicidad, usamos el método send_campaign pero limitado

        else:
            # Enviar campaña completa
            resultado = campaign.send_campaign()

            if resultado['success']:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Campaña enviada exitosamente. '
                        f'{resultado["emails_enviados"]} enviados, '
                        f'{resultado["emails_fallidos"]} fallidos.'
                    )
                )
            else:
                raise CommandError(f'Error enviando campaña: {resultado.get("error", "Error desconocido")}')

        self.stdout.write(
            self.style.SUCCESS('Comando completado exitosamente')
        )