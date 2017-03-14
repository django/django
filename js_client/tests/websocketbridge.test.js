import { WebSocket, Server } from 'mock-socket';
import { WebSocketBridge } from '../src/';



describe('WebSocketBridge', () => {
  const mockServer = new Server('ws://localhost');
  const serverReceivedMessage = jest.fn();
  mockServer.on('message', serverReceivedMessage);

  beforeEach(() => {
    serverReceivedMessage.mockReset();
  });

  it('Connects', () => {
    const webSocketBridge = new WebSocketBridge();
    webSocketBridge.connect('ws://localhost');
  });
  it('Processes messages', () => {
    const webSocketBridge = new WebSocketBridge();
    const myMock = jest.fn();

    webSocketBridge.connect('ws://localhost');
    webSocketBridge.listen(myMock);

    mockServer.send('{"type": "test", "payload": "message 1"}');
    mockServer.send('{"type": "test", "payload": "message 2"}');

    expect(myMock.mock.calls.length).toBe(2);
    expect(myMock.mock.calls[0][0]).toEqual({"type": "test", "payload": "message 1"});
    expect(myMock.mock.calls[0][1]).toBe(null);
  });
  it('Ignores multiplexed messages for unregistered streams', () => {
    const webSocketBridge = new WebSocketBridge();
    const myMock = jest.fn();

    webSocketBridge.connect('ws://localhost');
    webSocketBridge.listen(myMock);

    mockServer.send('{"stream": "stream1", "payload": {"type": "test", "payload": "message 1"}}');
    expect(myMock.mock.calls.length).toBe(0);

  });
  it('Demultiplexes messages only when they have a stream', () => {
    const webSocketBridge = new WebSocketBridge();
    const myMock = jest.fn();
    const myMock2 = jest.fn();
    const myMock3 = jest.fn();

    webSocketBridge.connect('ws://localhost');
    webSocketBridge.listen(myMock);
    webSocketBridge.demultiplex('stream1', myMock2);
    webSocketBridge.demultiplex('stream2', myMock3);

    mockServer.send('{"type": "test", "payload": "message 1"}');
    expect(myMock.mock.calls.length).toBe(1);
    expect(myMock2.mock.calls.length).toBe(0);
    expect(myMock3.mock.calls.length).toBe(0);

    mockServer.send('{"stream": "stream1", "payload": {"type": "test", "payload": "message 1"}}');

    expect(myMock.mock.calls.length).toBe(1);
    expect(myMock2.mock.calls.length).toBe(1);
    expect(myMock3.mock.calls.length).toBe(0);

    expect(myMock2.mock.calls[0][0]).toEqual({"type": "test", "payload": "message 1"});
    expect(myMock2.mock.calls[0][1]).toBe("stream1");

    mockServer.send('{"stream": "stream2", "payload": {"type": "test", "payload": "message 2"}}');

    expect(myMock.mock.calls.length).toBe(1);
    expect(myMock2.mock.calls.length).toBe(1);
    expect(myMock3.mock.calls.length).toBe(1);

    expect(myMock3.mock.calls[0][0]).toEqual({"type": "test", "payload": "message 2"});
    expect(myMock3.mock.calls[0][1]).toBe("stream2");
  });
  it('Demultiplexes messages', () => {
    const webSocketBridge = new WebSocketBridge();
    const myMock = jest.fn();
    const myMock2 = jest.fn();

    webSocketBridge.connect('ws://localhost');
    webSocketBridge.listen();

    webSocketBridge.demultiplex('stream1', myMock);
    webSocketBridge.demultiplex('stream2', myMock2);

    mockServer.send('{"type": "test", "payload": "message 1"}');
    mockServer.send('{"type": "test", "payload": "message 2"}');

    expect(myMock.mock.calls.length).toBe(0);
    expect(myMock2.mock.calls.length).toBe(0);

    mockServer.send('{"stream": "stream1", "payload": {"type": "test", "payload": "message 1"}}');

    expect(myMock.mock.calls.length).toBe(1);

    expect(myMock2.mock.calls.length).toBe(0);

    expect(myMock.mock.calls[0][0]).toEqual({"type": "test", "payload": "message 1"});
    expect(myMock.mock.calls[0][1]).toBe("stream1");

    mockServer.send('{"stream": "stream2", "payload": {"type": "test", "payload": "message 2"}}');

    expect(myMock.mock.calls.length).toBe(1);
    expect(myMock2.mock.calls.length).toBe(1);


    expect(myMock2.mock.calls[0][0]).toEqual({"type": "test", "payload": "message 2"});
    expect(myMock2.mock.calls[0][1]).toBe("stream2");

  });
  it('Sends messages', () => {
    const webSocketBridge = new WebSocketBridge();

    webSocketBridge.connect('ws://localhost');
    webSocketBridge.send({"type": "test", "payload": "message 1"});

    expect(serverReceivedMessage.mock.calls.length).toBe(1);
    expect(serverReceivedMessage.mock.calls[0][0]).toEqual(JSON.stringify({"type": "test", "payload": "message 1"}));
  });
  it('Multiplexes messages', () => {
    const webSocketBridge = new WebSocketBridge();

    webSocketBridge.connect('ws://localhost');
    webSocketBridge.stream('stream1').send({"type": "test", "payload": "message 1"});

    expect(serverReceivedMessage.mock.calls.length).toBe(1);
    expect(serverReceivedMessage.mock.calls[0][0]).toEqual(JSON.stringify({
      "stream": "stream1",
      "payload": {
        "type": "test", "payload": "message 1",
      },
    }));
  });
});
