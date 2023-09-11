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

from hashlib import md5 as md5_hash

from ..common.by import By
from .command import Command


class ShadowRoot:
    # TODO: We should look and see  how we can create a search context like Java/.NET

    def __init__(self, session, id_) -> None:
        self.session = session
        self._id = id_

    def __eq__(self, other_shadowroot) -> bool:
        return self._id == other_shadowroot._id

    def __hash__(self) -> int:
        return int(md5_hash(self._id.encode("utf-8")).hexdigest(), 16)

    def __repr__(self) -> str:
        return '<{0.__module__}.{0.__name__} (session="{1}", element="{2}")>'.format(
            type(self), self.session.session_id, self._id
        )

    def find_element(self, by: str = By.ID, value: str = None):
        if by == By.ID:
            by = By.CSS_SELECTOR
            value = f'[id="{value}"]'
        elif by == By.CLASS_NAME:
            by = By.CSS_SELECTOR
            value = f".{value}"
        elif by == By.NAME:
            by = By.CSS_SELECTOR
            value = f'[name="{value}"]'

        return self._execute(Command.FIND_ELEMENT_FROM_SHADOW_ROOT, {"using": by, "value": value})["value"]

    def find_elements(self, by: str = By.ID, value: str = None):
        if by == By.ID:
            by = By.CSS_SELECTOR
            value = f'[id="{value}"]'
        elif by == By.CLASS_NAME:
            by = By.CSS_SELECTOR
            value = f".{value}"
        elif by == By.NAME:
            by = By.CSS_SELECTOR
            value = f'[name="{value}"]'

        return self._execute(Command.FIND_ELEMENTS_FROM_SHADOW_ROOT, {"using": by, "value": value})["value"]

    # Private Methods
    def _execute(self, command, params=None):
        """Executes a command against the underlying HTML element.

        Args:
          command: The name of the command to _execute as a string.
          params: A dictionary of named parameters to send with the command.

        Returns:
          The command's JSON response loaded into a dictionary object.
        """
        if not params:
            params = {}
        params["shadowId"] = self._id
        return self.session.execute(command, params)
