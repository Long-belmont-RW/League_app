from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings

class Command(BaseCommand):
    help = 'Sends a test email to the specified email address.'

    def add_arguments(self, parser):
        parser.add_argument('email', type=str, help='The email address to send the test email to.')

    def handle(self, *args, **options):
        email = options['email']
        self.stdout.write(f'Sending test email to {email}...')

        try:
            send_mail(
                'Test Email from League App',
                'This is a test email from your Django application.',
                settings.EMAIL_HOST_USER,
                [email],
                fail_silently=False,
            )
            self.stdout.write(self.style.SUCCESS(f'Successfully sent test email to {email}'))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Failed to send test email: {e}'))
