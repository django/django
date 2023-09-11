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
"""The Proxy implementation."""


class ProxyTypeFactory:
    """Factory for proxy types."""

    @staticmethod
    def make(ff_value, string):
        return {"ff_value": ff_value, "string": string}


class ProxyType:
    """Set of possible types of proxy.

    Each proxy type has 2 properties:    'ff_value' is value of Firefox
    profile preference,    'string' is id of proxy type.
    """

    DIRECT = ProxyTypeFactory.make(0, "DIRECT")  # Direct connection, no proxy (default on Windows).
    MANUAL = ProxyTypeFactory.make(1, "MANUAL")  # Manual proxy settings (e.g., for httpProxy).
    PAC = ProxyTypeFactory.make(2, "PAC")  # Proxy autoconfiguration from URL.
    RESERVED_1 = ProxyTypeFactory.make(3, "RESERVED1")  # Never used.
    AUTODETECT = ProxyTypeFactory.make(4, "AUTODETECT")  # Proxy autodetection (presumably with WPAD).
    SYSTEM = ProxyTypeFactory.make(5, "SYSTEM")  # Use system settings (default on Linux).
    UNSPECIFIED = ProxyTypeFactory.make(6, "UNSPECIFIED")  # Not initialized (for internal use).

    @classmethod
    def load(cls, value):
        if isinstance(value, dict) and "string" in value:
            value = value["string"]
        value = str(value).upper()
        for attr in dir(cls):
            attr_value = getattr(cls, attr)
            if isinstance(attr_value, dict) and "string" in attr_value and attr_value["string"] == value:
                return attr_value
        raise Exception(f"No proxy type is found for {value}")


class _ProxyTypeDescriptor:
    def __init__(self, name, p_type):
        self.name = name
        self.p_type = p_type

    def __get__(self, obj, cls):
        return getattr(obj, self.name)

    def __set__(self, obj, value):
        if self.name == "autodetect" and not isinstance(value, bool):
            raise ValueError("Autodetect proxy value needs to be a boolean")
        getattr(obj, "_verify_proxy_type_compatibility")(self.p_type)
        setattr(obj, "proxyType", self.p_type)
        setattr(obj, self.name, value)


