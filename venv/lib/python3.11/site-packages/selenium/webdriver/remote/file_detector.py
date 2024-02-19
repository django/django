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

from abc import ABCMeta
from abc import abstractmethod
from contextlib import suppress
from pathlib import Path
from typing import Optional

from selenium.types import AnyKey
from selenium.webdriver.common.utils import keys_to_typing


class FileDetector(metaclass=ABCMeta):
    """Used for identifying whether a sequence of chars represents the path to
    a file."""

    @abstractmethod
    def is_local_file(self, *keys: AnyKey) -> Optional[str]:
        raise NotImplementedError


class UselessFileDetector(FileDetector):
    """A file detector that never finds anything."""

    def is_local_file(self, *keys: AnyKey) -> Optional[str]:
        return None


class LocalFileDetector(FileDetector):
    """Detects files on the local disk."""

    def is_local_file(self, *keys: AnyKey) -> Optional[str]:
        file_path = "".join(keys_to_typing(keys))

        with suppress(OSError):
            if Path(file_path).is_file():
                return file_path
