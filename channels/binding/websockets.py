import json

from django.core import serializers

from .base import Binding
from ..generic.websockets import WebsocketDemultiplexer


class WebsocketBinding(Binding):
    """
    Websocket-specific outgoing binding subclass that uses JSON encoding
    and the built-in JSON/WebSocket multiplexer.

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

    # Stream multiplexing name

    stream = None

    # Outbound

    def serialize(self, instance, action):
        payload = {
            "action": action,
            "pk": instance.pk,
            "data": self.serialize_data(instance),
        }
        # Encode for the stream
        assert self.stream is not None
        return WebsocketDemultiplexer.encode(self.stream, payload)

    def serialize_data(self, instance):
        """
        Serializes model data into JSON-compatible types.
        """
        data = serializers.serialize('json', [instance])
        return json.loads(data)[0]['fields']

    # Inbound

    def deserialize(self, message):
        """
        You must hook this up behind a Deserializer, so we expect the JSON
        already dealt with.
        """
        action = message['action']
        pk = message.get('pk', None)
        data = message.get('data', None)
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
