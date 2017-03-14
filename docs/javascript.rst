Channels WebSocket wrapper
==========================

Channels ships with a javascript WebSocket wrapper to help you connect to your websocket
and send/receive messages.

First, you must include the javascript library in your template::

    {% load staticfiles %}

    {% static "channels/js/websocketbridge.js" %}

To process messages::
    
    const webSocketBridge = new channels.WebSocketBridge();
    webSocketBridge.connect();
    webSocketBridge.listen(function(action, stream) {
      console.log(action, stream);
    });

To send messages, use the `send` method::

    ```
    webSocketBridge.send({prop1: 'value1', prop2: 'value1'});

    ```

To demultiplex specific streams::

    webSocketBridge.connect();
    webSocketBridge.listen();
    webSocketBridge.demultiplex('mystream', function(action, stream) {
      console.log(action, stream);
    });
    webSocketBridge.demultiplex('myotherstream', function(action, stream) {
      console.info(action, stream);
    });


To send a message to a specific stream::

    webSocketBridge.stream('mystream').send({prop1: 'value1', prop2: 'value1'})

The library is also available as npm module, under the name
`django-channels <https://www.npmjs.com/package/django-channels>`_
