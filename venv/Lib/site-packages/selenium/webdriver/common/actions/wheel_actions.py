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


from selenium.webdriver.common.actions.interaction import WHEEL, Interaction
from selenium.webdriver.common.actions.wheel_input import WheelInput


class WheelActions(Interaction):
    def __init__(self, source: WheelInput | None = None):
        if source is None:
            source = WheelInput(WHEEL)
        super().__init__(source)

    def pause(self, duration: float = 0):
        self.source.create_pause(duration)
        return self

    def scroll(self, x=0, y=0, delta_x=0, delta_y=0, duration=0, origin="viewport"):
        self.source.create_scroll(x, y, delta_x, delta_y, duration, origin)
        return self
