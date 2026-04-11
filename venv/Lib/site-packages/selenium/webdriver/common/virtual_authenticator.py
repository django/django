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

import functools
from base64 import urlsafe_b64decode, urlsafe_b64encode
from enum import Enum
from typing import Any


class Protocol(str, Enum):
    """Protocol to communicate with the authenticator."""

    CTAP2 = "ctap2"
    U2F = "ctap1/u2f"


class Transport(str, Enum):
    """Transport method to communicate with the authenticator."""

    BLE = "ble"
    USB = "usb"
    NFC = "nfc"
    INTERNAL = "internal"


class VirtualAuthenticatorOptions:
    # These are so unnecessary but are now public API so we can't remove them without deprecating first.
    # These should not be class level state in here.
    Protocol = Protocol
    Transport = Transport

    def __init__(
        self,
        protocol: str = Protocol.CTAP2,
        transport: str = Transport.USB,
        has_resident_key: bool = False,
        has_user_verification: bool = False,
        is_user_consenting: bool = True,
        is_user_verified: bool = False,
    ) -> None:
        """Constructor.

        Initialize VirtualAuthenticatorOptions object.
        """
        self.protocol: str = protocol
        self.transport: str = transport
        self.has_resident_key: bool = has_resident_key
        self.has_user_verification: bool = has_user_verification
        self.is_user_consenting: bool = is_user_consenting
        self.is_user_verified: bool = is_user_verified

    def to_dict(self) -> dict[str, str | bool]:
        return {
            "protocol": self.protocol,
            "transport": self.transport,
            "hasResidentKey": self.has_resident_key,
            "hasUserVerification": self.has_user_verification,
            "isUserConsenting": self.is_user_consenting,
            "isUserVerified": self.is_user_verified,
        }


class Credential:
    def __init__(
        self,
        credential_id: bytes,
        is_resident_credential: bool,
        rp_id: str | None,
        user_handle: bytes | None,
        private_key: bytes,
        sign_count: int,
    ):
        """Constructor. A credential stored in a virtual authenticator.

        https://w3c.github.io/webauthn/#credential-parameters.

        Args:
            credential_id (bytes): Unique base64 encoded string.
            is_resident_credential (bool): Whether the credential is client-side discoverable.
            rp_id (str): Relying party identifier.
            user_handle (bytes): userHandle associated to the credential. Must be Base64 encoded string. Can be None.
            private_key (bytes): Base64 encoded PKCS#8 private key.
            sign_count (int): initial value for a signature counter.
        """
        self._id = credential_id
        self._is_resident_credential = is_resident_credential
        self._rp_id = rp_id
        self._user_handle = user_handle
        self._private_key = private_key
        self._sign_count = sign_count

    @property
    def id(self) -> str:
        return urlsafe_b64encode(self._id).decode()

    @property
    def is_resident_credential(self) -> bool:
        return self._is_resident_credential

    @property
    def rp_id(self) -> str | None:
        return self._rp_id

    @property
    def user_handle(self) -> str | None:
        if self._user_handle:
            return urlsafe_b64encode(self._user_handle).decode()
        return None

    @property
    def private_key(self) -> str:
        return urlsafe_b64encode(self._private_key).decode()

    @property
    def sign_count(self) -> int:
        return self._sign_count

    @classmethod
    def create_non_resident_credential(cls, id: bytes, rp_id: str, private_key: bytes, sign_count: int) -> "Credential":
        """Creates a non-resident (i.e. stateless) credential.

        Args:
            id (bytes): Unique base64 encoded string.
            rp_id (str): Relying party identifier.
            private_key (bytes): Base64 encoded PKCS
            sign_count (int): initial value for a signature counter.

        Returns:
            Credential: A non-resident credential.
        """
        return cls(id, False, rp_id, None, private_key, sign_count)

    @classmethod
    def create_resident_credential(
        cls, id: bytes, rp_id: str, user_handle: bytes | None, private_key: bytes, sign_count: int
    ) -> "Credential":
        """Creates a resident (i.e. stateful) credential.

        Args:
            id (bytes): Unique base64 encoded string.
            rp_id (str): Relying party identifier.
            user_handle (bytes): userHandle associated to the credential. Must be Base64 encoded string.
            private_key (bytes): Base64 encoded PKCS
            sign_count (int): initial value for a signature counter.

        Returns:
            Credential: A resident credential.
        """
        return cls(id, True, rp_id, user_handle, private_key, sign_count)

    def to_dict(self) -> dict[str, Any]:
        credential_data = {
            "credentialId": self.id,
            "isResidentCredential": self._is_resident_credential,
            "rpId": self.rp_id,
            "privateKey": self.private_key,
            "signCount": self.sign_count,
        }

        if self.user_handle:
            credential_data["userHandle"] = self.user_handle

        return credential_data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Credential":
        _id = urlsafe_b64decode(f"{data['credentialId']}==")
        is_resident_credential = bool(data["isResidentCredential"])
        rp_id = data.get("rpId", None)
        private_key = urlsafe_b64decode(f"{data['privateKey']}==")
        sign_count = int(data["signCount"])
        user_handle = urlsafe_b64decode(f"{data['userHandle']}==") if data.get("userHandle", None) else None

        return cls(_id, is_resident_credential, rp_id, user_handle, private_key, sign_count)

    def __str__(self) -> str:
        return f"Credential(id={self.id}, is_resident_credential={self.is_resident_credential}, rp_id={self.rp_id},\
            user_handle={self.user_handle}, private_key={self.private_key}, sign_count={self.sign_count})"


def required_chromium_based_browser(func):
    """Decorator to ensure that the client used is a chromium-based browser."""

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        assert self.caps["browserName"].lower() not in [
            "firefox",
            "safari",
        ], "This only currently works in Chromium based browsers"
        return func(self, *args, **kwargs)

    return wrapper


def required_virtual_authenticator(func):
    """Decorator to ensure that the function is called with a virtual authenticator."""

    @functools.wraps(func)
    @required_chromium_based_browser
    def wrapper(self, *args, **kwargs):
        if not self.virtual_authenticator_id:
            raise ValueError("This function requires a virtual authenticator to be set.")
        return func(self, *args, **kwargs)

    return wrapper
