# Copyright 2014-2021 The aiosmtpd Developers
# SPDX-License-Identifier: Apache-2.0
import asyncio
import warnings


__version__ = "1.4.5"


def _get_or_new_eventloop() -> asyncio.AbstractEventLoop:
    loop = None
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        try:
            loop = asyncio.get_event_loop()
        except (DeprecationWarning, RuntimeError):  # pragma: py-lt-310
            if loop is None:  # pragma: py-lt-312
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
    assert isinstance(loop, asyncio.AbstractEventLoop)
    return loop
