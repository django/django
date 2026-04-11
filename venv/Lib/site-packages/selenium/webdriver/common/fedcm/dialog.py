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


from selenium.webdriver.common.fedcm.account import Account


class Dialog:
    """Represents a FedCM dialog that can be interacted with."""

    DIALOG_TYPE_ACCOUNT_LIST = "AccountChooser"
    DIALOG_TYPE_AUTO_REAUTH = "AutoReauthn"

    def __init__(self, driver) -> None:
        self._driver = driver

    @property
    def type(self) -> str | None:
        """Gets the type of the dialog currently being shown."""
        return self._driver.fedcm.dialog_type

    @property
    def title(self) -> str:
        """Gets the title of the dialog."""
        return self._driver.fedcm.title

    @property
    def subtitle(self) -> str | None:
        """Gets the subtitle of the dialog."""
        result = self._driver.fedcm.subtitle
        return result.get("subtitle") if result else None

    def get_accounts(self) -> list[Account]:
        """Gets the list of accounts shown in the dialog."""
        accounts = self._driver.fedcm.account_list
        return [Account(account) for account in accounts]

    def select_account(self, index: int) -> None:
        """Selects an account from the dialog by index."""
        self._driver.fedcm.select_account(index)

    def accept(self) -> None:
        """Clicks the continue button in the dialog."""
        self._driver.fedcm.accept()

    def dismiss(self) -> None:
        """Cancels/dismisses the dialog."""
        self._driver.fedcm.dismiss()
