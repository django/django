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

from enum import Enum


class LoginState(Enum):
    SIGN_IN = "SignIn"
    SIGN_UP = "SignUp"


class _AccountDescriptor:
    def __init__(self, name):
        self.name = name

    def __get__(self, obj, cls) -> str | None:
        return obj._account_data.get(self.name)

    def __set__(self, obj, value) -> None:
        raise AttributeError("Cannot set readonly attribute")


class Account:
    """Represents an account displayed in a FedCM account list.

    See: https://w3c-fedid.github.io/FedCM/#dictdef-identityprovideraccount
         https://w3c-fedid.github.io/FedCM/#webdriver-accountlist
    """

    account_id = _AccountDescriptor("accountId")
    email = _AccountDescriptor("email")
    name = _AccountDescriptor("name")
    given_name = _AccountDescriptor("givenName")
    picture_url = _AccountDescriptor("pictureUrl")
    idp_config_url = _AccountDescriptor("idpConfigUrl")
    terms_of_service_url = _AccountDescriptor("termsOfServiceUrl")
    privacy_policy_url = _AccountDescriptor("privacyPolicyUrl")
    login_state = _AccountDescriptor("loginState")

    def __init__(self, account_data):
        self._account_data = account_data
