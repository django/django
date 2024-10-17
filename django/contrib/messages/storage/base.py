from django.conf import settings
from django.contrib.messages import constants
from django.contrib.messages import restrictions as res
from django.contrib.messages import utils
from django.utils.functional import SimpleLazyObject

LEVEL_TAGS = SimpleLazyObject(utils.get_level_tags)


class RestrictionsContainer(list):
    res_map = {
        res.AmountRestriction.JSON_TYPE_CODE: res.AmountRestriction,
        res.TimeRestriction.JSON_TYPE_CODE: res.TimeRestriction,
    }

    def to_json_obj(self):
        return [r.to_json() for r in self]

    @classmethod
    def create_from_josn(cls, enc_restrictions):
        # set_trace()
        ret = []
        for r in enc_restrictions:
            restriction_type, values = r.split(res.Restriction.JSON_SEPARATOR)
            ret.append(cls.res_map[restriction_type].from_json_param(values))
        return RestrictionsContainer(ret)

    def __eq__(self, other):
        return set(self) == set(other)


class Message:
    """
    Represent an actual message that can be stored in any of the supported
    storage classes (typically session- or cookie-based) and rendered in a view
    or template.
    """

    def __init__(self, level, message, extra_tags=None, restrictions=[]):
        self.level = int(level)
        self.message = message
        self.extra_tags = extra_tags
        self.restrictions = restrictions or list([res.AmountRestriction(1)])
        self.restrictions = RestrictionsContainer(self.restrictions)
        # if not given any restriction - one show by default
        # todo: self.restrictions =

    def _prepare(self):
        """
        Prepare the message for serialization by forcing the ``message``
        and ``extra_tags`` to str in case they are lazy translations.
        """
        self.message = str(self.message)
        self.extra_tags = str(self.extra_tags) if self.extra_tags is not None else None

    def __eq__(self, other):
        if not isinstance(other, Message):
            return NotImplemented
        return (
            self.level == other.level
            and self.message == other.message
            and self.restrictions == other.restrictions
        )

    def __str__(self):
        return str(self.message)

    def __hash__(self):
        return hash(self.message)

    def __repr__(self):
        extra_tags = f", extra_tags={self.extra_tags!r}" if self.extra_tags else ""
        return f"Message(level={self.level}, message={self.message!r}{extra_tags})"

    @property
    def tags(self):
        return " ".join(tag for tag in [self.extra_tags, self.level_tag] if tag)

    @property
    def level_tag(self):
        return LEVEL_TAGS.get(self.level, "")

    def active(self):
        for r in self.restrictions:
            if r.is_expired():
                return False
        return True

    def on_display(self):
        for r in self.restrictions:
            r.on_display()


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
        # in case that there was a call for render template which would
        # cause iterating throught messages,
        # and then (e.g. in some middleware, would be call for iterating
        # through messages (e.g. by iterating of context['messages'])
        # TODO: implement a way to access messages without affecting
        # calling __iter__ method
        all_msgs = set(self._loaded_messages + self._queued_messages)
        return len(all_msgs)
        # return len(self._loaded_messages) + len(self._queued_messages)

    def __iter__(self):
        if not self.used:
            self.used = True
            if self._queued_messages:
                self._loaded_messages.extend(self._queued_messages)
                self._queued_messages = []

            active_messages = []
            for message in self._loaded_messages:
                if isinstance(message, Message):
                    if message.active():
                        active_messages.append(message)
                else:
                    active_messages.append(message)
            for x in active_messages:
                if isinstance(x, Message):
                    x.on_display()
            # self._queued_messages.extend(m for m in active_messages
            # if m not in self._queued_messages)
            self._queued_messages = active_messages
        return iter(self._queued_messages)

    def __contains__(self, item):
        return item in self._loaded_messages or item in self._queued_messages

    def __repr__(self):
        return f"<{self.__class__.__qualname__}: request={self.request!r}>"

    def filter_store(self, messages, response, *args, **kwargs):
        """stores only active messages from given messages in storage"""
        filtered_messages = [x for x in messages if x.active()]
        return self._store(filtered_messages, response, *args, **kwargs)

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
        # if used or used and added,
        # then _queued_messages contains all messages that should be saved
        # if added, then save: all messages currently stored and added ones
        self._prepare_messages(self._queued_messages)
        if self.used:
            return self.filter_store(self._queued_messages, response)
        elif self.added_new:
            messages = self._loaded_messages + self._queued_messages
            return self.filter_store(messages, response)

    def add(self, level, message, extra_tags="", restrictions=[]):
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
        message = Message(
            level, message, extra_tags=extra_tags, restrictions=restrictions
        )
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
