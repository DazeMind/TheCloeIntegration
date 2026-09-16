from django.core.management.base import BaseCommand
from django_q.tasks import async_task

from sales.models import Venta


class Command(BaseCommand):
    help = (
        'Re-encola ventas huérfanas (RECEIVED/QUEUED/PROCESSING) para emisión de '
        'DTE. Útil tras reinicios o si el cluster estuvo caído. Con --include-failed '
        'reintenta también las FAILED.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--include-failed',
            action='store_true',
            help='Re-intenta también las ventas en estado FAILED.',
        )
        parser.add_argument(
            '--max-ids',
            type=int,
            default=50,
            help='Límite de ventas a encolar por corrida (default 50).',
        )

    def handle(self, *args, **options):
        estados = ['RECEIVED', 'QUEUED', 'PROCESSING']
        if options['include_failed']:
            estados.append('FAILED')

        ventas = Venta.objects.filter(status__in=estados)[: options['max_ids']]
        n = 0
        for venta in ventas:
            async_task(
                'sales.tasks.procesar_venta',
                venta.pk,
                timeout=120,
            )
            n += 1
            self.stdout.write(f'Encolar venta {venta.pk} ({venta.sale_id} [{venta.status}])')
        self.stdout.write(self.style.SUCCESS(f'{n} ventas encoladas.'))