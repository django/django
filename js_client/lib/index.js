'use strict';

Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.WebSocketBridge = undefined;

var _extends = Object.assign || function (target) { for (var i = 1; i < arguments.length; i++) { var source = arguments[i]; for (var key in source) { if (Object.prototype.hasOwnProperty.call(source, key)) { target[key] = source[key]; } } } return target; };

var _createClass = function () { function defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if ("value" in descriptor) descriptor.writable = true; Object.defineProperty(target, descriptor.key, descriptor); } } return function (Constructor, protoProps, staticProps) { if (protoProps) defineProperties(Constructor.prototype, protoProps); if (staticProps) defineProperties(Constructor, staticProps); return Constructor; }; }();

var _reconnectingWebsocket = require('reconnecting-websocket');

var _reconnectingWebsocket2 = _interopRequireDefault(_reconnectingWebsocket);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

/**
 * Bridge between Channels and plain javascript.
 *
 * @example
 * const webSocketBridge = new WebSocketBridge();
 * webSocketBridge.connect();
 * webSocketBridge.listen(function(action, stream) {
 *   console.log(action, stream);
 * });
 */
var WebSocketBridge = function () {
  function WebSocketBridge(options) {
    _classCallCheck(this, WebSocketBridge);

    /**
     * The underlaying `ReconnectingWebSocket` instance.
     * 
     * @type {ReconnectingWebSocket}
     */
    this.socket = null;
    this.streams = {};
    this.default_cb = null;
    this.options = _extends({}, options);
  }

  /**
   * Connect to the websocket server
   *
   * @param      {String}  [url]     The url of the websocket. Defaults to
   * `window.location.host`
   * @param      {String[]|String}  [protocols] Optional string or array of protocols.
   * @param      {Object} options Object of options for [`reconnecting-websocket`](https://github.com/pladaria/reconnecting-websocket#configure).
   * @example
   * const webSocketBridge = new WebSocketBridge();
   * webSocketBridge.connect();
   */


  _createClass(WebSocketBridge, [{
    key: 'connect',
    value: function connect(url, protocols, options) {
      var _url = void 0;
      // Use wss:// if running on https://
      var scheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
      var base_url = scheme + '://' + window.location.host;
      if (url === undefined) {
        _url = base_url;
      } else {
        // Support relative URLs
        if (url[0] == '/') {
          _url = '' + base_url + url;
        } else {
          _url = url;
        }
      }
      // Some mobile devices (eg: HTC M8, SAMSUNG Galaxy S8) will get error code
      // [1006] during handshake if `protocols` is `undefined`.
      var _protocols = protocols === undefined ? '' : protocols;
      this.socket = new _reconnectingWebsocket2.default(_url, _protocols, options);
    }

    /**
     * Starts listening for messages on the websocket, demultiplexing if necessary.
     *
     * @param      {Function}  [cb]         Callback to be execute when a message
     * arrives. The callback will receive `action` and `stream` parameters
     *
     * @example
     * const webSocketBridge = new WebSocketBridge();
     * webSocketBridge.connect();
     * webSocketBridge.listen(function(action, stream) {
     *   console.log(action, stream);
     * });
     */

  }, {
    key: 'listen',
    value: function listen(cb) {
      var _this = this;

      this.default_cb = cb;
      this.socket.onmessage = function (event) {
        var msg = JSON.parse(event.data);
        var action = void 0;
        var stream = void 0;

        if (msg.stream !== undefined) {
          action = msg.payload;
          stream = msg.stream;
          var stream_cb = _this.streams[stream];
          stream_cb ? stream_cb(action, stream) : null;
        } else {
          action = msg;
          stream = null;
          _this.default_cb ? _this.default_cb(action, stream) : null;
        }
      };
    }

    /**
     * Adds a 'stream handler' callback. Messages coming from the specified stream
     * will call the specified callback.
     *
     * @param      {String}    stream  The stream name
     * @param      {Function}  cb      Callback to be execute when a message
     * arrives. The callback will receive `action` and `stream` parameters.
      * @example
     * const webSocketBridge = new WebSocketBridge();
     * webSocketBridge.connect();
     * webSocketBridge.listen();
     * webSocketBridge.demultiplex('mystream', function(action, stream) {
     *   console.log(action, stream);
     * });
     * webSocketBridge.demultiplex('myotherstream', function(action, stream) {
     *   console.info(action, stream);
     * });
     */

  }, {
    key: 'demultiplex',
    value: function demultiplex(stream, cb) {
      this.streams[stream] = cb;
    }

    /**
     * Sends a message to the reply channel.
     *
     * @param      {Object}  msg     The message
     *
     * @example
     * webSocketBridge.send({prop1: 'value1', prop2: 'value1'});
     */

  }, {
    key: 'send',
    value: function send(msg) {
      this.socket.send(JSON.stringify(msg));
    }

    /**
     * Returns an object to send messages to a specific stream
     *
     * @param      {String}  stream  The stream name
     * @return     {Object}  convenience object to send messages to `stream`.
     * @example
     * webSocketBridge.stream('mystream').send({prop1: 'value1', prop2: 'value1'})
     */

  }, {
    key: 'stream',
    value: function stream(_stream) {
      var _this2 = this;

      return {
        send: function send(action) {
          var msg = {
            stream: _stream,
            payload: action
          };
          _this2.socket.send(JSON.stringify(msg));
        }
      };
    }
  }]);

  return WebSocketBridge;
}();

exports.WebSocketBridge = WebSocketBridge;