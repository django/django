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

import math
from dataclasses import dataclass, field
from typing import Any

from selenium.webdriver.common.bidi.common import command_builder
from selenium.webdriver.common.bidi.session import Session


class PointerType:
    """Represents the possible pointer types."""

    MOUSE = "mouse"
    PEN = "pen"
    TOUCH = "touch"

    VALID_TYPES = {MOUSE, PEN, TOUCH}


class Origin:
    """Represents the possible origin types."""

    VIEWPORT = "viewport"
    POINTER = "pointer"


@dataclass
class ElementOrigin:
    """Represents an element origin for input actions."""

    type: str
    element: dict

    def __init__(self, element_reference: dict):
        self.type = "element"
        self.element = element_reference

    def to_dict(self) -> dict:
        """Convert the ElementOrigin to a dictionary."""
        return {"type": self.type, "element": self.element}


@dataclass
class PointerParameters:
    """Represents pointer parameters for pointer actions."""

    pointer_type: str = PointerType.MOUSE

    def __post_init__(self):
        if self.pointer_type not in PointerType.VALID_TYPES:
            raise ValueError(f"Invalid pointer type: {self.pointer_type}. Must be one of {PointerType.VALID_TYPES}")

    def to_dict(self) -> dict:
        """Convert the PointerParameters to a dictionary."""
        return {"pointerType": self.pointer_type}


@dataclass
class PointerCommonProperties:
    """Common properties for pointer actions."""

    width: int = 1
    height: int = 1
    pressure: float = 0.0
    tangential_pressure: float = 0.0
    twist: int = 0
    altitude_angle: float = 0.0
    azimuth_angle: float = 0.0

    def __post_init__(self):
        if self.width < 1:
            raise ValueError("width must be at least 1")
        if self.height < 1:
            raise ValueError("height must be at least 1")
        if not (0.0 <= self.pressure <= 1.0):
            raise ValueError("pressure must be between 0.0 and 1.0")
        if not (0.0 <= self.tangential_pressure <= 1.0):
            raise ValueError("tangential_pressure must be between 0.0 and 1.0")
        if not (0 <= self.twist <= 359):
            raise ValueError("twist must be between 0 and 359")
        if not (0.0 <= self.altitude_angle <= math.pi / 2):
            raise ValueError("altitude_angle must be between 0.0 and π/2")
        if not (0.0 <= self.azimuth_angle <= 2 * math.pi):
            raise ValueError("azimuth_angle must be between 0.0 and 2π")

    def to_dict(self) -> dict:
        """Convert the PointerCommonProperties to a dictionary."""
        result: dict[str, Any] = {}
        if self.width != 1:
            result["width"] = self.width
        if self.height != 1:
            result["height"] = self.height
        if self.pressure != 0.0:
            result["pressure"] = self.pressure
        if self.tangential_pressure != 0.0:
            result["tangentialPressure"] = self.tangential_pressure
        if self.twist != 0:
            result["twist"] = self.twist
        if self.altitude_angle != 0.0:
            result["altitudeAngle"] = self.altitude_angle
        if self.azimuth_angle != 0.0:
            result["azimuthAngle"] = self.azimuth_angle
        return result


# Action classes
@dataclass
class PauseAction:
    """Represents a pause action."""

    duration: int | None = None

    @property
    def type(self) -> str:
        return "pause"

    def to_dict(self) -> dict:
        """Convert the PauseAction to a dictionary."""
        result: dict[str, Any] = {"type": self.type}
        if self.duration is not None:
            result["duration"] = self.duration
        return result


@dataclass
class KeyDownAction:
    """Represents a key down action."""

    value: str = ""

    @property
    def type(self) -> str:
        return "keyDown"

    def to_dict(self) -> dict:
        """Convert the KeyDownAction to a dictionary."""
        return {"type": self.type, "value": self.value}


@dataclass
class KeyUpAction:
    """Represents a key up action."""

    value: str = ""

    @property
    def type(self) -> str:
        return "keyUp"

    def to_dict(self) -> dict:
        """Convert the KeyUpAction to a dictionary."""
        return {"type": self.type, "value": self.value}


