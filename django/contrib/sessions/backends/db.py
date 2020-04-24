import logging

from django.contrib.sessions.backends.base import (
    CreateError, HashingSessionBase, UpdateError,
)
from django.core.exceptions import SuspiciousOperation
from django.db import DatabaseError, IntegrityError, router, transaction
from django.utils import timezone
from django.utils.functional import cached_property


class SessionStore(HashingSessionBase):
    _model = None

    @classmethod
    def get_model_class(cls):
        # Avoids a circular import and allows importing SessionStore when
        # django.contrib.sessions is not in INSTALLED_APPS.
        from django.contrib.sessions.models import Session
        return Session

    @classmethod
    def get_model(cls):
        if cls._model is None: #not hasattr(cls, '_model'):
            cls._model = cls.get_model_class()
        return cls._model

    @classmethod
    def create_model_instance(cls, backend_key, session_data):
        """
        Return a new instance of the session model object, which represents the
        current session state. Intended to be used for saving the session data
        to the database.
        """
        model = cls.get_model()
        return model(
            session_key=backend_key,
            session_data=cls._encode(session_data),
            expire_date=cls._get_expiry_date(session_data))

    # SessionBase methods

    @classmethod
    def _exists(cls, backend_key):
        return cls.get_model().objects.filter(session_key=backend_key).exists()

    @classmethod
    def _load_data(cls, backend_key):
        """
        Load record with the given key and return a dictionary.
        Return None if the session doesn't exists.
        """
        try:
            s = cls.get_model().objects.get(
                session_key=backend_key,
                expire_date__gt=timezone.now())
            return cls._decode(s.session_data)
        except (cls.get_model().DoesNotExist, SuspiciousOperation) as e:
            if isinstance(e, SuspiciousOperation):
                logger = logging.getLogger('django.security.%s' % e.__class__.__name__)
                logger.warning(str(e))

        return None

    @classmethod
    def _save(cls, backend_key, session_data, must_create=False):
        """
        Save the session data to the database. If 'must_create' is
        True, raise a database error if the saving operation doesn't create a
        new entry (as opposed to possibly updating an existing entry).
        """
        data = session_data
        obj = cls.create_model_instance(backend_key, data)
        using = router.db_for_write(cls.get_model(), instance=obj)
        try:
            with transaction.atomic(using=using):
                obj.save(force_insert=must_create, force_update=not must_create, using=using)
        except IntegrityError:
            if must_create:
                raise CreateError
            raise
        except DatabaseError:
            if not must_create:
                raise UpdateError
            raise

    @classmethod
    def _delete(cls, backend_key):
        """
        Delete session from the database,
        fails silently is record doesn't exist
        """
        try:
            cls.get_model().objects.get(session_key=backend_key).delete()
        except cls.get_model().DoesNotExist:
            pass

    @classmethod
    def clear_expired(cls):
        cls.get_model_class().objects.filter(expire_date__lt=timezone.now()).delete()
