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

    Each proxy type has 2 properties: 'ff_value' is value of Firefox
    profile preference, 'string' is id of proxy type.
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
    """Proxy configuration containing proxy type and necessary proxy settings."""

    proxyType = ProxyType.UNSPECIFIED
    autodetect = False
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
    """Proxy autodetection setting (boolean)."""

    http_proxy = _ProxyTypeDescriptor("httpProxy", ProxyType.MANUAL)
    """HTTP proxy address."""

    no_proxy = _ProxyTypeDescriptor("noProxy", ProxyType.MANUAL)
    """Addresses to bypass proxy."""

    proxy_autoconfig_url = _ProxyTypeDescriptor("proxyAutoconfigUrl", ProxyType.PAC)
    """Proxy autoconfiguration URL."""

    ssl_proxy = _ProxyTypeDescriptor("sslProxy", ProxyType.MANUAL)
    """SSL proxy address."""

    socks_proxy = _ProxyTypeDescriptor("socksProxy", ProxyType.MANUAL)
    """SOCKS proxy address."""

    socks_username = _ProxyTypeDescriptor("socksUsername", ProxyType.MANUAL)
    """SOCKS proxy username."""

    socks_password = _ProxyTypeDescriptor("socksPassword", ProxyType.MANUAL)
    """SOCKS proxy password."""

    socks_version = _ProxyTypeDescriptor("socksVersion", ProxyType.MANUAL)
    """SOCKS proxy version."""

    def __init__(self, raw: dict | None = None):
        """Creates a new Proxy.

        Args:
            raw: Raw proxy data. If None, default class values are used.
        """
        if raw is None:
            return
        if not isinstance(raw, dict):
            raise TypeError(f"`raw` must be a dict, got {type(raw)}")
        if raw.get("proxyType"):
            self.proxy_type = ProxyType.load(raw["proxyType"])
        if raw.get("httpProxy"):
            self.http_proxy = raw["httpProxy"]
        if raw.get("noProxy"):
            self.no_proxy = raw["noProxy"]
        if raw.get("proxyAutoconfigUrl"):
            self.proxy_autoconfig_url = raw["proxyAutoconfigUrl"]
        if raw.get("sslProxy"):
            self.sslProxy = raw["sslProxy"]
        if raw.get("autodetect"):
            self.auto_detect = raw["autodetect"]
        if raw.get("socksProxy"):
            self.socks_proxy = raw["socksProxy"]
        if raw.get("socksUsername"):
            self.socks_username = raw["socksUsername"]
        if raw.get("socksPassword"):
            self.socks_password = raw["socksPassword"]
        if raw.get("socksVersion"):
            self.socks_version = raw["socksVersion"]

    @property
    def proxy_type(self):
        """Returns proxy type as `ProxyType`."""
        return self.proxyType

    @proxy_type.setter
    def proxy_type(self, value) -> None:
        """Sets proxy type.

        Args:
            value: The proxy type.
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

    def to_bidi_dict(self) -> dict:
        """Convert proxy settings to BiDi format.

        Returns:
            Proxy configuration in BiDi format.
        """
        proxy_type = self.proxyType["string"].lower()
        result = {"proxyType": proxy_type}

        if proxy_type == "manual":
            if self.httpProxy:
                result["httpProxy"] = self.httpProxy
            if self.sslProxy:
                result["sslProxy"] = self.sslProxy
            if self.socksProxy:
                result["socksProxy"] = self.socksProxy
            if self.socksVersion is not None:
                result["socksVersion"] = self.socksVersion
            if self.noProxy:
                # Convert comma-separated string to list
                if isinstance(self.noProxy, str):
                    result["noProxy"] = [host.strip() for host in self.noProxy.split(",") if host.strip()]
                elif isinstance(self.noProxy, list):
                    if not all(isinstance(h, str) for h in self.noProxy):
                        raise TypeError("no_proxy list must contain only strings")
                    result["noProxy"] = self.noProxy
                else:
                    raise TypeError("no_proxy must be a comma-separated string or a list of strings")

        elif proxy_type == "pac":
            if self.proxyAutoconfigUrl:
                result["proxyAutoconfigUrl"] = self.proxyAutoconfigUrl

        return result
