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


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Literal, TypedDict

    Orientation = Literal["portrait", "landscape"]

    class _MarginOpts(TypedDict, total=False):
        left: float
        right: float
        top: float
        bottom: float

    class _PageOpts(TypedDict, total=False):
        width: float
        height: float

    class _PrintOpts(TypedDict, total=False):
        margin: _MarginOpts
        page: _PageOpts
        background: bool
        orientation: Orientation
        scale: float
        shrinkToFit: bool
        pageRanges: list[str]

else:
    from typing import Any

    Orientation = str
    _MarginOpts = _PageOpts = _PrintOpts = dict[str, Any]


class _PageSettingsDescriptor:
    """Descriptor which validates `height` and 'width' of page."""

    def __init__(self, name):
        self.name = name

    def __get__(self, obj, cls) -> float | None:
        return obj._page.get(self.name, None)

    def __set__(self, obj, value) -> None:
        getattr(obj, "_validate_num_property")(self.name, value)
        obj._page[self.name] = value
        obj._print_options["page"] = obj._page


class _MarginSettingsDescriptor:
    """Descriptor which validates below attributes.

    - top
    - bottom
    - left
    - right
    """

    def __init__(self, name):
        self.name = name

    def __get__(self, obj, cls) -> float | None:
        return obj._margin.get(self.name, None)

    def __set__(self, obj, value) -> None:
        getattr(obj, "_validate_num_property")(f"Margin {self.name}", value)
        obj._margin[self.name] = value
        obj._print_options["margin"] = obj._margin


class _ScaleDescriptor:
    """Scale descriptor which validates scale."""

    def __init__(self, name):
        self.name = name

    def __get__(self, obj, cls) -> float | None:
        return obj._print_options.get(self.name)

    def __set__(self, obj, value) -> None:
        getattr(obj, "_validate_num_property")(self.name, value)
        if value < 0.1 or value > 2:
            raise ValueError("Value of scale should be between 0.1 and 2")
        obj._print_options[self.name] = value


class _PageOrientationDescriptor:
    """PageOrientation descriptor which validates orientation of page."""

    ORIENTATION_VALUES = ["portrait", "landscape"]

    def __init__(self, name):
        self.name = name

    def __get__(self, obj, cls) -> Orientation | None:
        return obj._print_options.get(self.name, None)

    def __set__(self, obj, value) -> None:
        if value not in self.ORIENTATION_VALUES:
            raise ValueError(f"Orientation value must be one of {self.ORIENTATION_VALUES}")
        obj._print_options[self.name] = value


class _ValidateTypeDescriptor:
    """Base Class Descriptor which validates type of any subclass attribute."""

    def __init__(self, name, expected_type: type):
        self.name = name
        self.expected_type = expected_type

    def __get__(self, obj, cls):
        return obj._print_options.get(self.name, None)

    def __set__(self, obj, value) -> None:
        if not isinstance(value, self.expected_type):
            raise ValueError(f"{self.name} should be of type {self.expected_type.__name__}")
        obj._print_options[self.name] = value


class _ValidateBackGround(_ValidateTypeDescriptor):
    """Expected type of background attribute."""

    def __init__(self, name):
        super().__init__(name, bool)


class _ValidateShrinkToFit(_ValidateTypeDescriptor):
    """Expected type of shrink to fit attribute."""

    def __init__(self, name):
        super().__init__(name, bool)


class _ValidatePageRanges(_ValidateTypeDescriptor):
    """Expected type of page ranges attribute."""

    def __init__(self, name):
        super().__init__(name, list)


