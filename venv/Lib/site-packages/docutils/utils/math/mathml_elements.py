# :Id: $Id: mathml_elements.py 10136 2025-05-20 15:48:27Z milde $
# :Copyright: 2024 Günter Milde.
#
# :License: Released under the terms of the `2-Clause BSD license`_, in short:
#
#    Copying and distribution of this file, with or without modification,
#    are permitted in any medium without royalty provided the copyright
#    notice and this notice are preserved.
#    This file is offered as-is, without any warranty.
#
# .. _2-Clause BSD license: https://opensource.org/licenses/BSD-2-Clause

"""MathML element classes based on `xml.etree`.

The module is intended for programmatic generation of MathML
and covers the part of `MathML Core`_ that is required by
Docutil's *TeX math to MathML* converter.

This module is PROVISIONAL:
the API is not settled and may change with any minor Docutils version.

.. _MathML Core: https://www.w3.org/TR/mathml-core/
"""

from __future__ import annotations

__docformat__ = 'reStructuredText'

# Usage:
#
# >>> from mathml_elements import *

import numbers
import xml.etree.ElementTree as ET


GLOBAL_ATTRIBUTES = (
    'class',  # space-separated list of element classes
    # 'data-*',  # custom data attributes (see HTML)
    'dir',  # directionality ('ltr', 'rtl')
    'displaystyle',  # True: normal, False: compact
    'id',  # unique identifier
    # 'mathbackground',  # color definition, deprecated
    # 'mathcolor',  # color definition, deprecated
    # 'mathsize',  # font-size, deprecated
    'nonce',  # cryptographic nonce ("number used once")
    'scriptlevel',  # math-depth for the element
    'style',  # CSS styling declarations
    'tabindex',  # indicate if the element takes input focus
    )
"""Global MathML attributes

https://w3c.github.io/mathml-core/#global-attributes
"""


# Base classes
# ------------

