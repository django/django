"""Base email backend class."""

from django.core.mail import InvalidMailer
from django.utils.deprecation import RemovedInDjango70Warning, warn_about_external_use


class BaseEmailBackend:
    """
    Base class for email backend implementations.

    Subclasses must implement at least send_messages().

    Subclass __init__() should pass alias and unknown **kwargs to
    super().__init__() for proper error reporting.

    open() and close() can be called indirectly by using a backend object as a
    context manager:

       with backend as connection:
           # do something with connection
           pass
    """

    # RemovedInDjango70Warning: _ignore_unknown_kwargs.
    def __init__(
        self, fail_silently=False, *, alias=None, _ignore_unknown_kwargs=None, **kwargs
    ):
        self.alias = alias
        self.fail_silently = fail_silently

        # RemovedInDjango70Warning.
        if _ignore_unknown_kwargs:
            for ignored in _ignore_unknown_kwargs:
                kwargs.pop(ignored, None)

        if kwargs:
            kwarg_names = ", ".join(repr(key) for key in kwargs.keys())

            # RemovedInDjango70Warning.
            if alias is None:
                # Not being initialized from mail.mailers. Unknown kwargs are
                # ignored -- with a deprecation warning if they originated from
                # outside Django (either direct construction of a built-in
                # backend or a super.__init__() call from a custom subclass).
                # Use something more precise than self.__class__.__name__,
                # which is often just "EmailBackend".
                class_name = f"{type(self).__module__}.{type(self).__qualname__}"
                warn_about_external_use(
                    f"{class_name}.__init__() does not support {kwarg_names}. "
                    "In Django 7.0, BaseEmailBackend will raise a TypeError "
                    "for unknown keyword arguments.",
                    RemovedInDjango70Warning,
                    skip_name_prefixes="django.core.mail.backends",
                )
                return

            raise InvalidMailer(f"Unknown options {kwarg_names}.", alias=alias)

    def open(self):
        """
        Open a network connection.

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

    def __enter__(self):
        try:
            self.open()
        except Exception:
            self.close()
            raise
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def send_messages(self, email_messages):
        """
        Send one or more EmailMessage objects and return the number of email
        messages sent.
        """
        raise NotImplementedError(
            "subclasses of BaseEmailBackend must override send_messages() method"
        )
