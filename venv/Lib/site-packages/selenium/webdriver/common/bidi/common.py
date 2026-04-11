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

from collections.abc import Generator


def command_builder(method: str, params: dict | None = None) -> Generator[dict, dict, dict]:
    """Build a command iterator to send to the BiDi protocol.

    Args:
        method: The method to execute.
        params: The parameters to pass to the method. Default is None.

    Returns:
        The response from the command execution.
    """
    if params is None:
        params = {}

    command = {"method": method, "params": params}
    cmd = yield command
    return cmd
