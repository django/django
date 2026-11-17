"""
This custom Session model adds an extra column to store an account ID. In
real-world applications, it gives you the option of querying the database for
all active sessions for a particular account.
"""

from django.contrib.sessions.backends.cached_db import SessionStore as CachedDBStore
from django.contrib.sessions.backends.db import SessionStore as DBStore
from django.contrib.sessions.base_session import AbstractBaseSession
from django.db import models


class CustomSession(AbstractBaseSession):
    """
    A session model with a column for an account ID.
    """

    account_id = models.IntegerField(null=True, db_index=True)

    @classmethod
    def get_session_store_class(cls):
        return SessionStore


class SessionStore(DBStore):
    """
    A database session store, that handles updating the account ID column
    inside the custom session model.
    """

    @classmethod
    def get_model_class(cls):
        return CustomSession

    def create_model_instance(self, data):
        obj = super().create_model_instance(data)

        try:
            account_id = int(data.get("_auth_user_id"))
        except (ValueError, TypeError):
            account_id = None
        obj.account_id = account_id

        return obj

    def get_session_cookie_age(self):
        return 60 * 60 * 24  # One day.


class ReferencedSession(AbstractBaseSession):
    """
    A session model that another model references.
    """

    @classmethod
    def get_session_store_class(cls):
        return ReferencedSessionStore


class SessionReference(models.Model):
    session = models.ForeignKey(ReferencedSession, models.CASCADE)
    memo = models.CharField(max_length=20)


class ReferencedSessionStore(DBStore):
    @classmethod
    def get_model_class(cls):
        return ReferencedSession


class CachedReferencedSessionStore(CachedDBStore):
    cache_key_prefix = "sessions_tests.cached_referenced_session"

    @classmethod
    def get_model_class(cls):
        return ReferencedSession


class MultiTenantSession(AbstractBaseSession):
    """
    A session model that another model is related to by several fields.
    """

    tenant_id = models.IntegerField(default=1)

    @classmethod
    def get_session_store_class(cls):
        return MultiTenantSessionStore


class MultiTenantSessionNote(models.Model):
    session_key = models.CharField(max_length=40)
    tenant_id = models.IntegerField(default=1, null=True)
    session = models.ForeignObject(
        MultiTenantSession,
        models.CASCADE,
        from_fields=["session_key", "tenant_id"],
        to_fields=["session_key", "tenant_id"],
    )


class MultiTenantSessionStore(DBStore):
    @classmethod
    def get_model_class(cls):
        return MultiTenantSession
