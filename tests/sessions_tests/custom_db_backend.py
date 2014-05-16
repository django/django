"""
This custom Session model adds an extra column to store an account ID. In
real-world applications, it gives you the option of querying the database for
all active sessions for a particular account.
"""
from django.contrib.sessions.backends.db import SessionStore as DBStore
from django.contrib.sessions.base_session import AbstractBaseSession
from django.db import models


class CustomSession(AbstractBaseSession):
    """
    A session model with a column for an account ID.
    """
    account_id = models.IntegerField(null=True, db_index=True)

    class Meta:
        app_label = 'sessions'

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
        obj = super(SessionStore, self).create_model_instance(data)

        try:
            account_id = int(data.get('_auth_user_id'))
        except (ValueError, TypeError):
            account_id = None
        obj.account_id = account_id

        return obj
