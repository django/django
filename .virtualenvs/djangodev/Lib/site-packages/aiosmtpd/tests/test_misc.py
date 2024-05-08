# Copyright 2014-2021 The aiosmtpd Developers
# SPDX-License-Identifier: Apache-2.0

"""Test other aspects of the server implementation."""

import asyncio
import warnings
from typing import Generator, Optional

import pytest

from aiosmtpd import _get_or_new_eventloop


@pytest.fixture(scope="module")
def close_existing_loop() -> Generator[Optional[asyncio.AbstractEventLoop], None, None]:
    loop: Optional[asyncio.AbstractEventLoop]
    with warnings.catch_warnings():
        warnings.filterwarnings("error")
        try:
            loop = asyncio.get_event_loop()
        except (DeprecationWarning, RuntimeError):
            loop = None
    if loop:
        loop.stop()
        loop.close()
        asyncio.set_event_loop(None)
        yield loop
    else:
        yield None


class TestInit:

    def test_create_new_if_none(self, close_existing_loop):
        old_loop = close_existing_loop
        loop: Optional[asyncio.AbstractEventLoop]
        loop = _get_or_new_eventloop()
        assert loop is not None
        assert loop is not old_loop
        assert isinstance(loop, asyncio.AbstractEventLoop)

    def test_not_create_new_if_exist(self, close_existing_loop):
        old_loop = close_existing_loop
        loop: Optional[asyncio.AbstractEventLoop]
        loop = asyncio.new_event_loop()
        assert loop is not old_loop
        asyncio.set_event_loop(loop)
        ret_loop = _get_or_new_eventloop()
        assert ret_loop is not old_loop
        assert ret_loop == loop
        assert ret_loop is loop
