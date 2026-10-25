from django.tasks import task

from . import mailers
from .serialization import deserialize_message


@task
def send_email(mailer, messages):
    """
    Send serialized EmailMessages using the MAILERS alias mailer, and return
    the number of messages sent.
    """
    email_messages = [deserialize_message(message) for message in messages]
    return mailers[mailer].send_messages(email_messages)
