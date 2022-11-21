# Copyright (c) 2007, Robert Coup <robert.coup@onetrackmind.co.nz>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
#   1. Redistributions of source code must retain the above copyright notice,
#      this list of conditions and the following disclaimer.
#
#   2. Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in the
#      documentation and/or other materials provided with the distribution.
#
#   3. Neither the name of Distance nor the names of its contributors may be used
#      to endorse or promote products derived from this software without
#      specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
# ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
"""
Distance and Area objects to allow for sensible and convenient calculation
and conversions.

Authors: Robert Coup, Justin Bronn, Riccardo Di Virgilio

Inspired by GeoPy (https://github.com/geopy/geopy)
and Geoff Biggs' PhD work on dimensioned units for robotics.
"""
from decimal import Decimal
from functools import total_ordering

__all__ = ["A", "Area", "D", "Distance"]

NUMERIC_TYPES = (int, float, Decimal)
AREA_PREFIX = "sq_"


def pretty_name(obj):
    return obj.__name__ if obj.__class__ == type else obj.__class__.__name__


@total_ordering
class MeasureBase:
    STANDARD_UNIT = None
    ALIAS = {}
    UNITS = {}
    LALIAS = {}

    def __init__(self, default_unit=None, **kwargs):
        value, self._default_unit = self.default_units(kwargs)
        setattr(self, self.STANDARD_UNIT, value)
        if default_unit and isinstance(default_unit, str):
            self._default_unit = default_unit

    def _get_standard(self):
        return getattr(self, self.STANDARD_UNIT)

    def _set_standard(self, value):
        setattr(self, self.STANDARD_UNIT, value)

    standard = property(_get_standard, _set_standard)

    def __getattr__(self, name):
        if name in self.UNITS:
            return self.standard / self.UNITS[name]
        else:
            raise AttributeError(f"Unknown unit type: {name}")

    def __repr__(self):
        return f"{pretty_name(self)}({self._default_unit}={getattr(self, self._default_unit)})"

    def __str__(self):
        return f"{getattr(self, self._default_unit)} {self._default_unit}"

    # **** Comparison methods ****

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.standard == other.standard
        else:
            return NotImplemented

    def __hash__(self):
        return hash(self.standard)

    def __lt__(self, other):
        if isinstance(other, self.__class__):
            return self.standard < other.standard
        else:
            return NotImplemented

    # **** Operators methods ****

    def __add__(self, other):
        if isinstance(other, self.__class__):
            return self.__class__(
                default_unit=self._default_unit,
                **{self.STANDARD_UNIT: (self.standard + other.standard)},
            )
        else:
            raise TypeError(
                "%(class)s must be added with %(class)s" % {"class": pretty_name(self)}
            )

    def __iadd__(self, other):
        if isinstance(other, self.__class__):
            self.standard += other.standard
            return self
        else:
            raise TypeError(
                "%(class)s must be added with %(class)s" % {"class": pretty_name(self)}
            )

    def __sub__(self, other):
        if isinstance(other, self.__class__):
            return self.__class__(
                default_unit=self._default_unit,
                **{self.STANDARD_UNIT: (self.standard - other.standard)},
            )
        else:
            raise TypeError(
                "%(class)s must be subtracted from %(class)s"
                % {"class": pretty_name(self)}
            )

    def __isub__(self, other):
        if isinstance(other, self.__class__):
            self.standard -= other.standard
            return self
        else:
            raise TypeError(
                "%(class)s must be subtracted from %(class)s"
                % {"class": pretty_name(self)}
            )

    def __mul__(self, other):
        if isinstance(other, NUMERIC_TYPES):
            return self.__class__(
                default_unit=self._default_unit,
                **{self.STANDARD_UNIT: (self.standard * other)},
            )
        else:
            raise TypeError(
                "%(class)s must be multiplied with number"
                % {"class": pretty_name(self)}
            )

    def __imul__(self, other):
        if isinstance(other, NUMERIC_TYPES):
            self.standard *= float(other)
            return self
        else:
            raise TypeError(
                "%(class)s must be multiplied with number"
                % {"class": pretty_name(self)}
            )

    def __rmul__(self, other):
        return self * other

    def __truediv__(self, other):
        if isinstance(other, self.__class__):
            return self.standard / other.standard
        if isinstance(other, NUMERIC_TYPES):
            return self.__class__(
                default_unit=self._default_unit,
                **{self.STANDARD_UNIT: (self.standard / other)},
            )
        else:
            raise TypeError(
                "%(class)s must be divided with number or %(class)s"
                % {"class": pretty_name(self)}
            )

    def __itruediv__(self, other):
        if isinstance(other, NUMERIC_TYPES):
            self.standard /= float(other)
            return self
        else:
            raise TypeError(
                "%(class)s must be divided with number" % {"class": pretty_name(self)}
            )

    def __bool__(self):
        return bool(self.standard)

    def default_units(self, kwargs):
        """
        Return the unit value and the default units specified
        from the given keyword arguments dictionary.
        """
        val = 0.0
        default_unit = self.STANDARD_UNIT
        for unit, value in kwargs.items():
            if not isinstance(value, float):
                value = float(value)
            if unit in self.UNITS:
                val += self.UNITS[unit] * value
                default_unit = unit
            elif unit in self.ALIAS:
                u = self.ALIAS[unit]
                val += self.UNITS[u] * value
                default_unit = u
            else:
                lower = unit.lower()
                if lower in self.UNITS:
                    val += self.UNITS[lower] * value
                    default_unit = lower
                elif lower in self.LALIAS:
                    u = self.LALIAS[lower]
                    val += self.UNITS[u] * value
                    default_unit = u
                else:
                    raise AttributeError(f"Unknown unit type: {unit}")
        return val, default_unit

    @classmethod
    def unit_attname(cls, unit_str):
        """
        Retrieve the unit attribute name for the given unit string.
        For example, if the given unit string is 'metre', return 'm'.
        Raise an exception if an attribute cannot be found.
        """
        lower = unit_str.lower()
        if unit_str in cls.UNITS:
            return unit_str
        elif lower in cls.UNITS:
            return lower
        elif lower in cls.LALIAS:
            return cls.LALIAS[lower]
        else:
            raise Exception(
                'Could not find a unit keyword associated with "%s"' % unit_str
            )


