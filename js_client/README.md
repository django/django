### Usage

Channels WebSocket wrapper.

To process messages:

```
import { WebSocketBridge } from 'django-channels'

const webSocketBridge = new WebSocketBridge();
webSocketBridge.connect();
webSocketBridge.listen(function(action, stream) {
  console.log(action, stream);
});
```

To send messages:

```
webSocketBridge.send({prop1: 'value1', prop2: 'value1'});

```

To demultiplex specific streams:

```
const webSocketBridge = new WebSocketBridge();
webSocketBridge.connect();
webSocketBridge.listen();
webSocketBridge.demultiplex('mystream', function(action, stream) {
  console.log(action, stream);
});
webSocketBridge.demultiplex('myotherstream', function(action, stream) {
  console.info(action, stream);
});
```

To send a message to a specific stream:

```
webSocketBridge.stream('mystream').send({prop1: 'value1', prop2: 'value1'})
```
