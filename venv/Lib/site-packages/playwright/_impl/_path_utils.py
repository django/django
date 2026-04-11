# Copyright (c) Microsoft Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import inspect
from pathlib import Path
from types import FrameType
from typing import cast


def get_file_dirname() -> Path:
    """Returns the callee (`__file__`) directory name"""
    frame = cast(FrameType, inspect.currentframe()).f_back
    module = inspect.getmodule(frame)
    assert module
    assert module.__file__
    return Path(module.__file__).parent.absolute()
