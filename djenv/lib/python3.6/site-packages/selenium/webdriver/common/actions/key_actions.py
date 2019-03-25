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
from .interaction import Interaction, KEY
from .key_input import KeyInput
from ..utils import keys_to_typing


class KeyActions(Interaction):

    def __init__(self, source=None):
        if source is None:
            source = KeyInput(KEY)
        self.source = source
        super(KeyActions, self).__init__(source)

    def key_down(self, letter):
        return self._key_action("create_key_down", letter)

    def key_up(self, letter):
        return self._key_action("create_key_up", letter)

    def pause(self, duration=0):
        return self._key_action("create_pause", duration)

    def send_keys(self, text):
        if not isinstance(text, list):
            text = keys_to_typing(text)
        for letter in text:
            self.key_down(letter)
            self.key_up(letter)
        return self

    def _key_action(self, action, letter):
        meth = getattr(self.source, action)
        meth(letter)
        return self
