# $Id$
# Author: Adam Turner.
# Copyright: This module is placed in the public domain
#            or under the `Zero Clause BSD licence`_,
#            whichever is more permissive.
#
# .. _Zero Clause BSD licence: https://opensource.org/license/0BSD

"""Conversion between integers and roman numerals."""

from __future__ import annotations

import sys

TYPE_CHECKING = False
if TYPE_CHECKING:
    from typing import Final, final

    from docutils.utils._typing import Self
else:
    from docutils.utils._typing import final


__all__: Final = (
    'MAX',
    'MIN',
    'InvalidRomanNumeralError',
    'OutOfRangeError',
    'RomanNumeral',
)

MIN: Final = 1
"""The value of the smallest well-formed roman numeral."""

# Note that 4,999 (MMMMCMXCIX) breaks one of the rules of Roman numerals,
# that the same character may not appear more than thrice consecutively,
# meaning the largest 'well-formed' Roman numeral is 3,999 (MMMCMXCIX).
# We use 4,999 for backwards compatibility reasons.
MAX: Final = 4_999
"""The value of the largest well-formed roman numeral."""


@final
class OutOfRangeError(TypeError):
    """Number out of range (must be between 1 and 4,999)."""


@final
class InvalidRomanNumeralError(ValueError):
    """Not a valid Roman numeral."""

    def __init__(self, value: str, *args: object) -> None:
        msg = f'Invalid Roman numeral: {value}'
        super().__init__(msg, *args)


