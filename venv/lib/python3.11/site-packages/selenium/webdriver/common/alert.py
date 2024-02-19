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
"""The Alert implementation."""

from selenium.webdriver.common.utils import keys_to_typing
from selenium.webdriver.remote.command import Command


class Alert:
    """Allows to work with alerts.

    Use this class to interact with alert prompts.  It contains methods for dismissing,
    accepting, inputting, and getting text from alert prompts.

    Accepting / Dismissing alert prompts::

        Alert(driver).accept()
        Alert(driver).dismiss()

    Inputting a value into an alert prompt::

        name_prompt = Alert(driver)
        name_prompt.send_keys("Willian Shakesphere")
        name_prompt.accept()


    Reading a the text of a prompt for verification::

        alert_text = Alert(driver).text
        self.assertEqual("Do you wish to quit?", alert_text)
    """

    def __init__(self, driver) -> None:
        """Creates a new Alert.

        :Args:
         - driver: The WebDriver instance which performs user actions.
        """
        self.driver = driver

    @property
    def text(self) -> str:
        """Gets the text of the Alert."""
        return self.driver.execute(Command.W3C_GET_ALERT_TEXT)["value"]

    def dismiss(self) -> None:
        """Dismisses the alert available."""
        self.driver.execute(Command.W3C_DISMISS_ALERT)

    def accept(self) -> None:
        """Accepts the alert available.

        :Usage:
            ::

                Alert(driver).accept() # Confirm a alert dialog.
        """
        self.driver.execute(Command.W3C_ACCEPT_ALERT)

    def send_keys(self, keysToSend: str) -> None:
        """Send Keys to the Alert.

        :Args:
         - keysToSend: The text to be sent to Alert.
        """
        self.driver.execute(Command.W3C_SET_ALERT_VALUE, {"value": keys_to_typing(keysToSend), "text": keysToSend})
