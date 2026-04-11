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


from selenium.webdriver.remote.command import Command


class FedCM:
    def __init__(self, driver) -> None:
        self._driver = driver

    @property
    def title(self) -> str:
        """Gets the title of the dialog."""
        return self._driver.execute(Command.GET_FEDCM_TITLE)["value"].get("title")

    @property
    def subtitle(self) -> str | None:
        """Gets the subtitle of the dialog."""
        return self._driver.execute(Command.GET_FEDCM_TITLE)["value"].get("subtitle")

    @property
    def dialog_type(self) -> str:
        """Gets the type of the dialog currently being shown."""
        return self._driver.execute(Command.GET_FEDCM_DIALOG_TYPE).get("value")

    @property
    def account_list(self) -> list[dict]:
        """Gets the list of accounts shown in the dialog."""
        return self._driver.execute(Command.GET_FEDCM_ACCOUNT_LIST).get("value")

    def select_account(self, index: int) -> None:
        """Selects an account from the dialog by index."""
        self._driver.execute(Command.SELECT_FEDCM_ACCOUNT, {"accountIndex": index})

    def accept(self) -> None:
        """Clicks the continue button in the dialog."""
        self._driver.execute(Command.CLICK_FEDCM_DIALOG_BUTTON, {"dialogButton": "ConfirmIdpLoginContinue"})

    def dismiss(self) -> None:
        """Cancels/dismisses the FedCM dialog."""
        self._driver.execute(Command.CANCEL_FEDCM_DIALOG)

    def enable_delay(self) -> None:
        """Re-enables the promise rejection delay for FedCM."""
        self._driver.execute(Command.SET_FEDCM_DELAY, {"enabled": True})

    def disable_delay(self) -> None:
        """Disables the promise rejection delay for FedCM."""
        self._driver.execute(Command.SET_FEDCM_DELAY, {"enabled": False})

    def reset_cooldown(self) -> None:
        """Resets the FedCM dialog cooldown, allowing immediate retriggers."""
        self._driver.execute(Command.RESET_FEDCM_COOLDOWN)
