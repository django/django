from __future__ import unicode_literals

import six

from django.apps import apps
from django.db.models.signals import post_save, post_delete

from ..channel import Group


class BindingMetaclass(type):
    """
    Metaclass that tracks instantiations of its type.
    """

    binding_classes = []

    def __new__(cls, name, bases, body):
        klass = type.__new__(cls, name, bases, body)
        if bases != (object, ):
            cls.binding_classes.append(klass)
        return klass

    @classmethod
    def register_all(cls):
        for binding_class in cls.binding_classes:
            binding_class.register()


@six.add_metaclass(BindingMetaclass)
class Binding(object):
    """
    Represents a two-way data binding from channels/groups to a Django model.
    Outgoing binding sends model events to zero or more groups.
    Incoming binding takes messages and maybe applies the action based on perms.

    To implement outbound, implement:
     - group_names, which returns a list of group names to send to
     - serialize, which returns message contents from an instance + action

    To implement inbound, implement:
     - deserialize, which returns pk, data and action from message contents
     - has_permission, which says if the user can do the action on an instance
     - create, which takes the data and makes a model instance
     - update, which takes data and a model instance and applies one to the other

    Outbound will work once you implement the functions; inbound requires you
    to place one or more bindings inside a protocol-specific Demultiplexer
    and tie that in as a consumer.
    """

    model = None

    @classmethod
    def register(cls):
        """
        Resolves models.
        """
        # If model is None directly on the class, assume it's abstract.
        if cls.model is None:
            if "model" in cls.__dict__:
                return
            else:
                raise ValueError("You must set the model attribute on Binding %r!" % cls)
        # Optionally resolve model strings
        if isinstance(cls.model, six.string_types):
            cls.model = apps.get_model(cls.model)
        # Connect signals
        post_save.connect(cls.save_receiver, sender=cls.model)
        post_delete.connect(cls.delete_receiver, sender=cls.model)

    # Outbound binding

    @classmethod
    def save_receiver(cls, instance, created, **kwargs):
        """
        Entry point for triggering the binding from save signals.
        """
        cls.trigger_outbound(instance, "create" if created else "update")

    @classmethod
    def delete_receiver(cls, instance, **kwargs):
        """
        Entry point for triggering the binding from save signals.
        """
        cls.trigger_outbound(instance, "delete")

    @classmethod
    def trigger_outbound(cls, instance, action):
        """
        Triggers the binding to possibly send to its group.
        """
        self = cls()
        self.instance = instance
        # Check to see if we're covered
        for group_name in self.group_names(instance, action):
            group = Group(group_name)
            group.send(self.serialize(instance, action))

    def group_names(self, instance, action):
        """
        Returns the iterable of group names to send the object to based on the
        instance and action performed on it.
        """
        raise NotImplementedError()

    def serialize(self, instance, action):
        """
        Should return a serialized version of the instance to send over the
        wire (return value must be a dict suitable for sending over a channel -
        e.g., to send JSON as a WebSocket text frame, you must return
        {"text": json.dumps(instance_serialized_as_dict)}
        """
        raise NotImplementedError()

    # Inbound binding

    @classmethod
    def trigger_inbound(cls, message):
        """
        Triggers the binding to see if it will do something.
        We separate out message serialization to a consumer, so this gets
        native arguments.
        """
        # Late import as it touches models
        from django.contrib.auth.models import AnonymousUser
        self = cls()
        self.message = message
        # Deserialize message
        self.action, self.pk, self.data = self.deserialize(self.message)
        self.user = getattr(self.message, "user", AnonymousUser())
        # Run incoming action
        self.run_action(self.action, self.pk, self.data)

    def deserialize(self, message):
        """
        Returns action, pk, data decoded from the message. pk should be None
        if action is create; data should be None if action is delete.
        """
        raise NotImplementedError()

    def has_permission(self, user, action, pk):
        """
        Return True if the user can do action to the pk, False if not.
        User may be AnonymousUser if no auth hooked up/they're not logged in.
        Action is one of "create", "delete", "update".
        """
        raise NotImplementedError()

    def run_action(self, action, pk, data):
        """
        Performs the requested action. This version dispatches to named
        functions by default for update/create, and handles delete itself.
        """
        # Check to see if we're allowed
        if self.has_permission(self.user, pk):
            if action == "create":
                self.create(data)
            elif action == "update":
                self.update(self.model.get(pk=pk), data)
            elif action == "delete":
                self.model.filter(pk=pk).delete()
            else:
                raise ValueError("Bad action %r" % action)

    def create(self, data):
        """
        Creates a new instance of the model with the data.
        """
        raise NotImplementedError()

    def update(self, instance, data):
        """
        Updates the model with the data.
        """
        raise NotImplementedError()
