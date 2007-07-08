"""
Distance and Area objects to allow for sensible and convienient calculation 
and conversions.

Inspired by GeoPy (http://exogen.case.edu/projects/geopy/)
and Geoff Biggs' PhD work on dimensioned units for robotics.

Copyright (c) 2007, Robert Coup <robert.coup@onetrackmind.co.nz>
"""

from math import *
from decimal import Decimal

class Distance(object):
    UNITS = {
        'm': 1.0,
        'km': 1000.0,
        'mi': 1609.344,
        'ft': 0.3048,
        'yd': 0.9144,
        'nm': 1852.0,
    }

    def __init__(self, default_unit=None, **kwargs):
        self.m = 0.0
        self._default_unit = 'm'
        
        for unit,value in kwargs.items():
            if unit in self.UNITS:
                self.m += self.UNITS[unit] * value
                self._default_unit = unit
            else:
                raise AttributeError("Unknown unit type: " + unit)

        if default_unit:
            self._default_unit = default_unit
    
    def __getattr__(self, name):
        if name in self.UNITS:
            return self.m / self.UNITS[name]
        else:
            raise AttributeError("Unknown unit type: " + name)
    
    def __repr__(self):
        return "Distance(%s=%s)" % (self._default_unit, getattr(self, self._default_unit))

    def __str__(self):
        return "%s %s" % (getattr(self, self._default_unit), self._default_unit)
        
    def __cmp__(self, other):
        if isinstance(other, Distance):
            return cmp(self.m, other.m)
        else:
            return NotImplemented
        
    def __add__(self, other):
        if isinstance(other, Distance):
            return Distance(default_unit=self._default_unit, m=(self.m + other.m))
        else:
            raise TypeError("Distance must be added with Distance")
    
    def __iadd__(self, other):
        if isinstance(other, Distance):
            self.m += other.m
            return self
        else:
            raise TypeError("Distance must be added with Distance")
    
    def __sub__(self, other):
        if isinstance(other, Distance):
            return Distance(default_unit=self._default_unit, m=(self.m - other.m))
        else:
            raise TypeError("Distance must be subtracted from Distance")
    
    def __isub__(self, other):
        if isinstance(other, Distance):
            self.m -= other.m
            return self
        else:
            raise TypeError("Distance must be subtracted from Distance")
    
    def __mul__(self, other):
        if isinstance(other, (int, float, long, Decimal)):
            return Distance(default_unit=self._default_unit, m=(self.m * float(other)))
        elif isinstance(other, Distance):
            return Area(default_unit='sq_' + self._default_unit, sq_m=(self.m * other.m))
        else:
            raise TypeError("Distance must be multiplied with number or Distance")
    
    def __imul__(self, other):
        if isinstance(other, (int, float, long, Decimal)):
            self.m *= float(other)
            return self
        else:
            raise TypeError("Distance must be multiplied with number")
    
    def __div__(self, other):
        if isinstance(other, (int, float, long, Decimal)):
            return Distance(default_unit=self._default_unit, m=(self.m / float(other)))
        else:
            raise TypeError("Distance must be divided with number")

    def __idiv__(self, other):
        if isinstance(other, (int, float, long, Decimal)):
            self.m /= float(other)
            return self
        else:
            raise TypeError("Distance must be divided with number")

    def __nonzero__(self):
        return bool(self.m)

class Area(object):
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
                raise AttributeError("Unknown unit type: " + unit)

        if default_unit:
            self._default_unit = default_unit
    
    def __getattr__(self, name):
        if name in self.UNITS:
            return self.sq_m / self.UNITS[name]
        else:
            raise AttributeError("Unknown unit type: " + name)
    
    def __repr__(self):
        return "Area(%s=%s)" % (self._default_unit, getattr(self, self._default_unit))

    def __str__(self):
        return "%s %s" % (getattr(self, self._default_unit), self._default_unit)

    def __cmp__(self, other):
        if isinstance(other, Area):
            return cmp(self.sq_m, other.sq_m)
        else:
            return NotImplemented
        
    def __add__(self, other):
        if isinstance(other, Area):
            return Area(default_unit=self._default_unit, sq_m=(self.sq_m + other.sq_m))
        else:
            raise TypeError("Area must be added with Area")
    
    def __iadd__(self, other):
        if isinstance(other, Area):
            self.sq_m += other.sq_m
            return self
        else:
            raise TypeError("Area must be added with Area")
    
    def __sub__(self, other):
        if isinstance(other, Area):
            return Area(default_unit=self._default_unit, sq_m=(self.sq_m - other.sq_m))
        else:
            raise TypeError("Area must be subtracted from Area")
    
    def __isub__(self, other):
        if isinstance(other, Area):
            self.sq_m -= other.sq_m
            return self
        else:
            raise TypeError("Area must be subtracted from Area")
    
    def __mul__(self, other):
        if isinstance(other, (int, float, long, Decimal)):
            return Area(default_unit=self._default_unit, sq_m=(self.sq_m * float(other)))
        else:
            raise TypeError("Area must be multiplied with number")
    
    def __imul__(self, other):
        if isinstance(other, (int, float, long, Decimal)):
            self.sq_m *= float(other)
            return self
        else:
            raise TypeError("Area must be multiplied with number")
    
    def __div__(self, other):
        if isinstance(other, (int, float, long, Decimal)):
            return Area(default_unit=self._default_unit, sq_m=(self.sq_m / float(other)))
        else:
            raise TypeError("Area must be divided with number")

    def __idiv__(self, other):
        if isinstance(other, (int, float, long, Decimal)):
            self.sq_m /= float(other)
            return self
        else:
            raise TypeError("Area must be divided with number")

    def __nonzero__(self):
        return bool(self.sq_m)

        
# Shortcuts
D = Distance
A = Area
