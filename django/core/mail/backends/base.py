"""Base email backend class."""

import warnings

from django.core.mail import InvalidEmailProvider
from django.utils.deprecation import RemovedInDjango70Warning


class BaseEmailBackend:
    """
    Base class for email backend implementations.

    Subclasses must implement at least send_messages().

    Subclass __init__() should pass alias and unknown **kwargs to
    super.__init__() for proper error reporting.

    open() and close() can be called indirectly by using a backend object as a
    context manager:

       with backend as connection:
           # do something with connection
           pass
    """

    # RemovedInDjango70Warning: _ignore_unknown_kwargs.
    def __init__(
        self, *, alias=None, fail_silently=False, _ignore_unknown_kwargs=None, **kwargs
    ):
        self.alias = alias
        self.fail_silently = fail_silently

        # RemovedInDjango70Warning.
        if _ignore_unknown_kwargs:
            for ignored in _ignore_unknown_kwargs:
                kwargs.pop(ignored, None)

        if kwargs:
            kwarg_names = ", ".join(repr(key) for key in kwargs.keys())
            if alias is not None:
                # Being initialized from mail.providers.
                raise InvalidEmailProvider(
                    f"Unknown OPTIONS for EMAIL_PROVIDERS[{alias!r}]: {kwarg_names}."
                )
            else:
                # Not being initialized from mail.providers.

                # Be more specific than "EmailBackend.__init__()".
                init_name = ".".join(
                    [
                        self.__class__.__module__,
                        self.__class__.__qualname__,
                        "__init__()",
                    ]
                )

                # RemovedInDjango70Warning: change warning to TypeError
                # "... got unexpected keyword argument(s) {kwarg_names}."

                warnings.warn(
                    f"{init_name} does not support {kwarg_names}. "
                    "In Django 7.0, BaseEmailBackend will raise a TypeError "
                    "for unknown keyword arguments.",
                    RemovedInDjango70Warning,
                )

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
