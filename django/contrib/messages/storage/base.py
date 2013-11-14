from __future__ import unicode_literals

from django.conf import settings
from django.utils.encoding import force_text, python_2_unicode_compatible
from django.contrib.messages import constants, utils


LEVEL_TAGS = utils.get_level_tags()


@python_2_unicode_compatible
class Message(object):
    """
    Represents an actual message that can be stored in any of the supported
    storage classes (typically session- or cookie-based) and rendered in a view
    or template.
    """

    def __init__(self, level, message, extra_tags=None):
        self.level = int(level)
        self.message = message
        self.extra_tags = extra_tags

    def _prepare(self):
        """
        Prepares the message for serialization by forcing the ``message``
        and ``extra_tags`` to unicode in case they are lazy translations.

        Known "safe" types (None, int, etc.) are not converted (see Django's
        ``force_text`` implementation for details).
        """
        self.message = force_text(self.message, strings_only=True)
        self.extra_tags = force_text(self.extra_tags, strings_only=True)

    def __eq__(self, other):
        return isinstance(other, Message) and self.level == other.level and \
            self.message == other.message

    def __str__(self):
        return force_text(self.message)

    def _get_tags(self):
        extra_tags = force_text(self.extra_tags, strings_only=True)
        if extra_tags and self.level_tag:
            return ' '.join([extra_tags, self.level_tag])
        elif extra_tags:
            return extra_tags
        elif self.level_tag:
            return self.level_tag
        return ''
    tags = property(_get_tags)

    @property
    def level_tag(self):
        return force_text(LEVEL_TAGS.get(self.level, ''), strings_only=True)


class BaseStorage(object):
    """
    This is the base backend for temporary message storage.

    This is not a complete class; to be a usable storage backend, it must be
    subclassed and the two methods ``_get`` and ``_store`` overridden.
    """

    def __init__(self, request, *args, **kwargs):
        self.request = request
        self._queued_messages = []
        self.used = False
        self.added_new = False
        super(BaseStorage, self).__init__(*args, **kwargs)

    def __len__(self):
        return len(self._loaded_messages) + len(self._queued_messages)

    def __iter__(self):
        self.used = True
        if self._queued_messages:
            self._loaded_messages.extend(self._queued_messages)
            self._queued_messages = []
        return iter(self._loaded_messages)

    def __contains__(self, item):
        return item in self._loaded_messages or item in self._queued_messages

    @property
    def _loaded_messages(self):
        """
        Returns a list of loaded messages, retrieving them first if they have
        not been loaded yet.
        """
        if not hasattr(self, '_loaded_data'):
            messages, all_retrieved = self._get()
            self._loaded_data = messages or []
        return self._loaded_data

    def _get(self, *args, **kwargs):
        """
        Retrieves a list of stored messages. Returns a tuple of the messages
        and a flag indicating whether or not all the messages originally
        intended to be stored in this storage were, in fact, stored and
        retrieved; e.g., ``(messages, all_retrieved)``.

        **This method must be implemented by a subclass.**

        If it is possible to tell if the backend was not used (as opposed to
        just containing no messages) then ``None`` should be returned in
        place of ``messages``.
        """
        raise NotImplementedError('subclasses of BaseStorage must provide a _get() method')

    def _store(self, messages, response, *args, **kwargs):
        """
        Stores a list of messages, returning a list of any messages which could
        not be stored.

        One type of object must be able to be stored, ``Message``.

        **This method must be implemented by a subclass.**
        """
        raise NotImplementedError('subclasses of BaseStorage must provide a _store() method')

    def _prepare_messages(self, messages):
        """
        Prepares a list of messages for storage.
        """
        for message in messages:
            message._prepare()

    def update(self, response):
        """
        Stores all unread messages.

        If the backend has yet to be iterated, previously stored messages will
        be stored again. Otherwise, only messages added after the last
        iteration will be stored.
        """
        self._prepare_messages(self._queued_messages)
        if self.used:
            return self._store(self._queued_messages, response)
        elif self.added_new:
            messages = self._loaded_messages + self._queued_messages
            return self._store(messages, response)

    def add(self, level, message, extra_tags=''):
        """
        Queues a message to be stored.

        The message is only queued if it contained something and its level is
        not less than the recording level (``self.level``).
        """
        if not message:
            return
        # Check that the message level is not less than the recording level.
        level = int(level)
        if level < self.level:
            return
        # Add the message.
        self.added_new = True
        message = Message(level, message, extra_tags=extra_tags)
        self._queued_messages.append(message)

    def _get_level(self):
        """
        Returns the minimum recorded level.

        The default level is the ``MESSAGE_LEVEL`` setting. If this is
        not found, the ``INFO`` level is used.
        """
        if not hasattr(self, '_level'):
            self._level = getattr(settings, 'MESSAGE_LEVEL', constants.INFO)
        return self._level

    def _set_level(self, value=None):
        """
        Sets a custom minimum recorded level.

        If set to ``None``, the default level will be used (see the
        ``_get_level`` method).
        """
        if value is None and hasattr(self, '_level'):
            del self._level
        else:
            self._level = int(value)

    level = property(_get_level, _set_level, _set_level)