class MathElement(ET.Element):
    """Base class for MathML elements."""

    nchildren = None
    """Expected number of children or None"""
    # cf. https://www.w3.org/TR/MathML3/chapter3.html#id.3.1.3.2
    parent = None
    """Parent node in MathML element tree."""

    def __init__(self, *children, **attributes) -> None:
        """Set up node with `children` and `attributes`.

        Attribute names are normalised to lowercase.
        You may use "CLASS" to set a "class" attribute.
        Attribute values are converted to strings
        (with True -> "true" and False -> "false").

        >>> math(CLASS='test', level=3, split=True)
        math(class='test', level='3', split='true')
        >>> math(CLASS='test', level=3, split=True).toxml()
        '<math class="test" level="3" split="true"></math>'

        """
        attrib = {k.lower(): self.a_str(v) for k, v in attributes.items()}
        super().__init__(self.__class__.__name__, **attrib)
        self.extend(children)

    @staticmethod
    def a_str(v):
        # Return string representation for attribute value `v`.
        if isinstance(v, bool):
            return str(v).lower()
        return str(v)

    def __repr__(self) -> str:
        """Return full string representation."""
        args = [repr(child) for child in self]
        if self.text:
            args.append(repr(self.text))
        if self.nchildren != self.__class__.nchildren:
            args.append(f'nchildren={self.nchildren}')
        if getattr(self, 'switch', None):
            args.append('switch=True')
        args += [f'{k}={v!r}' for k, v in self.items() if v is not None]
        return f'{self.tag}({", ".join(args)})'

    def __str__(self) -> str:
        """Return concise, informal string representation."""
        if self.text:
            args = repr(self.text)
        else:
            args = ', '.join(f'{child}' for child in self)
        return f'{self.tag}({args})'

    def set(self, key, value) -> None:
        super().set(key, self.a_str(value))

    def __setitem__(self, key, value) -> None:
        if self.nchildren == 0:
            raise TypeError(f'Element "{self}" does not take children.')
        if isinstance(value, MathElement):
            value.parent = self
        else:  # value may be an iterable
            if self.nchildren and len(self) + len(value) > self.nchildren:
                raise TypeError(f'Element "{self}" takes only {self.nchildren}'
                                ' children')
            for e in value:
                e.parent = self
        super().__setitem__(key, value)

    def is_full(self):
        """Return boolean indicating whether children may be appended."""
        return self.nchildren is not None and len(self) >= self.nchildren

    def close(self):
        """Close element and return first non-full anchestor or None."""
        self.nchildren = len(self)  # mark node as full
        parent = self.parent
        while parent is not None and parent.is_full():
            parent = parent.parent
        return parent

    def append(self, element):
        """Append `element` and return new "current node" (insertion point).

        Append as child element and set the internal `parent` attribute.

        If self is already full, raise TypeError.

        If self is full after appending, call `self.close()`
        (returns first non-full anchestor or None) else return `self`.
        """
        if self.is_full():
            if self.nchildren:
                status = f'takes only {self.nchildren} children'
            else:
                status = 'does not take children'
            raise TypeError(f'Element "{self}" {status}.')
        super().append(element)
        element.parent = self
        if self.is_full():
            return self.close()
        return self

    def extend(self, elements):
        """Sequentially append `elements`. Return new "current node".

        Raise TypeError if overfull.
        """
        current_node = self
        for element in elements:
            current_node = self.append(element)
        return current_node

    def pop(self, index=-1):
        element = self[index]
        del self[index]
        return element

    def in_block(self):
        """Return True, if `self` or an ancestor has ``display='block'``.

        Used to find out whether we are in inline vs. displayed maths.
        """
        if self.get('display') is None:
            try:
                return self.parent.in_block()
            except AttributeError:
                return False
        return self.get('display') == 'block'

    # XML output:

    def indent_xml(self, space='  ', level=0) -> None:
        """Format XML output with indents.

        Use with care:
          Formatting whitespace is permanently added to the
          `text` and `tail` attributes of `self` and anchestors!
        """
        ET.indent(self, space, level)

    def unindent_xml(self) -> None:
        """Strip whitespace at the end of `text` and `tail` attributes...

        to revert changes made by the `indent_xml()` method.
        Use with care, trailing whitespace from the original may be lost.
        """
        for e in self.iter():
            if not isinstance(e, MathToken) and e.text:
                e.text = e.text.rstrip()
            if e.tail:
                e.tail = e.tail.rstrip()

    def toxml(self, encoding=None):
        """Return an XML representation of the element.

        By default, the return value is a `str` instance. With an explicit
        `encoding` argument, the result is a `bytes` instance in the
        specified encoding. The XML default encoding is UTF-8, any other
        encoding must be specified in an XML document header.

        Name and encoding handling match `xml.dom.minidom.Node.toxml()`
        while `etree.Element.tostring()` returns `bytes` by default.
        """
        xml = ET.tostring(self, encoding or 'unicode',
                          short_empty_elements=False)
        # Visible representation for "Apply Function" character:
        try:
            xml = xml.replace('\u2061', '&ApplyFunction;')
        except TypeError:
            xml = xml.replace('\u2061'.encode(encoding), b'&ApplyFunction;')
        return xml


# Group sub-expressions in a horizontal row
#
# The elements <msqrt>, <mstyle>, <merror>, <mpadded>, <mphantom>,
# <menclose>, <mtd>, <mscarry>, and <math> treat their contents
# as a single inferred mrow formed from all their children.
# (https://www.w3.org/TR/mathml4/#presm_inferredmrow)
#
# MathML Core uses the term "anonymous mrow element".

class MathRow(MathElement):
    """Base class for elements treating content as a single mrow."""


# 2d Schemata

class MathSchema(MathElement):
    """Base class for schemata expecting 2 or more children.

    The special attribute `switch` indicates that the last two child
    elements are in reversed order and must be switched before XML-export.
    See `msub` for an example.
    """
    nchildren = 2

    def __init__(self, *children, **kwargs) -> None:
        self.switch = kwargs.pop('switch', False)
        super().__init__(*children, **kwargs)

    def append(self, element):
        """Append element. Normalize order and close if full."""
        current_node = super().append(element)
        if self.switch and self.is_full():
            self[-1], self[-2] = self[-2], self[-1]
            self.switch = False
        return current_node


# Token elements represent the smallest units of mathematical notation which
# carry meaning.

class MathToken(MathElement):
    """Token Element: contains textual data instead of children.

    Expect text data on initialisation.
    """
    nchildren = 0

    def __init__(self, text, **attributes) -> None:
        super().__init__(**attributes)
        if not isinstance(text, (str, numbers.Number)):
            raise ValueError('MathToken element expects `str` or number,'
                             f' not "{text}".')
        self.text = str(text)


# MathML element classes
# ----------------------

class math(MathRow):
    """Top-level MathML element, a single mathematical formula."""


# Token elements
# ~~~~~~~~~~~~~~

class mtext(MathToken):
    """Arbitrary text with no notational meaning."""


class mi(MathToken):
    """Identifier, such as a function name, variable or symbolic constant."""