@dataclass
class PointerDownAction:
    """Represents a pointer down action."""

    button: int = 0
    properties: PointerCommonProperties | None = None

    @property
    def type(self) -> str:
        return "pointerDown"

    def to_dict(self) -> dict:
        """Convert the PointerDownAction to a dictionary."""
        result: dict[str, Any] = {"type": self.type, "button": self.button}
        if self.properties:
            result.update(self.properties.to_dict())
        return result


@dataclass
class PointerUpAction:
    """Represents a pointer up action."""

    button: int = 0

    @property
    def type(self) -> str:
        return "pointerUp"

    def to_dict(self) -> dict:
        """Convert the PointerUpAction to a dictionary."""
        return {"type": self.type, "button": self.button}


@dataclass
class PointerMoveAction:
    """Represents a pointer move action."""

    x: float = 0
    y: float = 0
    duration: int | None = None
    origin: str | ElementOrigin | None = None
    properties: PointerCommonProperties | None = None

    @property
    def type(self) -> str:
        return "pointerMove"

    def to_dict(self) -> dict:
        """Convert the PointerMoveAction to a dictionary."""
        result: dict[str, Any] = {"type": self.type, "x": self.x, "y": self.y}
        if self.duration is not None:
            result["duration"] = self.duration
        if self.origin is not None:
            if isinstance(self.origin, ElementOrigin):
                result["origin"] = self.origin.to_dict()
            else:
                result["origin"] = self.origin
        if self.properties:
            result.update(self.properties.to_dict())
        return result


@dataclass
class WheelScrollAction:
    """Represents a wheel scroll action."""

    x: int = 0
    y: int = 0
    delta_x: int = 0
    delta_y: int = 0
    duration: int | None = None
    origin: str | ElementOrigin | None = Origin.VIEWPORT

    @property
    def type(self) -> str:
        return "scroll"

    def to_dict(self) -> dict:
        """Convert the WheelScrollAction to a dictionary."""
        result: dict[str, Any] = {
            "type": self.type,
            "x": self.x,
            "y": self.y,
            "deltaX": self.delta_x,
            "deltaY": self.delta_y,
        }
        if self.duration is not None:
            result["duration"] = self.duration
        if self.origin is not None:
            if isinstance(self.origin, ElementOrigin):
                result["origin"] = self.origin.to_dict()
            else:
                result["origin"] = self.origin
        return result


# Source Actions
@dataclass
class NoneSourceActions:
    """Represents a sequence of none actions."""

    id: str = ""
    actions: list[PauseAction] = field(default_factory=list)

    @property
    def type(self) -> str:
        return "none"

    def to_dict(self) -> dict:
        """Convert the NoneSourceActions to a dictionary."""
        return {"type": self.type, "id": self.id, "actions": [action.to_dict() for action in self.actions]}


@dataclass
class KeySourceActions:
    """Represents a sequence of key actions."""

    id: str = ""
    actions: list[PauseAction | KeyDownAction | KeyUpAction] = field(default_factory=list)

    @property
    def type(self) -> str:
        return "key"

    def to_dict(self) -> dict:
        """Convert the KeySourceActions to a dictionary."""
        return {"type": self.type, "id": self.id, "actions": [action.to_dict() for action in self.actions]}


@dataclass
class PointerSourceActions:
    """Represents a sequence of pointer actions."""

    id: str = ""
    parameters: PointerParameters | None = None
    actions: list[PauseAction | PointerDownAction | PointerUpAction | PointerMoveAction] = field(default_factory=list)

    def __post_init__(self):
        if self.parameters is None:
            self.parameters = PointerParameters()

    @property
    def type(self) -> str:
        return "pointer"

    def to_dict(self) -> dict:
        """Convert the PointerSourceActions to a dictionary."""
        result: dict[str, Any] = {
            "type": self.type,
            "id": self.id,
            "actions": [action.to_dict() for action in self.actions],
        }
        if self.parameters:
            result["parameters"] = self.parameters.to_dict()
        return result