class Proxy:
    """Proxy contains information about proxy type and necessary proxy
    settings."""

    proxyType = ProxyType.UNSPECIFIED
    autodetect = False
    ftpProxy = ""
    httpProxy = ""
    noProxy = ""
    proxyAutoconfigUrl = ""
    sslProxy = ""
    socksProxy = ""
    socksUsername = ""
    socksPassword = ""
    socksVersion = None

    # create descriptor type objects
    auto_detect = _ProxyTypeDescriptor("autodetect", ProxyType.AUTODETECT)
    """Gets and Sets `auto_detect`

    Usage
    -----
    - Get
        - `self.auto_detect`
    - Set
        - `self.auto_detect` = `value`

    Parameters
    ----------
    `value`: `str`
    """

    ftp_proxy = _ProxyTypeDescriptor("ftpProxy", ProxyType.MANUAL)
    """Gets and Sets `ftp_proxy`

    Usage
    -----
    - Get
        - `self.ftp_proxy`
    - Set
        - `self.ftp_proxy` = `value`

    Parameters
    ----------
    `value`: `str`
    """

    http_proxy = _ProxyTypeDescriptor("httpProxy", ProxyType.MANUAL)
    """Gets and Sets `http_proxy`

    Usage
    -----
    - Get
        - `self.http_proxy`
    - Set
        - `self.http_proxy` = `value`

    Parameters
    ----------
    `value`: `str`
    """

    no_proxy = _ProxyTypeDescriptor("noProxy", ProxyType.MANUAL)
    """Gets and Sets `no_proxy`

    Usage
    -----
    - Get
        - `self.no_proxy`
    - Set
        - `self.no_proxy` = `value`

    Parameters
    ----------
    `value`: `str`
    """

    proxy_autoconfig_url = _ProxyTypeDescriptor("proxyAutoconfigUrl", ProxyType.PAC)
    """Gets and Sets `proxy_autoconfig_url`

    Usage
    -----
    - Get
        - `self.proxy_autoconfig_url`
    - Set
        - `self.proxy_autoconfig_url` = `value`

    Parameter
    ---------
    `value`: `str`
    """

    ssl_proxy = _ProxyTypeDescriptor("sslProxy", ProxyType.MANUAL)
    """Gets and Sets `ssl_proxy`

    Usage
    -----
    - Get
        - `self.ssl_proxy`
    - Set
        - `self.ssl_proxy` = `value`

    Parameter
    ---------
    `value`: `str`
    """

    socks_proxy = _ProxyTypeDescriptor("socksProxy", ProxyType.MANUAL)
    """Gets and Sets `socks_proxy`

    Usage
    -----
    - Get
        - `self.sock_proxy`
    - Set
        - `self.socks_proxy` = `value`

    Parameter
    ---------
    `value`: `str`
    """

    socks_username = _ProxyTypeDescriptor("socksUsername", ProxyType.MANUAL)
    """Gets and Sets `socks_password`

    Usage
    -----
    - Get
        - `self.socks_password`
    - Set
        - `self.socks_password` = `value`

    Parameter
    ---------
    `value`: `str`
    """

    socks_password = _ProxyTypeDescriptor("socksPassword", ProxyType.MANUAL)
    """Gets and Sets `socks_password`

    Usage
    -----
    - Get
        - `self.socks_password`
    - Set
        - `self.socks_password` = `value`

    Parameter
    ---------
    `value`: `str`
    """

    socks_version = _ProxyTypeDescriptor("socksVersion", ProxyType.MANUAL)
    """Gets and Sets `socks_version`

    Usage
    -----
    - Get
        - `self.socks_version`
    - Set
        - `self.socks_version` = `value`

    Parameter
    ---------
    `value`: `str`
    """

    def __init__(self, raw=None):
        """Creates a new Proxy.

        :Args:
         - raw: raw proxy data. If None, default class values are used.
        """
        if raw:
            if "proxyType" in raw and raw["proxyType"]:
                self.proxy_type = ProxyType.load(raw["proxyType"])
            if "ftpProxy" in raw and raw["ftpProxy"]:
                self.ftp_proxy = raw["ftpProxy"]
            if "httpProxy" in raw and raw["httpProxy"]:
                self.http_proxy = raw["httpProxy"]
            if "noProxy" in raw and raw["noProxy"]:
                self.no_proxy = raw["noProxy"]
            if "proxyAutoconfigUrl" in raw and raw["proxyAutoconfigUrl"]:
                self.proxy_autoconfig_url = raw["proxyAutoconfigUrl"]
            if "sslProxy" in raw and raw["sslProxy"]:
                self.sslProxy = raw["sslProxy"]
            if "autodetect" in raw and raw["autodetect"]:
                self.auto_detect = raw["autodetect"]
            if "socksProxy" in raw and raw["socksProxy"]:
                self.socks_proxy = raw["socksProxy"]
            if "socksUsername" in raw and raw["socksUsername"]:
                self.socks_username = raw["socksUsername"]
            if "socksPassword" in raw and raw["socksPassword"]:
                self.socks_password = raw["socksPassword"]
            if "socksVersion" in raw and raw["socksVersion"]:
                self.socks_version = raw["socksVersion"]

    @property
    def proxy_type(self):
        """Returns proxy type as `ProxyType`."""
        return self.proxyType

    @proxy_type.setter
    def proxy_type(self, value) -> None:
        """Sets proxy type.

        :Args:
         - value: The proxy type.
        """
        self._verify_proxy_type_compatibility(value)
        self.proxyType = value

    def _verify_proxy_type_compatibility(self, compatible_proxy):
        if self.proxyType not in (ProxyType.UNSPECIFIED, compatible_proxy):
            raise ValueError(
                f"Specified proxy type ({compatible_proxy}) not compatible with current setting ({self.proxyType})"
            )

    def to_capabilities(self):
        proxy_caps = {"proxyType": self.proxyType["string"].lower()}
        proxies = [
            "autodetect",
            "ftpProxy",
            "httpProxy",
            "proxyAutoconfigUrl",
            "sslProxy",
            "noProxy",
            "socksProxy",
            "socksUsername",
            "socksPassword",
            "socksVersion",
        ]
        for proxy in proxies:
            attr_value = getattr(self, proxy)
            if attr_value:
                proxy_caps[proxy] = attr_value
        return proxy_caps
