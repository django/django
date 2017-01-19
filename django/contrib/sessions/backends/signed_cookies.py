import datetime

from django.conf import settings
from django.contrib.sessions.backends.base import SessionBase
from django.core import signing
from django.utils import timezone


class SessionStore(SessionBase):

    def load(self):
        """
        We load the data from the key itself instead of fetching from
        some external data store. Opposite of _get_session_key(),
        raises BadSignature if signature fails.
        """
        try:
            # Retrieve the session data if it contains valid data, no matter how old.
            session_data_non_checked_age = signing.loads(
                self.session_key,
                serializer=self.serializer,
                max_age=None,
                salt='django.contrib.sessions.backends.signed_cookies',
            )

            max_age = session_data_non_checked_age.get('_session_expiry')
            if isinstance(max_age, datetime.datetime):
                max_age = max_age - timezone.now()

            # Handle None and 0
            if not max_age:
                max_age = settings.SESSION_COOKIE_AGE

            return signing.loads(
                self.session_key,
                serializer=self.serializer,
                max_age=max_age,
                salt='django.contrib.sessions.backends.signed_cookies',
            )
        except Exception:
            # BadSignature, ValueError, or unpickling exceptions. If any of
            # these happen, reset the session.
            self.create()
        return {}

    def create(self):
        """
        To create a new key, we simply make sure that the modified flag is set
        so that the cookie is set on the client for the current request.
        """
        self.modified = True

    def save(self, must_create=False):
        """
        To save, we get the session key as a securely signed string and then
        set the modified flag so that the cookie is set on the client for the
        current request.
        """
        self._session_key = self._get_session_key()
        self.modified = True

    def exists(self, session_key=None):
        """
        This method makes sense when you're talking to a shared resource, but
        it doesn't matter when you're storing the information in the client's
        cookie.
        """
        return False

    def delete(self, session_key=None):
        """
        To delete, we clear the session key and the underlying data structure
        and set the modified flag so that the cookie is set on the client for
        the current request.
        """
        self._session_key = ''
        self._session_cache = {}
        self.modified = True

    def cycle_key(self):
        """
        Keeps the same data but with a new key.  To do this, we just have to
        call ``save()`` and it will automatically save a cookie with a new key
        at the end of the request.
        """
        self.save()

    def _get_session_key(self):
        """
        Most session backends don't need to override this method, but we do,
        because instead of generating a random string, we want to actually
        generate a secure url-safe Base64-encoded string of data as our
        session key.
        """
        session_cache = getattr(self, '_session_cache', {})
        return signing.dumps(
            session_cache, compress=True,
            salt='django.contrib.sessions.backends.signed_cookies',
            serializer=self.serializer,
        )

    @classmethod
    def clear_expired(cls):
        pass
