from django.contrib.sessions.backends.base import SessionBase


class SessionStore(SessionBase):
    """Session store without support for clearing expired sessions."""

    pass
