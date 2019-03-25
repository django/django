#!/usr/bin/env python
# -*- coding: utf-8 -*-

# :Id: $Id: latex2mathml.py 7995 2016-12-10 17:50:59Z milde $
# :Copyright: © 2010 Günter Milde.
#             Based on rst2mathml.py from the latex_math sandbox project
#             © 2005 Jens Jørgen Mortensen
# :License: Released under the terms of the `2-Clause BSD license`_, in short:
# 
#    Copying and distribution of this file, with or without modification,
#    are permitted in any medium without royalty provided the copyright
#    notice and this notice are preserved.
#    This file is offered as-is, without any warranty.
# 
# .. _2-Clause BSD license: http://www.spdx.org/licenses/BSD-2-Clause


"""Convert LaTex math code into presentational MathML"""

# Based on the `latex_math` sandbox project by Jens Jørgen Mortensen

import docutils.utils.math.tex2unichar as tex2unichar

#        TeX      spacing    combining
over = {'acute':    '\u00B4', # u'\u0301',
        'bar':      '\u00AF', # u'\u0304',
        'breve':    '\u02D8', # u'\u0306',
        'check':    '\u02C7', # u'\u030C',
        'dot':      '\u02D9', # u'\u0307',
        'ddot':     '\u00A8', # u'\u0308',
        'dddot':               '\u20DB',
        'grave':    '`',      # u'\u0300',
        'hat':      '^',      # u'\u0302',
        'mathring': '\u02DA', # u'\u030A',
        'overleftrightarrow':  '\u20e1',
        # 'overline':        # u'\u0305',
        'tilde':    '\u02DC', # u'\u0303',
        'vec':               '\u20D7'}

Greek = { # Capital Greek letters: (upright in TeX style)
    'Phi':'\u03a6', 'Xi':'\u039e', 'Sigma':'\u03a3',
    'Psi':'\u03a8', 'Delta':'\u0394', 'Theta':'\u0398',
    'Upsilon':'\u03d2', 'Pi':'\u03a0', 'Omega':'\u03a9',
    'Gamma':'\u0393', 'Lambda':'\u039b'}

letters = tex2unichar.mathalpha

special = tex2unichar.mathbin         # Binary symbols
special.update(tex2unichar.mathrel)   # Relation symbols, arrow symbols
special.update(tex2unichar.mathord)   # Miscellaneous symbols
special.update(tex2unichar.mathop)    # Variable-sized symbols
special.update(tex2unichar.mathopen)  # Braces
special.update(tex2unichar.mathclose) # Braces
special.update(tex2unichar.mathfence)

sumintprod = ''.join([special[symbol] for symbol in
                      ['sum', 'int', 'oint', 'prod']])

functions = ['arccos', 'arcsin', 'arctan', 'arg', 'cos',  'cosh',
             'cot',    'coth',   'csc',    'deg', 'det',  'dim',
             'exp',    'gcd',    'hom',    'inf', 'ker',  'lg',
             'lim',    'liminf', 'limsup', 'ln',  'log',  'max',
             'min',    'Pr',     'sec',    'sin', 'sinh', 'sup',
             'tan',    'tanh',
             'injlim',  'varinjlim', 'varlimsup',
             'projlim', 'varliminf', 'varprojlim']


mathbb = {
          'A': '\U0001D538',
          'B': '\U0001D539',
          'C': '\u2102',
          'D': '\U0001D53B',
          'E': '\U0001D53C',
          'F': '\U0001D53D',
          'G': '\U0001D53E',
          'H': '\u210D',
          'I': '\U0001D540',
          'J': '\U0001D541',
          'K': '\U0001D542',
          'L': '\U0001D543',
          'M': '\U0001D544',
          'N': '\u2115',
          'O': '\U0001D546',
          'P': '\u2119',
          'Q': '\u211A',
          'R': '\u211D',
          'S': '\U0001D54A',
          'T': '\U0001D54B',
          'U': '\U0001D54C',
          'V': '\U0001D54D',
          'W': '\U0001D54E',
          'X': '\U0001D54F',
          'Y': '\U0001D550',
          'Z': '\u2124',
         }

