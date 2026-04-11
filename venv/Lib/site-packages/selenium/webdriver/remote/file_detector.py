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

from abc import ABCMeta, abstractmethod
from contextlib import suppress
from pathlib import Path

from selenium.webdriver.common.utils import keys_to_typing


class FileDetector(metaclass=ABCMeta):
    """Identify whether a sequence of characters represents a file path."""

    @abstractmethod
    def is_local_file(self, *keys: str | int | float) -> str | None:
        raise NotImplementedError


class UselessFileDetector(FileDetector):
    """A file detector that never finds anything."""

    def is_local_file(self, *keys: str | int | float) -> str | None:
        return None


class LocalFileDetector(FileDetector):
    """Detects files on the local disk."""

    def is_local_file(self, *keys: str | int | float) -> str | None:
        file_path = "".join(keys_to_typing(keys))

        with suppress(OSError):
            if Path(file_path).is_file():
                return file_path
        return None
