import json

from django.core import serializers

from .base import Binding
from ..generic.websockets import JsonWebsocketConsumer


class WebsocketBinding(Binding):
    """
    Websocket-specific outgoing binding subclass that uses JSON encoding.

    To implement outbound, implement:
     - group_names, which returns a list of group names to send to

    To implement inbound, implement:
     - has_permission, which says if the user can do the action on an instance

    Optionally also implement:
     - serialize_data, which returns JSON-safe data from a model instance
     - create, which takes incoming data and makes a model instance
     - update, which takes incoming data and a model instance and applies one to the other
    """

    # Mark as abstract

    model = None

    # Outbound

    def serialize(self, instance, action):
        return {
            "text": json.dumps({
                "model": "%s.%s" % (
                    instance._meta.app_label.lower(),
                    instance._meta.object_name.lower(),
                ),
                "action": action,
                "pk": instance.pk,
                "data": self.serialize_data(instance),
            }),
        }

    def serialize_data(self, instance):
        """
        Serializes model data into JSON-compatible types.
        """
        data = serializers.serialize('json', [instance])
        return json.loads(data)[0]['fields']

    # Inbound

    def deserialize(self, message):
        content = json.loads(message['text'])
        action = content['action']
        pk = content.get('pk', None)
        data = content.get('data', None)
        return action, pk, data

    def _hydrate(self, pk, data):
        """
        Given a raw "data" section of an incoming message, returns a
        DeserializedObject.
        """
        s_data = [
            {
                "pk": pk,
                "model": self.model_label,
                "fields": data,
            }
        ]
        # TODO: Avoid the JSON roundtrip by using encoder directly?
        return list(serializers.deserialize("json", json.dumps(s_data)))[0]

    def create(self, data):
        self._hydrate(None, data).save()

    def update(self, pk, data):
        instance = self.model.objects.get(pk=pk)
        hydrated = self._hydrate(pk, data)
        for name in data.keys():
            setattr(instance, name, getattr(hydrated.object, name))
        instance.save()


class WebsocketBindingDemultiplexer(JsonWebsocketConsumer):
    """
    Allows you to combine multiple Bindings as one websocket consumer.
    Subclass and provide a custom list of Bindings.
    """

    http_user = True
    warn_if_no_match = True
    bindings = None

    def receive(self, content):
        # Sanity check
        if self.bindings is None:
            raise ValueError("Demultiplexer has no bindings!")
        # Find the matching binding
        model_label = content['model']
        triggered = False
        for binding in self.bindings:
            if binding.model_label == model_label:
                binding.trigger_inbound(self.message)
                triggered = True
        # At least one of them should have fired.
        if not triggered and self.warn_if_no_match:
            raise ValueError("No binding found for model %s" % model_label)