mathscr = {
           'A': '\U0001D49C',
           'B': '\u212C',     # bernoulli function
           'C': '\U0001D49E',
           'D': '\U0001D49F',
           'E': '\u2130',
           'F': '\u2131',
           'G': '\U0001D4A2',
           'H': '\u210B',     # hamiltonian
           'I': '\u2110',
           'J': '\U0001D4A5',
           'K': '\U0001D4A6',
           'L': '\u2112',     # lagrangian
           'M': '\u2133',     # physics m-matrix
           'N': '\U0001D4A9',
           'O': '\U0001D4AA',
           'P': '\U0001D4AB',
           'Q': '\U0001D4AC',
           'R': '\u211B',
           'S': '\U0001D4AE',
           'T': '\U0001D4AF',
           'U': '\U0001D4B0',
           'V': '\U0001D4B1',
           'W': '\U0001D4B2',
           'X': '\U0001D4B3',
           'Y': '\U0001D4B4',
           'Z': '\U0001D4B5',
           'a': '\U0001D4B6',
           'b': '\U0001D4B7',
           'c': '\U0001D4B8',
           'd': '\U0001D4B9',
           'e': '\u212F',
           'f': '\U0001D4BB',
           'g': '\u210A',
           'h': '\U0001D4BD',
           'i': '\U0001D4BE',
           'j': '\U0001D4BF',
           'k': '\U0001D4C0',
           'l': '\U0001D4C1',
           'm': '\U0001D4C2',
           'n': '\U0001D4C3',
           'o': '\u2134',     # order of
           'p': '\U0001D4C5',
           'q': '\U0001D4C6',
           'r': '\U0001D4C7',
           's': '\U0001D4C8',
           't': '\U0001D4C9',
           'u': '\U0001D4CA',
           'v': '\U0001D4CB',
           'w': '\U0001D4CC',
           'x': '\U0001D4CD',
           'y': '\U0001D4CE',
           'z': '\U0001D4CF',
          }

negatables = {'=': '\u2260',
              r'\in': '\u2209',
              r'\equiv': '\u2262'}

# LaTeX to MathML translation stuff:
class math:
    """Base class for MathML elements."""

    nchildren = 1000000
    """Required number of children"""

    def __init__(self, children=None, inline=None):
        """math([children]) -> MathML element

        children can be one child or a list of children."""

        self.children = []
        if children is not None:
            if type(children) is list:
                for child in children:
                    self.append(child)
            else:
                # Only one child:
                self.append(children)

        if inline is not None:
            self.inline = inline

    def __repr__(self):
        if hasattr(self, 'children'):
            return self.__class__.__name__ + '(%s)' % \
                   ','.join([repr(child) for child in self.children])
        else:
            return self.__class__.__name__

    def full(self):
        """Room for more children?"""

        return len(self.children) >= self.nchildren

    def append(self, child):
        """append(child) -> element

        Appends child and returns self if self is not full or first
        non-full parent."""

        assert not self.full()
        self.children.append(child)
        child.parent = self
        node = self
        while node.full():
            node = node.parent
        return node

    def delete_child(self):
        """delete_child() -> child

        Delete last child and return it."""

        child = self.children[-1]
        del self.children[-1]
        return child

    def close(self):
        """close() -> parent

        Close element and return first non-full element."""

        parent = self.parent
        while parent.full():
            parent = parent.parent
        return parent

    def xml(self):
        """xml() -> xml-string"""

        return self.xml_start() + self.xml_body() + self.xml_end()

    def xml_start(self):
        if not hasattr(self, 'inline'):
            return ['<%s>' % self.__class__.__name__]
        xmlns = 'http://www.w3.org/1998/Math/MathML'
        if self.inline:
            return ['<math xmlns="%s">' % xmlns]
        else:
            return ['<math xmlns="%s" mode="display">' % xmlns]

    def xml_end(self):
        return ['</%s>' % self.__class__.__name__]

    def xml_body(self):
        xml = []
        for child in self.children:
            xml.extend(child.xml())
        return xml

class mrow(math):
    def xml_start(self):
        return ['\n<%s>' % self.__class__.__name__]

class mtable(math):
    def xml_start(self):
        return ['\n<%s>' % self.__class__.__name__]

class mtr(mrow): pass
class mtd(mrow): pass

class mx(math):
    """Base class for mo, mi, and mn"""

    nchildren = 0
    def __init__(self, data):
        self.data = data

    def xml_body(self):
        return [self.data]

