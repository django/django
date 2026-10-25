"""
Email backend that sends messages in the background using django.tasks.
"""

from django.core.mail import InvalidMailer, mailers
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail.serialization import serialize_message
from django.core.mail.tasks import send_email
from django.tasks import TaskResultStatus


class EmailBackend(BaseEmailBackend):
    """
    Enqueue email messages in a task that sends them using another mailer.
    """

    def __init__(
        self,
        *,
        mailer=None,
        task_backend=None,
        queue_name=None,
        priority=None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        if mailer is None:
            raise InvalidMailer("The 'mailer' option is required.", alias=self.alias)
        if mailer == self.alias:
            raise InvalidMailer(
                "The 'mailer' option cannot refer to its own mailer.", alias=self.alias
            )
        if mailer not in mailers:
            raise InvalidMailer(
                f"The 'mailer' option refers to an unknown mailer {mailer!r}.",
                alias=self.alias,
            )
        self.mailer = mailer
        self.task = send_email.using(
            backend=task_backend, queue_name=queue_name, priority=priority
        )

    def send_messages(self, email_messages):
        """
        Enqueue a task to send the messages. Return the number of messages
        sent, which is 0 unless the task backend ran the task immediately.
        """
        messages = [
            serialize_message(message)
            for message in email_messages
            if message.recipients()
        ]
        if not messages:
            return 0
        result = self.task.enqueue(self.mailer, messages)
        if result.status == TaskResultStatus.SUCCESSFUL:
            return result.return_value
        return 0
