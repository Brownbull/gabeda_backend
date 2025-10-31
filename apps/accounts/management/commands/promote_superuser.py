"""
Django management command to promote a user to superuser.
Usage: python manage.py promote_superuser <email>
"""
from django.core.management.base import BaseCommand
from apps.accounts.models import User


class Command(BaseCommand):
    help = 'Promote a user to superuser status'

    def add_arguments(self, parser):
        parser.add_argument(
            'email',
            type=str,
            help='Email address of the user to promote'
        )

    def handle(self, *args, **options):
        email = options['email']

        try:
            user = User.objects.get(email=email)
            user.is_staff = True
            user.is_superuser = True
            user.save()

            self.stdout.write(
                self.style.SUCCESS(f'✅ Successfully promoted {email} to superuser!')
            )
            self.stdout.write(f'   - is_staff: {user.is_staff}')
            self.stdout.write(f'   - is_superuser: {user.is_superuser}')

        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'❌ User with email {email} does not exist.')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error: {e}')
            )
