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
from typing import List
from typing import Optional

if TYPE_CHECKING:
    from typing import Literal
    from typing import TypedDict

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
        pageRanges: List[str]

else:
    from typing import Any
    from typing import Dict

    Orientation = str
    _MarginOpts = _PageOpts = _PrintOpts = Dict[str, Any]


class _PageSettingsDescriptor:
    """Descriptor which validates `height` and 'width' of page."""

    def __init__(self, name):
        self.name = name

    def __get__(self, obj, cls) -> Optional[float]:
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

    def __get__(self, obj, cls) -> Optional[float]:
        return obj._margin.get(self.name, None)

    def __set__(self, obj, value) -> None:
        getattr(obj, "_validate_num_property")(f"Margin {self.name}", value)
        obj._margin[self.name] = value
        obj._print_options["margin"] = obj._margin


class _ScaleDescriptor:
    """Scale descriptor which validates scale."""

    def __init__(self, name):
        self.name = name

    def __get__(self, obj, cls) -> Optional[float]:
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

    def __get__(self, obj, cls) -> Optional[Orientation]:
        return obj._print_options.get(self.name, None)

    def __set__(self, obj, value) -> None:
        if value not in self.ORIENTATION_VALUES:
            raise ValueError(f"Orientation value must be one of {self.ORIENTATION_VALUES}")
        obj._print_options[self.name] = value


class _ValidateTypeDescriptor:
    """Base Class Descriptor which validates type of any subclass attribute."""

    expected_type = None

    def __init__(self, name, expected_type):
        self.name = name

    def __get__(self, obj, cls):
        return obj._print_options.get(self.name, None)

    def __set__(self, obj, value) -> None:
        if not isinstance(value, self.expected_type):
            raise ValueError(f"{self.name} should be of type {self.expected_type.__name__}")
        obj._print_options[self.name] = value


class _ValidateBackGround(_ValidateTypeDescriptor):
    """Expected type of background attribute."""

    expected_type = bool


class _ValidateShrinkToFit(_ValidateTypeDescriptor):
    """Expected type of shirnk to fit attribute."""

    expected_type = bool


class _ValidatePageRanges(_ValidateTypeDescriptor):
    """Excepted type of page ranges attribute."""

    expected_type = list


class PrintOptions:
    page_height = _PageSettingsDescriptor("height")
    """Gets and Sets page_height:

    Usage
    -----
    - Get
        - `self.page_height`
    - Set
        - `self.page_height` = `value`

    Parameters
    ----------
    `value`: `float`

    Returns
    -------
    - Get
        - `Optional[float]`
    - Set
        - `None`
    """

    page_width = _PageSettingsDescriptor("width")
    """Gets and Sets page_width:

    Usage
    -----
    - Get
        - `self.page_width`
    - Set
        - `self.page_width` = `value`

    Patameters
    ----------
    `value`: `float`

    Returns
    -------
    - Get
        - `Optional[float]`
    - Set
        - `None`
    """

    margin_top = _MarginSettingsDescriptor("top")
    """Gets and Sets margin_top:

    Usage
    -----
    - Get
        - `self.margin_top`
    - Set
        - `slef.margin_top` = `value`

    Parameters
    ----------
    `value`: `float`

    Returns
    -------
    - Get
        - `Optional[float]`
    - Set
        - `None`
    """

    margin_bottom = _MarginSettingsDescriptor("bottom")
    """Gets and Sets margin_bottom:

    Usage
    -----
    - Get
        - `self.margin_bottom`
    - Set
        - `self.margin_bottom` = `value`

    Parameters
    ----------
    `value`: `float`

    Returns
    -------
    - Get
        - `Optional[float]`
    - Set
        - `None`
    """

    margin_left = _MarginSettingsDescriptor("left")
    """Gets and Sets margin_left:

    Usage
    -----
    - Get
        - `self.margin_left`
    -Set
        - `self.margin_left` = `value`

    Parameters
    ----------
    `value`: `float`

    Returns
    -------
    - Get
        - `Optional[float]`
    - Set
        - `None`
    """

    margin_right = _MarginSettingsDescriptor("right")
    """Gets and Sets margin_right:

    Usage
    -----
    - Get
        - `self.margin_right`
    - Set
        - `self.margin_right` = `value`

    Parameters
    ----------
    `value`: `float`

    Returns
    -------
    - Get
        - `Optional[float]`
    - Set
        - `None`
    """

    scale = _ScaleDescriptor("scale")
    """Gets and Sets scale:

    Usage
    -----
    - Get
        - `self.scale`
    - Set
        - `self.scale` = `value`

    Parameters
    ----------
    `value`: `float`

    Returns
    -------
    - Get
        - `Optional[float]`
    - Set
        - `None`
    """

    orientation = _PageOrientationDescriptor("orientation")
    """Gets and Sets orientation:

    Usage
    -----
    - Get
        - `self.orientation`
    - Set
        - `self.orientation` = `value`

    Parameters
    ----------
    `value`: `Orientation`

    Returns
    -------
    - Get
        - `Optional[Orientation]`
    - Set
        - `None`
    """

    background = _ValidateBackGround("background", bool)
    """Gets and Sets background:

    Usage
    -----
    - Get
        - `self.backgorund`
    - Set
        - `self.background` = `value`

    Parameters
    ----------
    `value`: `bool`

    Returns
    -------
    - Get
        - `Optional[bool]`
    - Set
        - `None`
    """

    shrink_to_fit = _ValidateShrinkToFit("shrinkToFit", bool)
    """Gets and Sets shrink_to_fit:

    Usage
    -----
    - Get
        - `self.shrink_to_fit`
    - Set
        - `self.shrink_to_fit` = `value`

    Parameters
    ----------
    `value`: `bool`

    Returns
    -------
    - Get
        - `Optional[bool]`
    - Set
        - `None`
    """

    page_ranges = _ValidatePageRanges("pageRanges", list)
    """Gets and Sets page_ranges:

    Usage
    -----
    - Get
        - `self.page_ranges`
    - Set
        - `self.page_ranges` = `value`

    Parameters
    ----------
    `value`: ` List[str]`

    Returns
    -------
    - Get
        - `Optional[List[str]]`
    - Set
        - `None`
    """

    def __init__(self) -> None:
        self._print_options: _PrintOpts = {}
        self._page: _PageOpts = {}
        self._margin: _MarginOpts = {}

    def to_dict(self) -> _PrintOpts:
        """:Returns: A hash of print options configured."""
        return self._print_options

    def _validate_num_property(self, property_name: str, value: float) -> None:
        """Helper function to validate some of the properties."""
        if not isinstance(value, (int, float)):
            raise ValueError(f"{property_name} should be an integer or a float")

        if value < 0:
            raise ValueError(f"{property_name} cannot be less then 0")