@final
class RomanNumeral:
    """A Roman numeral.

    Only values between 1 and 4,999 are valid.
    Stores the value internally as an ``int``.

    >>> answer = RomanNumeral(42)
    >>> print(answer.to_uppercase())
    XLII
    """

    __slots__ = ('_value',)
    _value: int

    def __init__(self, value: int, /) -> None:
        if not isinstance(value, int):
            value_qualname = type(value).__qualname__
            msg = f'RomanNumeral: an integer is required, not {value_qualname!r}'  # NoQA: E501
            raise TypeError(msg)
        if value < MIN or value > MAX:
            msg = f'Number out of range (must be between 1 and 4,999). Got {value}.'  # NoQA: E501
            raise OutOfRangeError(msg)
        super().__setattr__('_value', value)

    def __int__(self) -> int:
        """Return the integer value of this numeral."""
        return self._value

    def __str__(self) -> str:
        """Return the well-formed (uppercase) string for this numeral."""
        return self.to_uppercase()

    def __repr__(self) -> str:
        """Return the string representation of this numeral."""
        return f'{self.__class__.__name__}({self._value!r})'

    def __eq__(self, other: object) -> bool:
        """Return self == other."""
        if isinstance(other, RomanNumeral):
            return self._value == other._value
        return NotImplemented

    def __lt__(self, other: object) -> bool:
        """Return self < other."""
        if isinstance(other, RomanNumeral):
            return self._value < other._value
        return NotImplemented

    def __hash__(self) -> int:
        """Return the hashed value of this numeral."""
        return hash(self._value)

    def __setattr__(self, key: str, value: object) -> None:
        """Implement setattr(self, name, value)."""
        if key == '_value':
            msg = f'Cannot set the {key!r} attribute.'
            raise AttributeError(msg)
        super().__setattr__(key, value)

    def to_uppercase(self) -> str:
        """Convert a ``RomanNumeral`` to an uppercase string.

        >>> answer = RomanNumeral(42)
        >>> assert answer.to_uppercase() == 'XLII'
        """
        out: list[str] = []
        n = self._value
        for value, name, _ in _ROMAN_NUMERAL_PREFIXES:
            while n >= value:
                n -= value
                out.append(name)
        return ''.join(out)

    def to_lowercase(self) -> str:
        """Convert a ``RomanNumeral`` to a lowercase string.

        >>> answer = RomanNumeral(42)
        >>> assert answer.to_lowercase() == 'xlii'
        """
        out: list[str] = []
        n = self._value
        for value, _, name in _ROMAN_NUMERAL_PREFIXES:
            while n >= value:
                n -= value
                out.append(name)
        return ''.join(out)

    @classmethod
    def from_string(cls, string: str, /) -> Self:
        """Create a ``RomanNumeral`` from a well-formed string representation.

        Returns ``RomanNumeral`` or raises ``InvalidRomanNumeralError``.

        >>> answer = RomanNumeral.from_string('XLII')
        >>> assert int(answer) == 42
        """
        # Not an empty string.
        if not string or not isinstance(string, str):
            raise InvalidRomanNumeralError(string)

        # ASCII-only uppercase string.
        if string.isascii() and string.isupper():
            chars = string.encode('ascii')
        elif string.isascii() and string.islower():
            chars = string.upper().encode('ascii')
        else:
            # Either Non-ASCII or mixed-case ASCII.
            raise InvalidRomanNumeralError(string)

        # ASCII-only uppercase string only containing I, V, X, L, C, D, M.
        if not frozenset(b'IVXLCDM').issuperset(chars):
            raise InvalidRomanNumeralError(string)

        result: int = 0
        idx: int = 0

        # Thousands: between 0 and 4 "M" characters at the start
        for _ in range(4):
            if chars[idx:idx + 1] == b'M':
                result += 1000
                idx += 1
            else:
                break
        if len(chars) == idx:
            return cls(result)

        # Hundreds: 900 ("CM"), 400 ("CD"), 0-300 (0 to 3 "C" chars),
        # or 500-800 ("D", followed by 0 to 3 "C" chars)
        if chars[idx:idx + 2] == b'CM':
            result += 900
            idx += 2
        elif chars[idx:idx + 2] == b'CD':
            result += 400
            idx += 2
        else:
            if chars[idx:idx + 1] == b'D':
                result += 500
                idx += 1
            for _ in range(3):
                if chars[idx:idx + 1] == b'C':
                    result += 100
                    idx += 1
                else:
                    break
        if len(chars) == idx:
            return cls(result)

        # Tens: 90 ("XC"), 40 ("XL"), 0-30 (0 to 3 "X" chars),
        # or 50-80 ("L", followed by 0 to 3 "X" chars)
        if chars[idx:idx + 2] == b'XC':
            result += 90
            idx += 2
        elif chars[idx:idx + 2] == b'XL':
            result += 40
            idx += 2
        else:
            if chars[idx:idx + 1] == b'L':
                result += 50
                idx += 1
            for _ in range(3):
                if chars[idx:idx + 1] == b'X':
                    result += 10
                    idx += 1
                else:
                    break
        if len(chars) == idx:
            return cls(result)

        # Ones: 9 ("IX"), 4 ("IV"), 0-3 (0 to 3 "I" chars),
        # or 5-8 ("V", followed by 0 to 3 "I" chars)
        if chars[idx:idx + 2] == b'IX':
            result += 9
            idx += 2
        elif chars[idx:idx + 2] == b'IV':
            result += 4
            idx += 2
        else:
            if chars[idx:idx + 1] == b'V':
                result += 5
                idx += 1
            for _ in range(3):
                if chars[idx:idx + 1] == b'I':
                    result += 1
                    idx += 1
                else:
                    break
        if len(chars) == idx:
            return cls(result)
        raise InvalidRomanNumeralError(string)


_ROMAN_NUMERAL_PREFIXES: Final = [
    (1000, sys.intern('M'), sys.intern('m')),
    (900, sys.intern('CM'), sys.intern('cm')),
    (500, sys.intern('D'), sys.intern('d')),
    (400, sys.intern('CD'), sys.intern('cd')),
    (100, sys.intern('C'), sys.intern('c')),
    (90, sys.intern('XC'), sys.intern('xc')),
    (50, sys.intern('L'), sys.intern('l')),
    (40, sys.intern('XL'), sys.intern('xl')),
    (10, sys.intern('X'), sys.intern('x')),
    (9, sys.intern('IX'), sys.intern('ix')),
    (5, sys.intern('V'), sys.intern('v')),
    (4, sys.intern('IV'), sys.intern('iv')),
    (1, sys.intern('I'), sys.intern('i')),
]
"""Numeral value, uppercase character, and lowercase character."""
