from django.conf import settings
from django.contrib.sessions.models import Session
from django.contrib.sessions.backends.base import SessionBase
from django.core.exceptions import SuspiciousOperation
import datetime

class SessionStore(SessionBase):
    """
    Implements database session store
    """
    def __init__(self, session_key=None):
        super(SessionStore, self).__init__(session_key)

    def load(self):
        try:
            s = Session.objects.get(
                session_key = self.session_key,
                expire_date__gt=datetime.datetime.now()
            )
            return self.decode(s.session_data)
        except (Session.DoesNotExist, SuspiciousOperation):

            # Create a new session_key for extra security.
            self.session_key = self._get_new_session_key()
            self._session_cache = {}

            # Save immediately to minimize collision
            self.save()
            # Ensure the user is notified via a new cookie.
            self.modified = True
            return {}

    def exists(self, session_key):
        try:
            Session.objects.get(session_key=session_key)
        except Session.DoesNotExist:
            return False
        return True

    def save(self):
        Session.objects.create(
            session_key = self.session_key,
            session_data = self.encode(self._session),
            expire_date = datetime.datetime.now() + datetime.timedelta(seconds=settings.SESSION_COOKIE_AGE)
        )

    def delete(self, session_key):
        try:
            Session.objects.get(session_key=session_key).delete()
        except Session.DoesNotExist:
            pass
