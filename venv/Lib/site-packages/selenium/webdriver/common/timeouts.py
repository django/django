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

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import TypedDict

    class JSONTimeouts(TypedDict, total=False):
        implicit: int
        pageLoad: int
        script: int

else:
    JSONTimeouts = dict[str, int]


class _TimeoutsDescriptor:
    """Get or set the value of the attributes listed below.

    _implicit_wait _page_load _script

    This does not set the value on the remote end.
    """

    def __init__(self, name):
        self.name = name

    def __get__(self, obj, cls) -> float:
        return getattr(obj, self.name) / 1000

    def __set__(self, obj, value) -> None:
        converted_value = getattr(obj, "_convert")(value)
        setattr(obj, self.name, converted_value)


class Timeouts:
    def __init__(self, implicit_wait: float = 0, page_load: float = 0, script: float = 0) -> None:
        """Create a new Timeouts object.

        This implements https://w3c.github.io/webdriver/#timeouts.

        Args:
            implicit_wait: Number of seconds to wait when searching for elements
                before throwing an error.
            page_load: Number of seconds to wait for a page load to complete
                before throwing an error.
            script: Number of seconds to wait for an asynchronous script to
                finish execution before throwing an error.
        """
        self._implicit_wait = self._convert(implicit_wait)
        self._page_load = self._convert(page_load)
        self._script = self._convert(script)

    # Creating descriptor objects
    implicit_wait = _TimeoutsDescriptor("_implicit_wait")
    """Number of seconds to wait when searching for elements.

    Note: This does not set the value on the remote end.
    """

    page_load = _TimeoutsDescriptor("_page_load")
    """Number of seconds to wait for the page to load.

    Note: This does not set the value on the remote end.
    """

    script = _TimeoutsDescriptor("_script")
    """Number of seconds to wait for an asynchronous script to finish execution.

    Note: This does not set the value on the remote end.
    """

    def _convert(self, timeout: float) -> int:
        if isinstance(timeout, (int, float)):
            return int(float(timeout) * 1000)
        raise TypeError("Timeouts can only be an int or a float")

    def _to_json(self) -> JSONTimeouts:
        timeouts: JSONTimeouts = {}
        if self._implicit_wait:
            timeouts["implicit"] = self._implicit_wait
        if self._page_load:
            timeouts["pageLoad"] = self._page_load
        if self._script:
            timeouts["script"] = self._script

        return timeouts
