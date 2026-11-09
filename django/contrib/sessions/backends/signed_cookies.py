import datetime
import time

from django.contrib.sessions.backends.base import SessionBase
from django.core import signing


class _SessionSigner(signing.TimestampSigner):
    def unsign_object_with_timestamp(
        self, signed_obj, serializer=signing.JSONSerializer
    ):
        value = super().unsign_object(signed_obj, serializer=serializer)
        # The signature and timestamp have been validated by unsign_object().
        timestamp = signed_obj.rsplit(self.sep, 2)[1]
        return value, signing.b62_decode(timestamp)


class SessionStore(SessionBase):
    def load(self):
        """
        Load the data from the key itself instead of fetching from some
        external data store. Opposite of _get_session_key(), raise BadSignature
        if signature fails.
        """
        try:
            session_data, timestamp = _SessionSigner(
                salt="django.contrib.sessions.backends.signed_cookies"
            ).unsign_object_with_timestamp(
                self.session_key,
                serializer=self.serializer,
            )
            expiry = session_data.get("_session_expiry")
            if isinstance(expiry, str):
                expiry = datetime.datetime.fromisoformat(expiry)
                tz = expiry.tzinfo
            else:
                tz = datetime.UTC
            modification = datetime.datetime.fromtimestamp(timestamp, tz=tz)
            if self.get_expiry_date(modification=modification, expiry=expiry) <= (
                datetime.datetime.fromtimestamp(time.time(), tz=tz)
            ):
                raise signing.SignatureExpired
            return session_data
        except Exception:
            # BadSignature, ValueError, or unpickling exceptions. If any of
            # these happen, reset the session.
            self.create()
        return {}

    async def aload(self):
        return self.load()

    def create(self):
        """
        To create a new key, set the modified flag so that the cookie is set
        on the client for the current request.
        """
        self.modified = True

    async def acreate(self):
        return self.create()

    def save(self, must_create=False):
        """
        To save, get the session key as a securely signed string and then set
        the modified flag so that the cookie is set on the client for the
        current request.
        """
        self._session_key = self._get_session_key()
        self.modified = True

    async def asave(self, must_create=False):
        return self.save(must_create=must_create)

    def exists(self, session_key=None):
        """
        This method makes sense when you're talking to a shared resource, but
        it doesn't matter when you're storing the information in the client's
        cookie.
        """
        return False

    async def aexists(self, session_key=None):
        return self.exists(session_key=session_key)

    def delete(self, session_key=None):
        """
        To delete, clear the session key and the underlying data structure
        and set the modified flag so that the cookie is set on the client for
        the current request.
        """
        self._session_key = ""
        self._session_cache = {}
        self.modified = True

    async def adelete(self, session_key=None):
        return self.delete(session_key=session_key)

    def cycle_key(self):
        """
        Keep the same data but with a new key. Call save() and it will
        automatically save a cookie with a new key at the end of the request.
        """
        self.save()

    async def acycle_key(self):
        return self.cycle_key()

    def _get_session_key(self):
        """
        Instead of generating a random string, generate a secure url-safe
        base64-encoded string of data as our session key.
        """
        return signing.dumps(
            self._session,
            compress=True,
            salt="django.contrib.sessions.backends.signed_cookies",
            serializer=self.serializer,
        )

    @classmethod
    def clear_expired(cls):
        pass

    @classmethod
    async def aclear_expired(cls):
        pass
