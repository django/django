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
Distance and Area objects to allow for sensible and convienient calculation 
and conversions.

Author: Robert Coup

Inspired by GeoPy (http://exogen.case.edu/projects/geopy/)
and Geoff Biggs' PhD work on dimensioned units for robotics.
"""
from decimal import Decimal

class Distance(object):
    UNITS = {
        'chain' : 20.1168,
        'chain_benoit' : 20.116782,
        'chain_sears' : 20.1167645,
        'british_chain_benoit' : 20.1167824944,
        'british_chain_sears' : 20.1167651216,
        'british_chain_sears_truncated' : 20.116756,
        'cm' : 0.01,
        'british_ft' : 0.304799471539,
        'british_yd' : 0.914398414616,
        'clarke_ft' : 0.3047972654,
        'clarke_link' : 0.201166195164,
        'fathom' :  1.8288,
        'ft': 0.3048,
        'german_m' : 1.0000135965,
        'grad' : 0.0157079632679,
        'gold_coast_ft' : 0.304799710181508,
        'indian_yd' : 0.914398530744,
        'in' : 0.0254,
        'km': 1000.0,
        'link' : 0.201168,
        'link_benoit' : 0.20116782,
        'link_sears' : 0.20116765,
        'm': 1.0,
        'mi': 1609.344,
        'mm' : 0.001,
        'nm': 1852.0,
        'nm_uk' : 1853.184,
        'rod' : 5.0292,
        'sears_yd' : 0.91439841,
        'survey_ft' : 0.304800609601,
        'um' : 0.000001,
        'yd': 0.9144,
        }

    # Unit aliases for `UNIT` terms encountered in Spatial Reference WKT.
    ALIAS = {
        'centimeter' : 'cm',
        'foot' : 'ft',
        'inches' : 'in',
        'kilometer' : 'km',
        'kilometre' : 'km',
        'meter' : 'm',
        'metre' : 'm',
        'micrometer' : 'um',
        'micrometre' : 'um',
        'millimeter' : 'mm',
        'millimetre' : 'mm',
        'mile' : 'mi',
        'yard' : 'yd',
        'British chain (Benoit 1895 B)' : 'british_chain_benoit',
        'British chain (Sears 1922)' : 'british_chain_sears',
        'British chain (Sears 1922 truncated)' : 'british_chain_sears_truncated',
        'British foot (Sears 1922)' : 'british_ft',
        'British yard (Sears 1922)' : 'british_yd',
        "Clarke's Foot" : 'clarke_ft',
        "Clarke's foot" : 'clarke_ft',
        "Clarke's link" : 'clarke_link',
        'Chain (Benoit)' : 'chain_benoit',
        'Chain (Sears)' : 'chain_sears',
        'Foot (International)' : 'ft',
        'German legal metre' : 'german_m',
        'Gold Coast foot' : 'gold_coast_ft',
        'Indian yard' : 'indian_yd',
        'Link (Benoit)': 'link_benoit',
        'Link (Sears)': 'link_sears',
        'Nautical Mile' : 'nm',
        'Nautical Mile (UK)' : 'nm_uk',
        'US survey foot' : 'survey_ft',
        'U.S. Foot' : 'survey_ft',
        'Yard (Indian)' : 'indian_yd',
        'Yard (Sears)' : 'sears_yd'
        }
    REV_ALIAS = dict((value, key) for key, value in ALIAS.items())

    def __init__(self, default_unit=None, **kwargs):
        # The base unit is in meters.
        self.m = 0.0
        self._default_unit = 'm'
        
        for unit,value in kwargs.items():
            if unit in self.UNITS:
                self.m += self.UNITS[unit] * value
                self._default_unit = unit
            elif unit in self.ALIAS:
                u = self.ALIAS[unit]
                self.m += self.UNITS[u] * value
                self._default_unit = u
            else:
                lower = unit.lower()
                if lower in self.UNITS:
                    self.m += self.UNITS[lower] * value
                    self._default_unit = lower
                elif lower in self.ALIAS:
                    u = self.ALIAS[lower]
                    self.m += self.UNITS[u] * value
                    self._default_unit = u
                else:
                    raise AttributeError('Unknown unit type: %s' % unit)

        if default_unit and isinstance(default_unit, str):
            self._default_unit = default_unit
    
    def __getattr__(self, name):
        if name in self.UNITS:
            return self.m / self.UNITS[name]
        else:
            raise AttributeError('Unknown unit type: %s' % name)
    
    def __repr__(self):
        return 'Distance(%s=%s)' % (self._default_unit, getattr(self, self._default_unit))

    def __str__(self):
        return '%s %s' % (getattr(self, self._default_unit), self._default_unit)
        
    def __cmp__(self, other):
        if isinstance(other, Distance):
            return cmp(self.m, other.m)
        else:
            return NotImplemented
        
    def __add__(self, other):
        if isinstance(other, Distance):
            return Distance(default_unit=self._default_unit, m=(self.m + other.m))
        else:
            raise TypeError('Distance must be added with Distance')
    
    def __iadd__(self, other):
        if isinstance(other, Distance):
            self.m += other.m
            return self
        else:
            raise TypeError('Distance must be added with Distance')
    
    def __sub__(self, other):
        if isinstance(other, Distance):
            return Distance(default_unit=self._default_unit, m=(self.m - other.m))
        else:
            raise TypeError('Distance must be subtracted from Distance')
    
    def __isub__(self, other):
        if isinstance(other, Distance):
            self.m -= other.m
            return self
        else:
            raise TypeError('Distance must be subtracted from Distance')
    
    def __mul__(self, other):
        if isinstance(other, (int, float, long, Decimal)):
            return Distance(default_unit=self._default_unit, m=(self.m * float(other)))
        elif isinstance(other, Distance):
            return Area(default_unit='sq_' + self._default_unit, sq_m=(self.m * other.m))
        else:
            raise TypeError('Distance must be multiplied with number or Distance')
    
    def __imul__(self, other):
        if isinstance(other, (int, float, long, Decimal)):
            self.m *= float(other)
            return self
        else:
            raise TypeError('Distance must be multiplied with number')
    
    def __div__(self, other):
        if isinstance(other, (int, float, long, Decimal)):
            return Distance(default_unit=self._default_unit, m=(self.m / float(other)))
        else:
            raise TypeError('Distance must be divided with number')

    def __idiv__(self, other):
        if isinstance(other, (int, float, long, Decimal)):
            self.m /= float(other)
            return self
        else:
            raise TypeError('Distance must be divided with number')

    def __nonzero__(self):
        return bool(self.m)

    @classmethod
    def unit_attname(cls, unit_str):
        """
        Retrieves the unit attribute name for the given unit string.  
        For example, if the given unit string is 'metre', 'm' would be returned.  
        An exception is raised if an attribute cannot be found.
        """
        lower = unit_str.lower()

        if unit_str in cls.UNITS:
            return unit_str
        elif lower in cls.UNITS:
            return lower
        elif unit_str in cls.ALIAS:
            return cls.ALIAS[unit_str]
        elif lower in cls.ALIAS:
            return cls.ALIAS[lower]
        else:
            raise Exception('Could not find a unit keyword associated with "%s"' % unit_str)

class Area(object):
    # TODO: Add units from above.
    UNITS = {
        'sq_m': 1.0,
        'sq_km': 1000000.0,
        'sq_mi': 2589988.110336,
        'sq_ft': 0.09290304,
        'sq_yd': 0.83612736,
        'sq_nm': 3429904.0,
    }

    def __init__(self, default_unit=None, **kwargs):
        self.sq_m = 0.0
        self._default_unit = 'sq_m'
        
        for unit,value in kwargs.items():
            if unit in self.UNITS:
                self.sq_m += self.UNITS[unit] * value
                self._default_unit = unit
            else:
                raise AttributeError('Unknown unit type: ' + unit)

        if default_unit:
            self._default_unit = default_unit
    
    def __getattr__(self, name):
        if name in self.UNITS:
            return self.sq_m / self.UNITS[name]
        else:
            raise AttributeError('Unknown unit type: ' + name)
    
    def __repr__(self):
        return 'Area(%s=%s)' % (self._default_unit, getattr(self, self._default_unit))

    def __str__(self):
        return '%s %s' % (getattr(self, self._default_unit), self._default_unit)

    def __cmp__(self, other):
        if isinstance(other, Area):
            return cmp(self.sq_m, other.sq_m)
        else:
            return NotImplemented
        
    def __add__(self, other):
        if isinstance(other, Area):
            return Area(default_unit=self._default_unit, sq_m=(self.sq_m + other.sq_m))
        else:
            raise TypeError('Area must be added with Area')
    
    def __iadd__(self, other):
        if isinstance(other, Area):
            self.sq_m += other.sq_m
            return self
        else:
            raise TypeError('Area must be added with Area')
    
    def __sub__(self, other):
        if isinstance(other, Area):
            return Area(default_unit=self._default_unit, sq_m=(self.sq_m - other.sq_m))
        else:
            raise TypeError('Area must be subtracted from Area')
    
    def __isub__(self, other):
        if isinstance(other, Area):
            self.sq_m -= other.sq_m
            return self
        else:
            raise TypeError('Area must be subtracted from Area')
    
    def __mul__(self, other):
        if isinstance(other, (int, float, long, Decimal)):
            return Area(default_unit=self._default_unit, sq_m=(self.sq_m * float(other)))
        else:
            raise TypeError('Area must be multiplied with number')
    
    def __imul__(self, other):
        if isinstance(other, (int, float, long, Decimal)):
            self.sq_m *= float(other)
            return self
        else:
            raise TypeError('Area must be multiplied with number')
    
    def __div__(self, other):
        if isinstance(other, (int, float, long, Decimal)):
            return Area(default_unit=self._default_unit, sq_m=(self.sq_m / float(other)))
        else:
            raise TypeError('Area must be divided with number')

    def __idiv__(self, other):
        if isinstance(other, (int, float, long, Decimal)):
            self.sq_m /= float(other)
            return self
        else:
            raise TypeError('Area must be divided with number')

    def __nonzero__(self):
        return bool(self.sq_m)

        
# Shortcuts
D = Distance
A = Area