class PrintOptions:
    page_height = _PageSettingsDescriptor("height")
    """Gets and Sets page_height:

    Usage:
        - Get: `self.page_height`
        - Set: `self.page_height = value`

    Args:
        value: float value for page height.

    Returns:
        - Get: Optional[float]
        - Set: None
    """

    page_width = _PageSettingsDescriptor("width")
    """Gets and Sets page_width:

    Usage:
        - Get: `self.page_width`
        - Set: `self.page_width = value`

    Args:
        value: float value for page width.

    Returns:
        - Get: Optional[float]
        - Set: None
    """

    margin_top = _MarginSettingsDescriptor("top")
    """Gets and Sets margin_top:

    Usage:
        - Get: `self.margin_top`
        - Set: `self.margin_top = value`

    Args:
        value: float value for top margin.

    Returns:
        - Get: Optional[float]
        - Set: None
    """

    margin_bottom = _MarginSettingsDescriptor("bottom")
    """Gets and Sets margin_bottom:

    Usage:
        - Get: `self.margin_bottom`
        - Set: `self.margin_bottom = value`

    Args:
        value: float value for bottom margin.

    Returns:
        - Get: Optional[float]
        - Set: None
    """

    margin_left = _MarginSettingsDescriptor("left")
    """Gets and Sets margin_left:

    Usage:
        - Get: `self.margin_left`
        - Set: `self.margin_left = value`

    Args:
        value: float value for left margin.

    Returns:
        - Get: Optional[float]
        - Set: None
    """

    margin_right = _MarginSettingsDescriptor("right")
    """Gets and Sets margin_right:

    Usage:
        - Get: `self.margin_right`
        - Set: `self.margin_right = value`

    Args:
        value: float value for right margin.

    Returns:
        - Get: Optional[float]
        - Set: None
    """

    scale = _ScaleDescriptor("scale")
    """Gets and Sets scale:

    Usage:
        - Get: `self.scale`
        - Set: `self.scale = value`

    Args:
        value: float value for scale (between 0.1 and 2).

    Returns:
        - Get: Optional[float]
        - Set: None
    """

    orientation = _PageOrientationDescriptor("orientation")
    """Gets and Sets orientation:

    Usage:
        - Get: `self.orientation`
        - Set: `self.orientation = value`

    Args:
        value: Orientation value ("portrait" or "landscape").

    Returns:
        - Get: Optional[Orientation]
        - Set: None
    """

    background = _ValidateBackGround("background")
    """Gets and Sets background:

    Usage:
        - Get: `self.background`
        - Set: `self.background = value`

    Args:
        value: bool value for background printing.

    Returns:
        - Get: Optional[bool]
        - Set: None
    """

    shrink_to_fit = _ValidateShrinkToFit("shrinkToFit")
    """Gets and Sets shrink_to_fit:

    Usage:
        - Get: `self.shrink_to_fit`
        - Set: `self.shrink_to_fit = value`

    Args:
        value: bool value for shrink to fit.

    Returns:
        - Get: Optional[bool]
        - Set: None
    """

    page_ranges = _ValidatePageRanges("pageRanges")
    """Gets and Sets page_ranges:

    Usage:
        - Get: `self.page_ranges`
        - Set: `self.page_ranges = value`

    Args:
        value: list of page range strings.

    Returns:
        - Get: Optional[List[str]]
        - Set: None
    """
    # Reference for predefined page size constants: https://www.agooddaytoprint.com/page/paper-size-chart-faq
    A4 = {"height": 29.7, "width": 21.0}  # size in cm
    LEGAL = {"height": 35.56, "width": 21.59}  # size in cm
    LETTER = {"height": 27.94, "width": 21.59}  # size in cm
    TABLOID = {"height": 43.18, "width": 27.94}  # size in cm

    def __init__(self) -> None:
        self._print_options: _PrintOpts = {}
        self._page: _PageOpts = {
            "height": PrintOptions.A4["height"],
            "width": PrintOptions.A4["width"],
        }  # Default page size set to A4
        self._margin: _MarginOpts = {}

    def to_dict(self) -> _PrintOpts:
        """Returns a hash of print options configured."""
        return self._print_options

    def set_page_size(self, page_size: dict) -> None:
        """Sets the page size to predefined or custom dimensions.

        Args:
            page_size: A dictionary containing 'height' and 'width' keys with
                respective values in cm.

        Example:
            self.set_page_size(PageSize.A4)  # A4 predefined size
            self.set_page_size({"height": 15.0, "width": 20.0})  # Custom size
        """
        self._validate_num_property("height", page_size["height"])
        self._validate_num_property("width", page_size["width"])
        self._page["height"] = page_size["height"]
        self._page["width"] = page_size["width"]
        self._print_options["page"] = self._page

    def _validate_num_property(self, property_name: str, value: float) -> None:
        """Helper function to validate some of the properties."""
        if not isinstance(value, (int, float)):
            raise ValueError(f"{property_name} should be an integer or a float")

        if value < 0:
            raise ValueError(f"{property_name} cannot be less than 0")