class mo(mx):
    translation = {'<': '&lt;', '>': '&gt;'}
    def xml_body(self):
        return [self.translation.get(self.data, self.data)]

class mi(mx): pass
class mn(mx): pass

class msub(math):
    nchildren = 2

class msup(math):
    nchildren = 2

class msqrt(math):
    nchildren = 1

class mroot(math):
    nchildren = 2

class mfrac(math):
    nchildren = 2

class msubsup(math):
    nchildren = 3
    def __init__(self, children=None, reversed=False):
        self.reversed = reversed
        math.__init__(self, children)

    def xml(self):
        if self.reversed:
##            self.children[1:3] = self.children[2:0:-1]
            self.children[1:3] = [self.children[2], self.children[1]]
            self.reversed = False
        return math.xml(self)

class mfenced(math):
    translation = {'\\{': '{', '\\langle': '\u2329',
                   '\\}': '}', '\\rangle': '\u232A',
                   '.': ''}
    def __init__(self, par):
        self.openpar = par
        math.__init__(self)

    def xml_start(self):
        open = self.translation.get(self.openpar, self.openpar)
        close = self.translation.get(self.closepar, self.closepar)
        return ['<mfenced open="%s" close="%s">' % (open, close)]

class mspace(math):
    nchildren = 0

class mstyle(math):
    def __init__(self, children=None, nchildren=None, **kwargs):
        if nchildren is not None:
            self.nchildren = nchildren
        math.__init__(self, children)
        self.attrs = kwargs

    def xml_start(self):
        return ['<mstyle '] + ['%s="%s"' % item
                               for item in list(self.attrs.items())] + ['>']

class mover(math):
    nchildren = 2
    def __init__(self, children=None, reversed=False):
        self.reversed = reversed
        math.__init__(self, children)

    def xml(self):
        if self.reversed:
            self.children.reverse()
            self.reversed = False
        return math.xml(self)

class munder(math):
    nchildren = 2

class munderover(math):
    nchildren = 3
    def __init__(self, children=None):
        math.__init__(self, children)

class mtext(math):
    nchildren = 0
    def __init__(self, text):
        self.text = text

    def xml_body(self):
        return [self.text]

def parse_latex_math(string, inline=True):
    """parse_latex_math(string [,inline]) -> MathML-tree

    Returns a MathML-tree parsed from string.  inline=True is for
    inline math and inline=False is for displayed math.

    tree is the whole tree and node is the current element."""

    # Normalize white-space:
    string = ' '.join(string.split())

    if inline:
        node = mrow()
        tree = math(node, inline=True)
    else:
        node = mtd()
        tree = math(mtable(mtr(node)), inline=False)

    while len(string) > 0:
        n = len(string)
        c = string[0]
        skip = 1  # number of characters consumed
        if n > 1:
            c2 = string[1]
        else:
            c2 = ''
##        print n, string, c, c2, node.__class__.__name__
        if c == ' ':
            pass
        elif c == '\\':
            if c2 in '{}':
                node = node.append(mo(c2))
                skip = 2
            elif c2 == ' ':
                node = node.append(mspace())
                skip = 2
            elif c2 == ',': # TODO: small space
                node = node.append(mspace())
                skip = 2
            elif c2.isalpha():
                # We have a LaTeX-name:
                i = 2
                while i < n and string[i].isalpha():
                    i += 1
                name = string[1:i]
                node, skip = handle_keyword(name, node, string[i:])
                skip += i
            elif c2 == '\\':
                # End of a row:
                entry = mtd()
                row = mtr(entry)
                node.close().close().append(row)
                node = entry
                skip = 2
            else:
                raise SyntaxError(r'Syntax error: "%s%s"' % (c, c2))
        elif c.isalpha():
            node = node.append(mi(c))
        elif c.isdigit():
            node = node.append(mn(c))
        elif c in "+-*/=()[]|<>,.!?':;@":
            node = node.append(mo(c))
        elif c == '_':
            child = node.delete_child()
            if isinstance(child, msup):
                sub = msubsup(child.children, reversed=True)
            elif isinstance(child, mo) and child.data in sumintprod:
                sub = munder(child)
            else:
                sub = msub(child)
            node.append(sub)
            node = sub
        elif c == '^':
            child = node.delete_child()
            if isinstance(child, msub):
                sup = msubsup(child.children)
            elif isinstance(child, mo) and child.data in sumintprod:
                sup = mover(child)
            elif (isinstance(child, munder) and
                  child.children[0].data in sumintprod):
                sup = munderover(child.children)
            else:
                sup = msup(child)
            node.append(sup)
            node = sup
        elif c == '{':
            row = mrow()
            node.append(row)
            node = row
        elif c == '}':
            node = node.close()
        elif c == '&':
            entry = mtd()
            node.close().append(entry)
            node = entry
        else:
            raise SyntaxError(r'Illegal character: "%s"' % c)
        string = string[skip:]
    return tree


