"""
Storages used to assist in the deprecation of contrib.auth User messages.

"""
from django.contrib.messages import constants
from django.contrib.messages.storage.base import BaseStorage, Message
from django.contrib.auth.models import User
from django.contrib.messages.storage.fallback import FallbackStorage


class UserMessagesStorage(BaseStorage):
    """
    Retrieves messages from the User, using the legacy user.message_set API.

    This storage is "read-only" insofar as it can only retrieve and delete
    messages, not store them.
    """
    session_key = '_messages'

    def _get_messages_queryset(self):
        """
        Returns the QuerySet containing all user messages (or ``None`` if
        request.user is not a contrib.auth User).
        """
        user = getattr(self.request, 'user', None)
        if isinstance(user, User):
            return user._message_set.all()

    def add(self, *args, **kwargs):
        raise NotImplementedError('This message storage is read-only.')

    def _get(self, *args, **kwargs):
        """
        Retrieves a list of messages assigned to the User.  This backend never
        stores anything, so all_retrieved is assumed to be False.
        """
        queryset = self._get_messages_queryset()
        if queryset is None:
            # This is a read-only and optional storage, so to ensure other
            # storages will also be read if used with FallbackStorage an empty
            # list is returned rather than None.
            return [], False
        messages = []
        for user_message in queryset:
            messages.append(Message(constants.INFO, user_message.message))
        return messages, False

    def _store(self, messages, *args, **kwargs):
        """
        Removes any messages assigned to the User and returns the list of
        messages (since no messages are stored in this read-only storage).
        """
        queryset = self._get_messages_queryset()
        if queryset is not None:
            queryset.delete()
        return messages


class LegacyFallbackStorage(FallbackStorage):
    """
    Works like ``FallbackStorage`` but also handles retrieving (and clearing)
    contrib.auth User messages.
    """
    storage_classes = (UserMessagesStorage,) + FallbackStorage.storage_classes
