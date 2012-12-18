try:
    from django.utils.six.moves import cPickle as pickle
except ImportError:
    import pickle

from django.conf import settings
from django.core import signing

from django.contrib.sessions.backends.base import SessionBase


class PickleSerializer(object):
    """
    Simple wrapper around pickle to be used in signing.dumps and
    signing.loads.
    """
    def dumps(self, obj):
        return pickle.dumps(obj, pickle.HIGHEST_PROTOCOL)

    def loads(self, data):
        return pickle.loads(data)


class SessionStore(SessionBase):

    def load(self):
        """
        We load the data from the key itself instead of fetching from
        some external data store. Opposite of _get_session_key(),
        raises BadSignature if signature fails.
        """
        try:
            return signing.loads(self.session_key,
                serializer=PickleSerializer,
                # This doesn't handle non-default expiry dates, see #19201
                max_age=settings.SESSION_COOKIE_AGE,
                salt='django.contrib.sessions.backends.signed_cookies')
        except (signing.BadSignature, ValueError):
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
        return signing.dumps(session_cache, compress=True,
            salt='django.contrib.sessions.backends.signed_cookies',
            serializer=PickleSerializer)

    @classmethod
    def clear_expired(cls):
        pass
