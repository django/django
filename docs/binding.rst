Data Binding
============

.. warning::

    The Data Binding part is new and might change slightly in the
    upcoming weeks, and so don't consider this API totally stable yet.

The Channels data binding framework automates the process of tying Django
models into frontend views, such as javascript-powered website UIs. It provides
a quick and flexible way to generate messages on Groups for model changes
and to accept messages that chanes models themselves.

The main target for the moment is WebSockets, but the framework is flexible
enough to be used over any protocol.

What does data binding allow?
-----------------------------

Data binding in Channels works two ways:

* Outbound, where model changes made through Django are sent out to listening
  clients. This includes creation, update and deletion of instances.

* Inbound, where a standardised message format allow creation, update and
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
get started and likely close to what you want. Start off like this::

    from django.db import models
    from channels.binding.websockets import WebsocketBinding

    class IntegerValue(models.Model):

        name = models.CharField(max_length=100, unique=True)
        value = models.IntegerField(default=0)

    class IntegerValueBinding(WebsocketBinding):

        model = IntegerValue

        def group_names(self, instance, action):
            return ["intval-updates"]

        def has_permission(self, user, action, pk):
            return True

This defines a WebSocket binding - so it knows to send outgoing messages
formatted as JSON WebSocket frames - and provides the two methods you must
always provide:

* ``group_names`` returns a list of groups to send outbound updates to based
  on the model and action. For example, you could dispatch posts on different
  liveblogs to groups that included the parent blog ID in the name; here, we
  just use a fixed group name.

* ``has_permission`` returns if an inbound binding update is allowed to actually
  be carried out on the model. We've been very unsafe and made it always return
  ``True``, but here is where you would check against either Django's or your
  own permission system to see if the user is allowed that action.

For reference, ``action`` is always one of the unicode strings ``"create"``,
``"update"`` or ``"delete"``.

Just adding the binding like this in a place where it will be imported will
get outbound messages sending, but you still need a Consumer that will both
accept incoming binding updates and add people to the right Groups when they
connect. For that, you need the other part of the WebSocket binding module,
the demultiplexer::

    from channels.binding.websockets import WebsocketBindingDemultiplexer
    from .models import IntegerValueBinding

    class BindingConsumer(WebsocketBindingDemultiplexer):

        bindings = [
            IntegerValueBinding,
        ]

        def connection_groups(self):
            return ["intval-updates"]

This class needs two things set:

* ``bindings``, a list of Binding subclasses (the ones from before) of the
  models you want this to receive messages for. The socket will take care of
  looking for what model the incoming message is and giving it to the correct
  Binding.

* ``connection_groups``, a list of groups to put people in when they connect.
  This should match the logic of ``group_names`` on your binding - we've used
  our fixed group name again.

Tie that into your routing and you're ready to go::

    from channels import route_class
    from .consumers import BindingConsumer

    channel_routing = [
        route_class(BindingConsumer, path="^binding/"),
    ]


Frontend Considerations
-----------------------

Channels is a Python library, and so does not provide any JavaScript to tie
the binding into your JavaScript (though hopefully some will appear over time).
It's not very hard to write your own; messages are all in JSON format, and
have a key of ``action`` to tell you what's happening and ``model`` with the
Django label of the model they're on.


Custom Serialization/Protocols
------------------------------

Rather than inheriting from the ``WebsocketBinding``, you can inherit directly
from the base ``Binding`` class and implement serialization and deserialization
yourself. Until proper reference documentation for this is written, we
recommend looking at the source code in ``channels/bindings/base.py``; it's
reasonably well-commented.
