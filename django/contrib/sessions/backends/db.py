import logging

from django.contrib.sessions.backends.base import SessionBase, CreateError
from django.core.exceptions import SuspiciousOperation
from django.db import IntegrityError, transaction, router
from django.utils import timezone
from django.utils.encoding import force_text


class SessionStore(SessionBase):
    """
    Implements database session store.
    """
    def __init__(self, session_key=None):
        super(SessionStore, self).__init__(session_key)

    @classmethod
    def get_session_class(cls):
        return Session

    def load(self):
        try:
            s = self.get_session_class().objects.get(
                session_key=self.session_key,
                expire_date__gt=timezone.now()
            )
            return self.decode(s.session_data)
        except (self.get_session_class().DoesNotExist, SuspiciousOperation) as e:
            if isinstance(e, SuspiciousOperation):
                logger = logging.getLogger('django.security.%s' %
                        e.__class__.__name__)
                logger.warning(force_text(e))
            self.create()
            return {}

    def exists(self, session_key):
        return self.get_session_class().objects.filter(session_key=session_key).exists()

    def create(self):
        while True:
            self._session_key = self._get_new_session_key()
            try:
                # Save immediately to ensure we have a unique entry in the
                # database.
                self.save(must_create=True)
            except CreateError:
                # Key wasn't unique. Try again.
                continue
            self.modified = True
            self._session_cache = {}
            return

    def create_session_instance(self, data):
        """
        Returns a new instance of the session model object, which represents
        the current session state. Intended to be used for saving the session
        data to the database.
        """
        return self.get_session_class()(
            session_key=self._get_or_create_session_key(),
            session_data=self.encode(data),
            expire_date=self.get_expiry_date()
        )

    def save(self, must_create=False):
        """
        Saves the current session data to the database. If 'must_create' is
        True, a database error will be raised if the saving operation doesn't
        create a *new* entry (as opposed to possibly updating an existing
        entry).
        """
        data = self._get_session(no_load=must_create)
        obj = self.create_session_instance(data)
        using = router.db_for_write(self.get_session_class(), instance=obj)
        try:
            with transaction.atomic(using=using):
                obj.save(force_insert=must_create, using=using)
        except IntegrityError:
            if must_create:
                raise CreateError
            raise

    def delete(self, session_key=None):
        if session_key is None:
            if self.session_key is None:
                return
            session_key = self.session_key
        try:
            self.get_session_class().objects.get(session_key=session_key).delete()
        except self.get_session_class().DoesNotExist:
            pass

    @classmethod
    def clear_expired(cls):
        cls.get_session_class().objects.filter(expire_date__lt=timezone.now()).delete()


# At bottom to avoid circular import
from django.contrib.sessions.models import Session