class mn(MathToken):
    """Numeric literal.

    >>> mn(3.41).toxml()
    '<mn>3.41</mn>'

    Normally a sequence of digits with a possible separator (a dot or a comma).
    (Values with comma must be specified as `str`.)
    """


class mo(MathToken):
    """Operator, Fence, Separator, or Accent.

    >>> mo('<').toxml()
    '<mo>&lt;</mo>'

    Besides operators in strict mathematical meaning, this element also
    includes "operators" like parentheses, separators like comma and
    semicolon, or "absolute value" bars.
    """


class mspace(MathElement):
    """Blank space, whose size is set by its attributes.

    Takes additional attributes `depth`, `height`, `width`.
    Takes no children and no text.

    See also `mphantom`.
    """
    nchildren = 0


# General Layout Schemata
# ~~~~~~~~~~~~~~~~~~~~~~~

class mrow(MathRow):
    """Generic element to group children as a horizontal row.

    Removed on closing if not required (see `mrow.close()`).
    """

    def transfer_attributes(self, other) -> None:
        """Transfer attributes from self to other.

        "List values" (class, style) are appended to existing values,
        other values replace existing values.
        """
        delimiters = {'class': ' ', 'style': '; '}
        for k, v in self.items():
            if k in ('class', 'style') and v:
                if other.get(k):
                    v = delimiters[k].join(
                        (other.get(k).rstrip(delimiters[k]), v))
            other.set(k, v)

    def close(self):
        """Close element and return first non-full anchestor or None.

        Remove <mrow> if it has only one child element.
        """
        parent = self.parent
        # replace `self` with single child
        if parent is not None and len(self) == 1:
            child = self[0]
            try:
                parent[list(parent).index(self)] = child
                child.parent = parent
            except (AttributeError, ValueError):
                return None
            self.transfer_attributes(child)
        return super().close()


class mfrac(MathSchema):
    """Fractions or fraction-like objects such as binomial coefficients."""


class msqrt(MathRow):
    """Square root. See also `mroot`."""
    nchildren = 1  # \sqrt expects one argument or a group


class mroot(MathSchema):
    """Roots with an explicit index. See also `msqrt`."""


class mstyle(MathRow):
    """Style Change.

    In modern browsers, <mstyle> is equivalent to an <mrow> element.
    However, <mstyle> may still be relevant for compatibility with
    MathML implementations outside browsers.
    """


class merror(MathRow):
    """Display contents as error messages."""


class menclose(MathRow):
    """Renders content inside an enclosing notation...

    ... specified by the notation attribute.

    Non-standard but still required by Firefox for boxed expressions.
    """
    nchildren = 1  # \boxed expects one argument or a group


class mpadded(MathRow):
    """Adjust space around content."""
    # nchildren = 1  # currently not used by latex2mathml


class mphantom(MathRow):
    """Placeholder: Rendered invisibly but dimensions are kept."""
    nchildren = 1  # \phantom expects one argument or a group


# Script and Limit Schemata
# ~~~~~~~~~~~~~~~~~~~~~~~~~

class msub(MathSchema):
    """Attach a subscript to an expression."""


class msup(MathSchema):
    """Attach a superscript to an expression."""


class msubsup(MathSchema):
    """Attach both a subscript and a superscript to an expression."""
    nchildren = 3

# Examples:
#
# The `switch` attribute reverses the order of the last two children:
# >>> msub(mn(1), mn(2)).toxml()
# '<msub><mn>1</mn><mn>2</mn></msub>'
# >>> msub(mn(1), mn(2), switch=True).toxml()
# '<msub><mn>2</mn><mn>1</mn></msub>'
#
# >>> msubsup(mi('base'), mn(1), mn(2)).toxml()
# '<msubsup><mi>base</mi><mn>1</mn><mn>2</mn></msubsup>'
# >>> msubsup(mi('base'), mn(1), mn(2), switch=True).toxml()
# '<msubsup><mi>base</mi><mn>2</mn><mn>1</mn></msubsup>'


class munder(msub):
    """Attach an accent or a limit under an expression."""


class mover(msup):
    """Attach an accent or a limit over an expression."""


class munderover(msubsup):
    """Attach accents or limits both under and over an expression."""


# Tabular Math
# ~~~~~~~~~~~~

class mtable(MathElement):
    """Table or matrix element."""


class mtr(MathRow):
    """Row in a table or a matrix."""


class mtd(MathRow):
    """Cell in a table or a matrix"""
