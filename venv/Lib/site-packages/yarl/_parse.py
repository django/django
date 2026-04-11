"""URL parsing utilities."""

import re
import unicodedata
from functools import lru_cache
from typing import Union
from urllib.parse import scheme_chars, uses_netloc

from ._quoters import QUOTER, UNQUOTER_PLUS

# Leading and trailing C0 control and space to be stripped per WHATWG spec.
# == "".join([chr(i) for i in range(0, 0x20 + 1)])
WHATWG_C0_CONTROL_OR_SPACE = (
    "\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\x0c\r\x0e\x0f\x10"
    "\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f "
)

# Unsafe bytes to be removed per WHATWG spec
UNSAFE_URL_BYTES_TO_REMOVE = ["\t", "\r", "\n"]
USES_AUTHORITY = frozenset(uses_netloc)

SplitURLType = tuple[str, str, str, str, str]


def split_url(url: str) -> SplitURLType:
    """Split URL into parts."""
    # Adapted from urllib.parse.urlsplit
    # Only lstrip url as some applications rely on preserving trailing space.
    # (https://url.spec.whatwg.org/#concept-basic-url-parser would strip both)
    url = url.lstrip(WHATWG_C0_CONTROL_OR_SPACE)
    for b in UNSAFE_URL_BYTES_TO_REMOVE:
        if b in url:
            url = url.replace(b, "")

    scheme = netloc = query = fragment = ""
    i = url.find(":")
    if i > 0 and url[0] in scheme_chars:
        for c in url[1:i]:
            if c not in scheme_chars:
                break
        else:
            scheme, url = url[:i].lower(), url[i + 1 :]
    has_hash = "#" in url
    has_question_mark = "?" in url
    if url[:2] == "//":
        delim = len(url)  # position of end of domain part of url, default is end
        if has_hash and has_question_mark:
            delim_chars = "/?#"
        elif has_question_mark:
            delim_chars = "/?"
        elif has_hash:
            delim_chars = "/#"
        else:
            delim_chars = "/"
        for c in delim_chars:  # look for delimiters; the order is NOT important
            wdelim = url.find(c, 2)  # find first of this delim
            if wdelim >= 0 and wdelim < delim:  # if found
                delim = wdelim  # use earliest delim position
        netloc = url[2:delim]
        url = url[delim:]
        has_left_bracket = "[" in netloc
        has_right_bracket = "]" in netloc
        if (has_left_bracket and not has_right_bracket) or (
            has_right_bracket and not has_left_bracket
        ):
            raise ValueError("Invalid IPv6 URL")
        if has_left_bracket:
            bracketed_host = netloc.partition("[")[2].partition("]")[0]
            # Valid bracketed hosts are defined in
            # https://www.rfc-editor.org/rfc/rfc3986#page-49
            # https://url.spec.whatwg.org/
            if bracketed_host and bracketed_host[0] == "v":
                if not re.match(r"\Av[a-fA-F0-9]+\..+\Z", bracketed_host):
                    raise ValueError("IPvFuture address is invalid")
            elif ":" not in bracketed_host:
                raise ValueError("The IPv6 content between brackets is not valid")
    if has_hash:
        url, _, fragment = url.partition("#")
    if has_question_mark:
        url, _, query = url.partition("?")
    if netloc and not netloc.isascii():
        _check_netloc(netloc)
    return scheme, netloc, url, query, fragment


def _check_netloc(netloc: str) -> None:
    # Adapted from urllib.parse._checknetloc
    # looking for characters like \u2100 that expand to 'a/c'
    # IDNA uses NFKC equivalence, so normalize for this check

    # ignore characters already included
    # but not the surrounding text
    n = netloc.replace("@", "").replace(":", "").replace("#", "").replace("?", "")
    normalized_netloc = unicodedata.normalize("NFKC", n)
    if n == normalized_netloc:
        return
    # Note that there are no unicode decompositions for the character '@' so
    # its currently impossible to have test coverage for this branch, however if the
    # one should be added in the future we want to make sure its still checked.
    for c in "/?#@:":  # pragma: no branch
        if c in normalized_netloc:
            raise ValueError(
                f"netloc '{netloc}' contains invalid "
                "characters under NFKC normalization"
            )


@lru_cache  # match the same size as urlsplit
def split_netloc(
    netloc: str,
) -> tuple[Union[str, None], Union[str, None], Union[str, None], Union[int, None]]:
    """Split netloc into username, password, host and port."""
    if "@" not in netloc:
        username: Union[str, None] = None
        password: Union[str, None] = None
        hostinfo = netloc
    else:
        userinfo, _, hostinfo = netloc.rpartition("@")
        username, have_password, password = userinfo.partition(":")
        if not have_password:
            password = None

    if "[" in hostinfo:
        _, _, bracketed = hostinfo.partition("[")
        hostname, _, port_str = bracketed.partition("]")
        _, _, port_str = port_str.partition(":")
    else:
        hostname, _, port_str = hostinfo.partition(":")

    if not port_str:
        return username or None, password, hostname or None, None

    try:
        port = int(port_str)
    except ValueError:
        raise ValueError("Invalid URL: port can't be converted to integer")
    if not (0 <= port <= 65535):
        raise ValueError("Port out of range 0-65535")
    return username or None, password, hostname or None, port


def unsplit_result(
    scheme: str, netloc: str, url: str, query: str, fragment: str
) -> str:
    """Unsplit a URL without any normalization."""
    if netloc or (scheme and scheme in USES_AUTHORITY) or url[:2] == "//":
        if url and url[:1] != "/":
            url = f"{scheme}://{netloc}/{url}" if scheme else f"{scheme}:{url}"
        else:
            url = f"{scheme}://{netloc}{url}" if scheme else f"//{netloc}{url}"
    elif scheme:
        url = f"{scheme}:{url}"
    if query:
        url = f"{url}?{query}"
    return f"{url}#{fragment}" if fragment else url


@lru_cache  # match the same size as urlsplit
def make_netloc(
    user: Union[str, None],
    password: Union[str, None],
    host: Union[str, None],
    port: Union[int, None],
    encode: bool = False,
) -> str:
    """Make netloc from parts.

    The user and password are encoded if encode is True.

    The host must already be encoded with _encode_host.
    """
    if host is None:
        return ""
    ret = host
    if port is not None:
        ret = f"{ret}:{port}"
    if user is None and password is None:
        return ret
    if password is not None:
        if not user:
            user = ""
        elif encode:
            user = QUOTER(user)
        if encode:
            password = QUOTER(password)
        user = f"{user}:{password}"
    elif user and encode:
        user = QUOTER(user)
    return f"{user}@{ret}" if user else ret


def query_to_pairs(query_string: str) -> list[tuple[str, str]]:
    """Parse a query given as a string argument.

    Works like urllib.parse.parse_qsl with keep empty values.
    """
    pairs: list[tuple[str, str]] = []
    if not query_string:
        return pairs
    for k_v in query_string.split("&"):
        k, _, v = k_v.partition("=")
        pairs.append((UNQUOTER_PLUS(k), UNQUOTER_PLUS(v)))
    return pairs
