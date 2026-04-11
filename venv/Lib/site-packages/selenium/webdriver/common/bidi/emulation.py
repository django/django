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
from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Any, TypeVar

from selenium.webdriver.common.bidi.common import command_builder

if TYPE_CHECKING:
    from selenium.webdriver.remote.websocket_connection import WebSocketConnection


class ScreenOrientationNatural(Enum):
    """Natural screen orientation."""

    PORTRAIT = "portrait"
    LANDSCAPE = "landscape"


class ScreenOrientationType(Enum):
    """Screen orientation type."""

    PORTRAIT_PRIMARY = "portrait-primary"
    PORTRAIT_SECONDARY = "portrait-secondary"
    LANDSCAPE_PRIMARY = "landscape-primary"
    LANDSCAPE_SECONDARY = "landscape-secondary"


E = TypeVar("E", ScreenOrientationNatural, ScreenOrientationType)


def _convert_to_enum(value: E | str, enum_class: type[E]) -> E:
    if isinstance(value, enum_class):
        return value
    assert isinstance(value, str)
    try:
        return enum_class(value.lower())
    except ValueError:
        raise ValueError(f"Invalid orientation: {value}")


class ScreenOrientation:
    """Represents screen orientation configuration."""

    def __init__(
        self,
        natural: ScreenOrientationNatural | str,
        type: ScreenOrientationType | str,
    ):
        """Initialize ScreenOrientation.

        Args:
            natural: Natural screen orientation ("portrait" or "landscape").
            type: Screen orientation type ("portrait-primary", "portrait-secondary",
                "landscape-primary", or "landscape-secondary").

        Raises:
            ValueError: If natural or type values are invalid.
        """
        # handle string values
        self.natural = _convert_to_enum(natural, ScreenOrientationNatural)
        self.type = _convert_to_enum(type, ScreenOrientationType)

    def to_dict(self) -> dict[str, str]:
        return {
            "natural": self.natural.value,
            "type": self.type.value,
        }


class GeolocationCoordinates:
    """Represents geolocation coordinates."""

    def __init__(
        self,
        latitude: float,
        longitude: float,
        accuracy: float = 1.0,
        altitude: float | None = None,
        altitude_accuracy: float | None = None,
        heading: float | None = None,
        speed: float | None = None,
    ):
        """Initialize GeolocationCoordinates.

        Args:
            latitude: Latitude coordinate (-90.0 to 90.0).
            longitude: Longitude coordinate (-180.0 to 180.0).
            accuracy: Accuracy in meters (>= 0.0), defaults to 1.0.
            altitude: Altitude in meters or None, defaults to None.
            altitude_accuracy: Altitude accuracy in meters (>= 0.0) or None, defaults to None.
            heading: Heading in degrees (0.0 to 360.0) or None, defaults to None.
            speed: Speed in meters per second (>= 0.0) or None, defaults to None.

        Raises:
            ValueError: If coordinates are out of valid range or if altitude_accuracy is provided without altitude.
        """
        self.latitude = latitude
        self.longitude = longitude
        self.accuracy = accuracy
        self.altitude = altitude
        self.altitude_accuracy = altitude_accuracy
        self.heading = heading
        self.speed = speed

    @property
    def latitude(self) -> float:
        return self._latitude

    @latitude.setter
    def latitude(self, value: float) -> None:
        if not (-90.0 <= value <= 90.0):
            raise ValueError("latitude must be between -90.0 and 90.0")
        self._latitude = value

    @property
    def longitude(self) -> float:
        return self._longitude

    @longitude.setter
    def longitude(self, value: float) -> None:
        if not (-180.0 <= value <= 180.0):
            raise ValueError("longitude must be between -180.0 and 180.0")
        self._longitude = value

    @property
    def accuracy(self) -> float:
        return self._accuracy

    @accuracy.setter
    def accuracy(self, value: float) -> None:
        if value < 0.0:
            raise ValueError("accuracy must be >= 0.0")
        self._accuracy = value

    @property
    def altitude(self) -> float | None:
        return self._altitude

    @altitude.setter
    def altitude(self, value: float | None) -> None:
        self._altitude = value

    @property
    def altitude_accuracy(self) -> float | None:
        return self._altitude_accuracy

    @altitude_accuracy.setter
    def altitude_accuracy(self, value: float | None) -> None:
        if value is not None and self.altitude is None:
            raise ValueError("altitude_accuracy cannot be set without altitude")
        if value is not None and value < 0.0:
            raise ValueError("altitude_accuracy must be >= 0.0")
        self._altitude_accuracy = value

    @property
    def heading(self) -> float | None:
        return self._heading

    @heading.setter
    def heading(self, value: float | None) -> None:
        if value is not None and not (0.0 <= value < 360.0):
            raise ValueError("heading must be between 0.0 and 360.0")
        self._heading = value

    @property
    def speed(self) -> float | None:
        return self._speed

    @speed.setter
    def speed(self, value: float | None) -> None:
        if value is not None and value < 0.0:
            raise ValueError("speed must be >= 0.0")
        self._speed = value

    def to_dict(self) -> dict[str, float | None]:
        result: dict[str, float | None] = {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "accuracy": self.accuracy,
        }

        if self.altitude is not None:
            result["altitude"] = self.altitude

        if self.altitude_accuracy is not None:
            result["altitudeAccuracy"] = self.altitude_accuracy

        if self.heading is not None:
            result["heading"] = self.heading

        if self.speed is not None:
            result["speed"] = self.speed

        return result


