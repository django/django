"""Simple requests package loader"""

from __future__ import annotations

import warnings
from typing import Any
from urllib.parse import urlsplit

import requests
from urllib3.exceptions import InsecureRequestWarning

import sphinx

_USER_AGENT = (f'Mozilla/5.0 (X11; Linux x86_64; rv:100.0) Gecko/20100101 Firefox/100.0 '
               f'Sphinx/{sphinx.__version__}')


def _get_tls_cacert(url: str, certs: str | dict[str, str] | None) -> str | bool:
    """Get additional CA cert for a specific URL."""
    if not certs:
        return True
    elif isinstance(certs, (str, tuple)):
        return certs
    else:
        hostname = urlsplit(url).netloc
        if '@' in hostname:
            _, hostname = hostname.split('@', 1)

        return certs.get(hostname, True)


def get(url: str, **kwargs: Any) -> requests.Response:
    """Sends a GET request like requests.get().

    This sets up User-Agent header and TLS verification automatically."""
    with _Session() as session:
        return session.get(url, **kwargs)


def head(url: str, **kwargs: Any) -> requests.Response:
    """Sends a HEAD request like requests.head().

    This sets up User-Agent header and TLS verification automatically."""
    with _Session() as session:
        return session.head(url, **kwargs)


class _Session(requests.Session):
    def request(  # type: ignore[override]
        self, method: str, url: str,
        _user_agent: str = '',
        _tls_info: tuple[bool, str | dict[str, str] | None] = (),  # type: ignore[assignment]
        **kwargs: Any,
    ) -> requests.Response:
        """Sends a request with an HTTP verb and url.

        This sets up User-Agent header and TLS verification automatically."""
        headers = kwargs.setdefault('headers', {})
        headers.setdefault('User-Agent', _user_agent or _USER_AGENT)
        if _tls_info:
            tls_verify, tls_cacerts = _tls_info
            verify = bool(kwargs.get('verify', tls_verify))
            kwargs.setdefault('verify', verify and _get_tls_cacert(url, tls_cacerts))
        else:
            verify = kwargs.get('verify', True)

        if verify:
            return super().request(method, url, **kwargs)

        with warnings.catch_warnings():
            # ignore InsecureRequestWarning if verify=False
            warnings.filterwarnings("ignore", category=InsecureRequestWarning)
            return super().request(method, url, **kwargs)
