"""Base email backend class."""

class BaseEmailBackend(object):
    """
    Base class for email backend implementations.

    Subclasses must at least overwrite send_messages().
    """
    def __init__(self, fail_silently=False, **kwargs):
        self.fail_silently = fail_silently

    def open(self):
        """Open a network connection.

        This method can be overwritten by backend implementations to
        open a network connection.

        It's up to the backend implementation to track the status of
        a network connection if it's needed by the backend.

        This method can be called by applications to force a single
        network connection to be used when sending mails. See the
        send_messages() method of the SMTP backend for a reference
        implementation.

        The default implementation does nothing.
        """
        pass

    def close(self):
        """Close a network connection."""
        pass

    def send_messages(self, email_messages):
        """
        Sends one or more EmailMessage objects and returns the number of email
        messages sent.
        """
        raise NotImplementedError