class Distance(MeasureBase):
    STANDARD_UNIT = "m"
    UNITS = {
        "chain": 20.1168,
        "chain_benoit": 20.116782,
        "chain_sears": 20.1167645,
        "british_chain_benoit": 20.1167824944,
        "british_chain_sears": 20.1167651216,
        "british_chain_sears_truncated": 20.116756,
        "cm": 0.01,
        "british_ft": 0.304799471539,
        "british_yd": 0.914398414616,
        "clarke_ft": 0.3047972654,
        "clarke_link": 0.201166195164,
        "fathom": 1.8288,
        "ft": 0.3048,
        "furlong": 201.168,
        "german_m": 1.0000135965,
        "gold_coast_ft": 0.304799710181508,
        "indian_yd": 0.914398530744,
        "inch": 0.0254,
        "km": 1000.0,
        "link": 0.201168,
        "link_benoit": 0.20116782,
        "link_sears": 0.20116765,
        "m": 1.0,
        "mi": 1609.344,
        "mm": 0.001,
        "nm": 1852.0,
        "nm_uk": 1853.184,
        "rod": 5.0292,
        "sears_yd": 0.91439841,
        "survey_ft": 0.304800609601,
        "um": 0.000001,
        "yd": 0.9144,
    }

    # Unit aliases for `UNIT` terms encountered in Spatial Reference WKT.
    ALIAS = {
        "centimeter": "cm",
        "foot": "ft",
        "inches": "inch",
        "kilometer": "km",
        "kilometre": "km",
        "meter": "m",
        "metre": "m",
        "micrometer": "um",
        "micrometre": "um",
        "millimeter": "mm",
        "millimetre": "mm",
        "mile": "mi",
        "yard": "yd",
        "British chain (Benoit 1895 B)": "british_chain_benoit",
        "British chain (Sears 1922)": "british_chain_sears",
        "British chain (Sears 1922 truncated)": "british_chain_sears_truncated",
        "British foot (Sears 1922)": "british_ft",
        "British foot": "british_ft",
        "British yard (Sears 1922)": "british_yd",
        "British yard": "british_yd",
        "Clarke's Foot": "clarke_ft",
        "Clarke's link": "clarke_link",
        "Chain (Benoit)": "chain_benoit",
        "Chain (Sears)": "chain_sears",
        "Foot (International)": "ft",
        "Furrow Long": "furlong",
        "German legal metre": "german_m",
        "Gold Coast foot": "gold_coast_ft",
        "Indian yard": "indian_yd",
        "Link (Benoit)": "link_benoit",
        "Link (Sears)": "link_sears",
        "Nautical Mile": "nm",
        "Nautical Mile (UK)": "nm_uk",
        "US survey foot": "survey_ft",
        "U.S. Foot": "survey_ft",
        "Yard (Indian)": "indian_yd",
        "Yard (Sears)": "sears_yd",
    }
    LALIAS = {k.lower(): v for k, v in ALIAS.items()}

    def __mul__(self, other):
        if isinstance(other, self.__class__):
            return Area(
                default_unit=AREA_PREFIX + self._default_unit,
                **{AREA_PREFIX + self.STANDARD_UNIT: (self.standard * other.standard)},
            )
        elif isinstance(other, NUMERIC_TYPES):
            return self.__class__(
                default_unit=self._default_unit,
                **{self.STANDARD_UNIT: (self.standard * other)},
            )
        else:
            raise TypeError(
                "%(distance)s must be multiplied with number or %(distance)s"
                % {
                    "distance": pretty_name(self.__class__),
                }
            )


class Area(MeasureBase):
    STANDARD_UNIT = AREA_PREFIX + Distance.STANDARD_UNIT
    # Getting the square units values and the alias dictionary.
    UNITS = {"%s%s" % (AREA_PREFIX, k): v**2 for k, v in Distance.UNITS.items()}
    ALIAS = {k: "%s%s" % (AREA_PREFIX, v) for k, v in Distance.ALIAS.items()}
    LALIAS = {k.lower(): v for k, v in ALIAS.items()}

    def __truediv__(self, other):
        if isinstance(other, NUMERIC_TYPES):
            return self.__class__(
                default_unit=self._default_unit,
                **{self.STANDARD_UNIT: (self.standard / other)},
            )
        else:
            raise TypeError(
                "%(class)s must be divided by a number" % {"class": pretty_name(self)}
            )


# Shortcuts
D = Distance
A = Area