class GeolocationPositionError:
    """Represents a geolocation position error."""

    TYPE_POSITION_UNAVAILABLE = "positionUnavailable"

    def __init__(self, type: str = TYPE_POSITION_UNAVAILABLE):
        if type != self.TYPE_POSITION_UNAVAILABLE:
            raise ValueError(f'type must be "{self.TYPE_POSITION_UNAVAILABLE}"')
        self.type = type

    def to_dict(self) -> dict[str, str]:
        return {"type": self.type}


class Emulation:
    """BiDi implementation of the emulation module."""

    def __init__(self, conn: WebSocketConnection) -> None:
        self.conn = conn

    def set_geolocation_override(
        self,
        coordinates: GeolocationCoordinates | None = None,
        error: GeolocationPositionError | None = None,
        contexts: list[str] | None = None,
        user_contexts: list[str] | None = None,
    ) -> None:
        """Set geolocation override for the given contexts or user contexts.

        Args:
            coordinates: Geolocation coordinates to emulate, or None.
            error: Geolocation error to emulate, or None.
            contexts: List of browsing context IDs to apply the override to.
            user_contexts: List of user context IDs to apply the override to.

        Raises:
            ValueError: If both coordinates and error are provided, or if both contexts
                and user_contexts are provided, or if neither contexts nor
                user_contexts are provided.
        """
        if coordinates is not None and error is not None:
            raise ValueError("Cannot specify both coordinates and error")

        if contexts is not None and user_contexts is not None:
            raise ValueError("Cannot specify both contexts and userContexts")

        if contexts is None and user_contexts is None:
            raise ValueError("Must specify either contexts or userContexts")

        params: dict[str, Any] = {}

        if coordinates is not None:
            params["coordinates"] = coordinates.to_dict()
        elif error is not None:
            params["error"] = error.to_dict()

        if contexts is not None:
            params["contexts"] = contexts
        elif user_contexts is not None:
            params["userContexts"] = user_contexts

        self.conn.execute(command_builder("emulation.setGeolocationOverride", params))

    def set_timezone_override(
        self,
        timezone: str | None = None,
        contexts: list[str] | None = None,
        user_contexts: list[str] | None = None,
    ) -> None:
        """Set timezone override for the given contexts or user contexts.

        Args:
            timezone: Timezone identifier (IANA timezone name or offset string like '+01:00'),
                or None to clear the override.
            contexts: List of browsing context IDs to apply the override to.
            user_contexts: List of user context IDs to apply the override to.

        Raises:
            ValueError: If both contexts and user_contexts are provided, or if neither
                contexts nor user_contexts are provided.
        """
        if contexts is not None and user_contexts is not None:
            raise ValueError("Cannot specify both contexts and user_contexts")

        if contexts is None and user_contexts is None:
            raise ValueError("Must specify either contexts or user_contexts")

        params: dict[str, Any] = {"timezone": timezone}

        if contexts is not None:
            params["contexts"] = contexts
        elif user_contexts is not None:
            params["userContexts"] = user_contexts

        self.conn.execute(command_builder("emulation.setTimezoneOverride", params))

    def set_locale_override(
        self,
        locale: str | None = None,
        contexts: list[str] | None = None,
        user_contexts: list[str] | None = None,
    ) -> None:
        """Set locale override for the given contexts or user contexts.

        Args:
            locale: Locale string as per BCP 47, or None to clear override.
            contexts: List of browsing context IDs to apply the override to.
            user_contexts: List of user context IDs to apply the override to.

        Raises:
            ValueError: If both contexts and user_contexts are provided, or if neither
                contexts nor user_contexts are provided, or if locale is invalid.
        """
        if contexts is not None and user_contexts is not None:
            raise ValueError("Cannot specify both contexts and userContexts")

        if contexts is None and user_contexts is None:
            raise ValueError("Must specify either contexts or userContexts")

        params: dict[str, Any] = {"locale": locale}

        if contexts is not None:
            params["contexts"] = contexts
        elif user_contexts is not None:
            params["userContexts"] = user_contexts

        self.conn.execute(command_builder("emulation.setLocaleOverride", params))

    def set_scripting_enabled(
        self,
        enabled: bool | None = False,
        contexts: list[str] | None = None,
        user_contexts: list[str] | None = None,
    ) -> None:
        """Set scripting enabled override for the given contexts or user contexts.

        Args:
            enabled: False to disable scripting, None to clear the override.
                Note: Only emulation of disabled JavaScript is supported.
            contexts: List of browsing context IDs to apply the override to.
            user_contexts: List of user context IDs to apply the override to.

        Raises:
            ValueError: If both contexts and user_contexts are provided, or if neither
                contexts nor user_contexts are provided, or if enabled is True.
        """
        if enabled:
            raise ValueError("Only emulation of disabled JavaScript is supported (enabled must be False or None)")

        if contexts is not None and user_contexts is not None:
            raise ValueError("Cannot specify both contexts and userContexts")

        if contexts is None and user_contexts is None:
            raise ValueError("Must specify either contexts or userContexts")

        params: dict[str, Any] = {"enabled": enabled}

        if contexts is not None:
            params["contexts"] = contexts
        elif user_contexts is not None:
            params["userContexts"] = user_contexts

        self.conn.execute(command_builder("emulation.setScriptingEnabled", params))

    def set_screen_orientation_override(
        self,
        screen_orientation: ScreenOrientation | None = None,
        contexts: list[str] | None = None,
        user_contexts: list[str] | None = None,
    ) -> None:
        """Set screen orientation override for the given contexts or user contexts.

        Args:
            screen_orientation: ScreenOrientation object to emulate, or None to clear the override.
            contexts: List of browsing context IDs to apply the override to.
            user_contexts: List of user context IDs to apply the override to.

        Raises:
            ValueError: If both contexts and user_contexts are provided, or if neither
                contexts nor user_contexts are provided.
        """
        if contexts is not None and user_contexts is not None:
            raise ValueError("Cannot specify both contexts and userContexts")

        if contexts is None and user_contexts is None:
            raise ValueError("Must specify either contexts or userContexts")

        params: dict[str, Any] = {
            "screenOrientation": screen_orientation.to_dict() if screen_orientation is not None else None
        }

        if contexts is not None:
            params["contexts"] = contexts
        elif user_contexts is not None:
            params["userContexts"] = user_contexts

        self.conn.execute(command_builder("emulation.setScreenOrientationOverride", params))

    def set_user_agent_override(
        self,
        user_agent: str | None = None,
        contexts: list[str] | None = None,
        user_contexts: list[str] | None = None,
    ) -> None:
        """Set user agent override for the given contexts or user contexts.

        Args:
            user_agent: User agent string to emulate, or None to clear the override.
            contexts: List of browsing context IDs to apply the override to.
            user_contexts: List of user context IDs to apply the override to.

        Raises:
            ValueError: If both contexts and user_contexts are provided, or if neither
                contexts nor user_contexts are provided.
        """
        if contexts is not None and user_contexts is not None:
            raise ValueError("Cannot specify both contexts and user_contexts")

        if contexts is None and user_contexts is None:
            raise ValueError("Must specify either contexts or user_contexts")

        params: dict[str, Any] = {"userAgent": user_agent}

        if contexts is not None:
            params["contexts"] = contexts
        elif user_contexts is not None:
            params["userContexts"] = user_contexts

        self.conn.execute(command_builder("emulation.setUserAgentOverride", params))

    def set_network_conditions(
        self,
        offline: bool = False,
        contexts: list[str] | None = None,
        user_contexts: list[str] | None = None,
    ) -> None:
        """Set network conditions for the given contexts or user contexts.

        Args:
            offline: True to emulate offline network conditions, False to clear the override.
            contexts: List of browsing context IDs to apply the conditions to.
            user_contexts: List of user context IDs to apply the conditions to.

        Raises:
            ValueError: If both contexts and user_contexts are provided, or if neither
                contexts nor user_contexts are provided.
        """
        if contexts is not None and user_contexts is not None:
            raise ValueError("Cannot specify both contexts and user_contexts")

        if contexts is None and user_contexts is None:
            raise ValueError("Must specify either contexts or user_contexts")

        params: dict[str, Any] = {}

        if offline:
            params["networkConditions"] = {"type": "offline"}
        else:
            # if offline is False or None, then clear the override
            params["networkConditions"] = None

        if contexts is not None:
            params["contexts"] = contexts
        elif user_contexts is not None:
            params["userContexts"] = user_contexts

        self.conn.execute(command_builder("emulation.setNetworkConditions", params))

    def set_screen_settings_override(
        self,
        width: int | None = None,
        height: int | None = None,
        contexts: list[str] | None = None,
        user_contexts: list[str] | None = None,
    ) -> None:
        """Set screen settings override for the given contexts or user contexts.

        Args:
            width: Screen width in pixels (>= 0). None to clear the override.
            height: Screen height in pixels (>= 0). None to clear the override.
            contexts: List of browsing context IDs to apply the override to.
            user_contexts: List of user context IDs to apply the override to.

        Raises:
            ValueError: If only one of width/height is provided, or if both contexts
                and user_contexts are provided, or if neither is provided.
        """
        if (width is None) != (height is None):
            raise ValueError("Must provide both width and height, or neither to clear the override")

        if contexts is not None and user_contexts is not None:
            raise ValueError("Cannot specify both contexts and user_contexts")

        if contexts is None and user_contexts is None:
            raise ValueError("Must specify either contexts or user_contexts")

        screen_area = None
        if width is not None and height is not None:
            if not isinstance(width, int) or not isinstance(height, int):
                raise ValueError("width and height must be integers")
            if width < 0 or height < 0:
                raise ValueError("width and height must be >= 0")
            screen_area = {"width": width, "height": height}

        params: dict[str, Any] = {"screenArea": screen_area}

        if contexts is not None:
            params["contexts"] = contexts
        elif user_contexts is not None:
            params["userContexts"] = user_contexts

        self.conn.execute(command_builder("emulation.setScreenSettingsOverride", params))
