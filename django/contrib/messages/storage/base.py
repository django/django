from django.conf import settings
from django.contrib.messages import constants, utils

LEVEL_TAGS = utils.get_level_tags()


class Message:
    """
    Represent an actual message that can be stored in any of the supported
    storage classes (typically session- or cookie-based) and rendered in a view
    or template.
    """

    def __init__(self, level, message, extra_tags=None):
        self.level = int(level)
        self.message = message
        self.extra_tags = extra_tags

    def _prepare(self):
        """
        Prepare the message for serialization by forcing the ``message``
        and ``extra_tags`` to str in case they are lazy translations.
        """
        self.message = str(self.message)
        self.extra_tags = str(self.extra_tags) if self.extra_tags is not None else None

    def __eq__(self, other):
        return (
            self.level == other.level and self.message == other.message
            if isinstance(other, Message)
            else NotImplemented
        )

    def __str__(self):
        return str(self.message)

    @property
    def tags(self):
        return " ".join(tag for tag in [self.extra_tags, self.level_tag] if tag)

    @property
    def level_tag(self):
        return LEVEL_TAGS.get(self.level, "")


class BaseStorage:
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
        super().__init__(*args, **kwargs)

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

    def __repr__(self):
        return f"<{self.__class__.__qualname__}: request={self.request!r}>"

    @property
    def _loaded_messages(self):
        """
        Return a list of loaded messages, retrieving them first if they have
        not been loaded yet.
        """
        if not hasattr(self, "_loaded_data"):
            messages, all_retrieved = self._get()
            self._loaded_data = messages or []
        return self._loaded_data

    def _get(self, *args, **kwargs):
        """
        Retrieve a list of stored messages. Return a tuple of the messages
        and a flag indicating whether or not all the messages originally
        intended to be stored in this storage were, in fact, stored and
        retrieved; e.g., ``(messages, all_retrieved)``.

        **This method must be implemented by a subclass.**

        If it is possible to tell if the backend was not used (as opposed to
        just containing no messages) then ``None`` should be returned in
        place of ``messages``.
        """
        raise NotImplementedError(
            "subclasses of BaseStorage must provide a _get() method"
        )

    def _store(self, messages, response, *args, **kwargs):
        """
        Store a list of messages and return a list of any messages which could
        not be stored.

        One type of object must be able to be stored, ``Message``.

        **This method must be implemented by a subclass.**
        """
        raise NotImplementedError(
            "subclasses of BaseStorage must provide a _store() method"
        )

    def _prepare_messages(self, messages):
        """
        Prepare a list of messages for storage.
        """
        for message in messages:
            message._prepare()

    def update(self, response):
        """
        Store all unread messages.

        If the backend has yet to be iterated, store previously stored messages
        again. Otherwise, only store messages added after the last iteration.
        """
        self._prepare_messages(self._queued_messages)
        if self.used:
            return self._store(self._queued_messages, response)
        elif self.added_new:
            messages = self._loaded_messages + self._queued_messages
            return self._store(messages, response)

    def add(self, level, message, extra_tags=""):
        """
        Queue a message to be stored.

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
        Return the minimum recorded level.

        The default level is the ``MESSAGE_LEVEL`` setting. If this is
        not found, the ``INFO`` level is used.
        """
        if not hasattr(self, "_level"):
            self._level = getattr(settings, "MESSAGE_LEVEL", constants.INFO)
        return self._level

    def _set_level(self, value=None):
        """
        Set a custom minimum recorded level.

        If set to ``None``, the default level will be used (see the
        ``_get_level`` method).
        """
        if value is None and hasattr(self, "_level"):
            del self._level
        else:
            self._level = int(value)

    level = property(_get_level, _set_level, _set_level)
