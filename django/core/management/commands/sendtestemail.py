import datetime
import socket

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Sends a test email to the email addresses specified as arguments."
    missing_args_message = "You must specify some email recipients, or pass the --managers or --admin options."

    def add_arguments(self, parser):
        parser.add_argument('email', nargs='*',
            help='One or more email addresses to send the test mail to.')
        parser.add_argument('--managers', action='store_true', dest='managers', default=False,
            help='Send the test email to all addresses specified in settings.MANAGERS.')
        parser.add_argument('--admins', action='store_true', dest='admins', default=False,
            help='Send the test email to all addresses specified in settings.ADMINS.')

    def handle(self, *args, **kwargs):
        recipients = kwargs['email']

        if kwargs['managers']:
            recipients += [email for name, email in settings.MANAGERS]

        if kwargs['admins']:
            recipients += [email for name, email in settings.ADMINS]

        send_mail(
            subject='Test email from %s on %s' % (socket.gethostname(), datetime.datetime.now()),
            message="If you\'re reading this, it was successful.",
            from_email=settings.SERVER_EMAIL,
            recipient_list=set(recipients),
        )
