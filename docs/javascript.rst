Channels WebSocket wrapper
==========================

Channels ships with a javascript WebSocket wrapper to help you connect to your websocket
and send/receive messages.

First, you must include the javascript library in your template; if you're using
Django's staticfiles, this is as easy as::

    {% load staticfiles %}

    {% static "channels/js/websocketbridge.js" %}

If you are using an alternative method of serving static files, the compiled
source code is located at ``channels/static/channels/js/websocketbridge.js`` in
a Channels installation. We compile the file for you each release; it's ready
to serve as-is.

The library is deliberately quite low-level and generic; it's designed to
be compatible with any JavaScript code or framework, so you can build more
specific integration on top of it.

To process messages::

    const webSocketBridge = new channels.WebSocketBridge();
    webSocketBridge.connect('/ws/');
    webSocketBridge.listen(function(action, stream) {
      console.log(action, stream);
    });

To send messages, use the `send` method::

    webSocketBridge.send({prop1: 'value1', prop2: 'value1'});

To demultiplex specific streams::

    webSocketBridge.connect();
    webSocketBridge.listen('/ws/');
    webSocketBridge.demultiplex('mystream', function(action, stream) {
      console.log(action, stream);
    });
    webSocketBridge.demultiplex('myotherstream', function(action, stream) {
      console.info(action, stream);
    });

To send a message to a specific stream::

    webSocketBridge.stream('mystream').send({prop1: 'value1', prop2: 'value1'})

The `WebSocketBridge` instance exposes the underlaying `ReconnectingWebSocket` as the `socket` property. You can use this property to add any custom behavior. For example::

    webSocketBridge.socket.addEventListener('open', function() {
        console.log("Connected to WebSocket");
    })


The library is also available as a npm module, under the name
`django-channels <https://www.npmjs.com/package/django-channels>`_
