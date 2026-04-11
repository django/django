# Licensed to the Software Freedom Conservancy (SFC) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The SFC licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

import json
import logging
from ssl import CERT_NONE
from threading import Thread
from time import sleep

from websocket import WebSocketApp

from selenium.common import WebDriverException

logger = logging.getLogger(__name__)


class WebSocketConnection:
    _max_log_message_size = 9999

    def __init__(self, url, timeout, interval):
        if not isinstance(timeout, (int, float)) or timeout < 0:
            raise WebDriverException("timeout must be a positive number")
        if not isinstance(interval, (int, float)) or timeout < 0:
            raise WebDriverException("interval must be a positive number")

        self.url = url
        self.response_wait_timeout = timeout
        self.response_wait_interval = interval

        self.callbacks = {}
        self.session_id = None
        self._id = 0
        self._messages = {}
        self._started = False

        self._start_ws()
        self._wait_until(lambda: self._started)

    def close(self):
        self._ws_thread.join(timeout=self.response_wait_timeout)
        self._ws.close()
        self._started = False
        self._ws = None

    def execute(self, command):
        self._id += 1
        payload = self._serialize_command(command)
        payload["id"] = self._id
        if self.session_id:
            payload["sessionId"] = self.session_id

        data = json.dumps(payload)
        logger.debug(f"-> {data}"[: self._max_log_message_size])
        self._ws.send(data)

        current_id = self._id
        self._wait_until(lambda: current_id in self._messages)
        response = self._messages.pop(current_id)

        if "error" in response:
            error = response["error"]
            if "message" in response:
                error_msg = f"{error}: {response['message']}"
                raise WebDriverException(error_msg)
            else:
                raise WebDriverException(error)
        else:
            result = response["result"]
            return self._deserialize_result(result, command)

    def add_callback(self, event, callback):
        event_name = event.event_class
        if event_name not in self.callbacks:
            self.callbacks[event_name] = []

        def _callback(params):
            callback(event.from_json(params))

        self.callbacks[event_name].append(_callback)
        return id(_callback)

    on = add_callback

    def remove_callback(self, event, callback_id):
        event_name = event.event_class
        if event_name in self.callbacks:
            for callback in self.callbacks[event_name]:
                if id(callback) == callback_id:
                    self.callbacks[event_name].remove(callback)
                    return

    def _serialize_command(self, command):
        return next(command)

    def _deserialize_result(self, result, command):
        try:
            _ = command.send(result)
            raise WebDriverException("The command's generator function did not exit when expected!")
        except StopIteration as exit:
            return exit.value

    def _start_ws(self):
        def on_open(ws):
            self._started = True

        def on_message(ws, message):
            self._process_message(message)

        def on_error(ws, error):
            logger.debug(f"error: {error}")
            ws.close()

        def run_socket():
            if self.url.startswith("wss://"):
                self._ws.run_forever(sslopt={"cert_reqs": CERT_NONE}, suppress_origin=True)
            else:
                self._ws.run_forever(suppress_origin=True)

        self._ws = WebSocketApp(self.url, on_open=on_open, on_message=on_message, on_error=on_error)
        self._ws_thread = Thread(target=run_socket, daemon=True)
        self._ws_thread.start()

    def _process_message(self, message):
        message = json.loads(message)
        logger.debug(f"<- {message}"[: self._max_log_message_size])

        if "id" in message:
            self._messages[message["id"]] = message

        if "method" in message:
            params = message["params"]
            for callback in self.callbacks.get(message["method"], []):
                Thread(target=callback, args=(params,), daemon=True).start()

    def _wait_until(self, condition):
        timeout = self.response_wait_timeout
        interval = self.response_wait_interval

        while timeout > 0:
            result = condition()
            if result:
                return result
            else:
                timeout -= interval
                sleep(interval)
