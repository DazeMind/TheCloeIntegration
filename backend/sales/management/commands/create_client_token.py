from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from rest_framework.authtoken.models import Token


class Command(BaseCommand):
    help = (
        'Crea o actualiza un usuario cliente (is_staff=False) y muestra su token '
        'DRF una sola vez. Uso: create_client_token <username>'
    )

    def add_arguments(self, parser):
        parser.add_argument('username')

    def handle(self, *args, **options):
        username = options['username']
        user_model = get_user_model()
        user, created = user_model.objects.get_or_create(
            username=username,
            defaults={'is_staff': False, 'is_active': True},
        )
        if not created:
            user.is_staff = False
            user.is_active = True
            user.save(update_fields=['is_staff', 'is_active'])

        token, _ = Token.objects.get_or_create(user=user)
        self.stdout.write(token.key)