def handle_keyword(name, node, string):
    skip = 0
    if len(string) > 0 and string[0] == ' ':
        string = string[1:]
        skip = 1
    if name == 'begin':
        if not string.startswith('{matrix}'):
            raise SyntaxError('Environment not supported! '
                              'Supported environment: "matrix".')
        skip += 8
        entry = mtd()
        table = mtable(mtr(entry))
        node.append(table)
        node = entry
    elif name == 'end':
        if not string.startswith('{matrix}'):
            raise SyntaxError(r'Expected "\end{matrix}"!')
        skip += 8
        node = node.close().close().close()
    elif name in ('text', 'mathrm'):
        if string[0] != '{':
            raise SyntaxError(r'Expected "\text{...}"!')
        i = string.find('}')
        if i == -1:
            raise SyntaxError(r'Expected "\text{...}"!')
        node = node.append(mtext(string[1:i]))
        skip += i + 1
    elif name == 'sqrt':
        sqrt = msqrt()
        node.append(sqrt)
        node = sqrt
    elif name == 'frac':
        frac = mfrac()
        node.append(frac)
        node = frac
    elif name == 'left':
        for par in ['(', '[', '|', '\\{', '\\langle', '.']:
            if string.startswith(par):
                break
        else:
            raise SyntaxError('Missing left-brace!')
        fenced = mfenced(par)
        node.append(fenced)
        row = mrow()
        fenced.append(row)
        node = row
        skip += len(par)
    elif name == 'right':
        for par in [')', ']', '|', '\\}', '\\rangle', '.']:
            if string.startswith(par):
                break
        else:
            raise SyntaxError('Missing right-brace!')
        node = node.close()
        node.closepar = par
        node = node.close()
        skip += len(par)
    elif name == 'not':
        for operator in negatables:
            if string.startswith(operator):
                break
        else:
            raise SyntaxError(r'Expected something to negate: "\not ..."!')
        node = node.append(mo(negatables[operator]))
        skip += len(operator)
    elif name == 'mathbf':
        style = mstyle(nchildren=1, fontweight='bold')
        node.append(style)
        node = style
    elif name == 'mathbb':
        if string[0] != '{' or not string[1].isupper() or string[2] != '}':
            raise SyntaxError(r'Expected something like "\mathbb{A}"!')
        node = node.append(mi(mathbb[string[1]]))
        skip += 3
    elif name in ('mathscr', 'mathcal'):
        if string[0] != '{' or string[2] != '}':
            raise SyntaxError(r'Expected something like "\mathscr{A}"!')
        node = node.append(mi(mathscr[string[1]]))
        skip += 3
    elif name == 'colon': # "normal" colon, not binary operator
        node = node.append(mo(':')) # TODO: add ``lspace="0pt"``
    elif name in Greek:   # Greek capitals (upright in "TeX style")
        node = node.append(mo(Greek[name]))
        # TODO: "ISO style" sets them italic. Could we use a class argument
        # to enable styling via CSS?
    elif name in letters:
        node = node.append(mi(letters[name]))
    elif name in special:
        node = node.append(mo(special[name]))
    elif name in functions:
        node = node.append(mo(name))
    elif name in over:
        ovr = mover(mo(over[name]), reversed=True)
        node.append(ovr)
        node = ovr
    else:
        raise SyntaxError('Unknown LaTeX command: ' + name)

    return node, skip

def tex2mathml(tex_math, inline=True):
    """Return string with MathML code corresponding to `tex_math`. 
    
    `inline`=True is for inline math and `inline`=False for displayed math.
    """
    
    mathml_tree = parse_latex_math(tex_math, inline=inline)
    return ''.join(mathml_tree.xml())

    