@dataclass
class WheelSourceActions:
    """Represents a sequence of wheel actions."""

    id: str = ""
    actions: list[PauseAction | WheelScrollAction] = field(default_factory=list)

    @property
    def type(self) -> str:
        return "wheel"

    def to_dict(self) -> dict:
        """Convert the WheelSourceActions to a dictionary."""
        return {"type": self.type, "id": self.id, "actions": [action.to_dict() for action in self.actions]}


@dataclass
class FileDialogInfo:
    """Represents file dialog information from input.fileDialogOpened event."""

    context: str
    multiple: bool
    element: dict | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "FileDialogInfo":
        """Creates a FileDialogInfo instance from a dictionary.

        Args:
            data: A dictionary containing the file dialog information.

        Returns:
            FileDialogInfo: A new instance of FileDialogInfo.
        """
        return cls(context=data["context"], multiple=data["multiple"], element=data.get("element"))


# Event Class
class FileDialogOpened:
    """Event class for input.fileDialogOpened event."""

    event_class = "input.fileDialogOpened"

    @classmethod
    def from_json(cls, json):
        """Create FileDialogInfo from JSON data."""
        return FileDialogInfo.from_dict(json)


class Input:
    """BiDi implementation of the input module."""

    def __init__(self, conn):
        self.conn = conn
        self.subscriptions = {}
        self.callbacks = {}

    def perform_actions(
        self,
        context: str,
        actions: list[NoneSourceActions | KeySourceActions | PointerSourceActions | WheelSourceActions],
    ) -> None:
        """Performs a sequence of user input actions.

        Args:
            context: The browsing context ID where actions should be performed.
            actions: A list of source actions to perform.
        """
        params = {"context": context, "actions": [action.to_dict() for action in actions]}
        self.conn.execute(command_builder("input.performActions", params))

    def release_actions(self, context: str) -> None:
        """Releases all input state for the given context.

        Args:
            context: The browsing context ID to release actions for.
        """
        params = {"context": context}
        self.conn.execute(command_builder("input.releaseActions", params))

    def set_files(self, context: str, element: dict, files: list[str]) -> None:
        """Sets files for a file input element.

        Args:
            context: The browsing context ID.
            element: The element reference (script.SharedReference).
            files: A list of file paths to set.
        """
        params = {"context": context, "element": element, "files": files}
        self.conn.execute(command_builder("input.setFiles", params))

    def add_file_dialog_handler(self, handler) -> int:
        """Add a handler for file dialog opened events.

        Args:
            handler: Callback function that takes a FileDialogInfo object.

        Returns:
            int: Callback ID for removing the handler later.
        """
        # Subscribe to the event if not already subscribed
        if FileDialogOpened.event_class not in self.subscriptions:
            session = Session(self.conn)
            self.conn.execute(session.subscribe(FileDialogOpened.event_class))
            self.subscriptions[FileDialogOpened.event_class] = []

        # Add callback - the callback receives the parsed FileDialogInfo directly
        callback_id = self.conn.add_callback(FileDialogOpened, handler)

        self.subscriptions[FileDialogOpened.event_class].append(callback_id)
        self.callbacks[callback_id] = handler

        return callback_id

    def remove_file_dialog_handler(self, callback_id: int) -> None:
        """Remove a file dialog handler.

        Args:
            callback_id: The callback ID returned by add_file_dialog_handler.
        """
        if callback_id in self.callbacks:
            del self.callbacks[callback_id]

        if FileDialogOpened.event_class in self.subscriptions:
            if callback_id in self.subscriptions[FileDialogOpened.event_class]:
                self.subscriptions[FileDialogOpened.event_class].remove(callback_id)

            # If no more callbacks for this event, unsubscribe
            if not self.subscriptions[FileDialogOpened.event_class]:
                session = Session(self.conn)
                self.conn.execute(session.unsubscribe(FileDialogOpened.event_class))
                del self.subscriptions[FileDialogOpened.event_class]

        self.conn.remove_callback(FileDialogOpened, callback_id)
