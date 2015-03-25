import datetime
import socket

from django.core.mail import send_mail
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Sends a test email to the email addresses specified as arguments."

    def add_arguments(self, parser):
        parser.add_argument('email', nargs='+',
            help='One or more email addresses to send the test mail to.')

    def handle(self, *args, **kwargs):
        send_mail(
            subject='Test email from %s on %s' % (socket.gethostname(), datetime.datetime.now()),
            message="If you\'re reading this, it was successful.",
            from_email=None,
            recipient_list=kwargs['email'],
        )
