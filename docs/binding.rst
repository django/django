Data Binding
============

.. warning::

    Data Binding is new and might change slightly in the
    upcoming weeks, and so don't consider this API totally stable yet.

The Channels data binding framework automates the process of tying Django
models into frontend views, such as javascript-powered website UIs. It provides
a quick and flexible way to generate messages on Groups for model changes
and to accept messages that change models themselves.

The main target for the moment is WebSockets, but the framework is flexible
enough to be used over any protocol.

What does data binding allow?
-----------------------------

Data binding in Channels works two ways:

* Outbound, where model changes made through Django are sent out to listening
  clients. This includes creation, updates and deletion of instances.

* Inbound, where a standardised message format allows creation, update and
  deletion of instances to be made by clients sending messages.

Combined, these allow a UI to be designed that automatically updates to
reflect new values and reflects across clients. A live blog is easily done
using data binding against the post object, for example, or an edit interface
can show data live as it's edited by other users.

It has some limitations:

* Signals are used to power outbound binding, so if you change the values of
  a model outside of Django (or use the ``.update()`` method on a QuerySet),
  the signals are not triggered and the change will not be sent out. You
  can trigger changes yourself, but you'll need to source the events from the
  right place for your system.

* The built-in serializers are based on the built-in Django ones and can only
  handle certain field types; for more flexibility, you can plug in something
  like the Django REST Framework serializers.

Getting Started
---------------

A single Binding subclass will handle outbound and inbound binding for a model,
and you can have multiple bindings per model (if you want different formats
or permission checks, for example).

You can inherit from the base Binding and provide all the methods needed, but
we'll focus on the WebSocket JSON variant here, as it's the easiest thing to
get started and likely close to what you want.

Start off like this::

    from django.db import models
    from channels.binding.websockets import WebsocketBinding

    class IntegerValue(models.Model):

        name = models.CharField(max_length=100, unique=True)
        value = models.IntegerField(default=0)

    class IntegerValueBinding(WebsocketBinding):

        model = IntegerValue
        stream = "intval"
        fields = ["name", "value"]

        def group_names(self, instance, action):
            return ["intval-updates"]

        def has_permission(self, user, action, pk):
            return True

This defines a WebSocket binding - so it knows to send outgoing messages
formatted as JSON WebSocket frames - and provides the three things you must
always provide:

* ``fields`` is a whitelist of fields to return in the serialized request.
  Channels does not default to all fields for security concerns; if you want
  this, set it to the value ``["__all__"]``.

* ``group_names`` returns a list of groups to send outbound updates to based
  on the model and action. For example, you could dispatch posts on different
  liveblogs to groups that included the parent blog ID in the name; here, we
  just use a fixed group name.

* ``has_permission`` returns if an inbound binding update is allowed to actually
  be carried out on the model. We've been very unsafe and made it always return
  ``True``, but here is where you would check against either Django's or your
  own permission system to see if the user is allowed that action.

For reference, ``action`` is always one of the unicode strings ``"create"``,
``"update"`` or ``"delete"``. You also supply the :ref:`multiplexing`
stream name to provide to the client - you must use multiplexing if you
use WebSocket data binding.

Just adding the binding like this in a place where it will be imported will
get outbound messages sending, but you still need a Consumer that will both
accept incoming binding updates and add people to the right Groups when they
connect. The WebSocket binding classes use the standard :ref:`multiplexing`,
so you just need to use that::

    from channels.generic.websockets import WebsocketDemultiplexer

    class Demultiplexer(WebsocketDemultiplexer):

        mapping = {
            "intval": "binding.intval",
        }

        def connection_groups(self):
            return ["intval-updates"]

As well as the standard stream-to-channel mapping, you also need to set
``connection_groups``, a list of groups to put people in when they connect.
This should match the logic of ``group_names`` on your binding - we've used
our fixed group name again.

Tie that into your routing, and tie each demultiplexed channel into the
``.consumer`` attribute of the Binding, and you're ready to go::

    from channels import route_class, route
    from .consumers import Demultiplexer
    from .models import IntegerValueBinding

    channel_routing = [
        route_class(Demultiplexer, path="^/binding/"),
        route("binding.intval", IntegerValueBinding.consumer),
    ]


Frontend Considerations
-----------------------

You can use the standard Channels WebSocket wrapper **(not yet available)**
to automatically run demultiplexing, and then tie the events you receive into
your frontend framework of choice based on ``action``, ``pk`` and ``data``.

.. note::

    Common plugins for data binding against popular JavaScript frameworks are
    wanted; if you're interested, please get in touch.


Custom Serialization/Protocols
------------------------------

Rather than inheriting from the ``WebsocketBinding``, you can inherit directly
from the base ``Binding`` class and implement serialization and deserialization
yourself. Until proper reference documentation for this is written, we
recommend looking at the source code in ``channels/bindings/base.py``; it's
reasonably well-commented.


Dealing with Disconnection
--------------------------

Because the data binding Channels ships with has no history of events,
it means that when a disconnection happens you may miss events that happen
during your offline time. For this reason, it's recommended you reload
data directly using an API call once connection has been re-established,
don't rely on the live updates for critical functionality, or have UI designs
that cope well with missing data (e.g. ones where it's all updates and no
creates, so the next update will correct everything).
