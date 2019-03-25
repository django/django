# -*- coding: utf-8 -*-
"""
    sphinx.pygments_styles
    ~~~~~~~~~~~~~~~~~~~~~~

    Sphinx theme specific highlighting styles.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from pygments.style import Style
from pygments.styles.friendly import FriendlyStyle
from pygments.token import Generic, Comment, Number, Whitespace, Keyword, \
    Operator, Name, String, Error


class NoneStyle(Style):
    """Style without any styling."""


class SphinxStyle(Style):
    """
    Like friendly, but a bit darker to enhance contrast on the green
    background.
    """

    background_color = '#eeffcc'
    default_style = ''

    styles = FriendlyStyle.styles
    styles.update({
        Generic.Output: '#333',
        Comment: 'italic #408090',
        Number: '#208050',
    })


class PyramidStyle(Style):
    """
    Pylons/pyramid pygments style based on friendly style, by Blaise Laflamme.
    """

    # work in progress...

    background_color = "#f8f8f8"
    default_style = ""

    styles = {
        Whitespace:                "#bbbbbb",
        Comment:                   "italic #60a0b0",
        Comment.Preproc:           "noitalic #007020",
        Comment.Special:           "noitalic bg:#fff0f0",

        Keyword:                   "bold #007020",
        Keyword.Pseudo:            "nobold",
        Keyword.Type:              "nobold #902000",

        Operator:                  "#666666",
        Operator.Word:             "bold #007020",

        Name.Builtin:              "#007020",
        Name.Function:             "#06287e",
        Name.Class:                "bold #0e84b5",
        Name.Namespace:            "bold #0e84b5",
        Name.Exception:            "#007020",
        Name.Variable:             "#bb60d5",
        Name.Constant:             "#60add5",
        Name.Label:                "bold #002070",
        Name.Entity:               "bold #d55537",
        Name.Attribute:            "#0e84b5",
        Name.Tag:                  "bold #062873",
        Name.Decorator:            "bold #555555",

        String:                    "#4070a0",
        String.Doc:                "italic",
        String.Interpol:           "italic #70a0d0",
        String.Escape:             "bold #4070a0",
        String.Regex:              "#235388",
        String.Symbol:             "#517918",
        String.Other:              "#c65d09",
        Number:                    "#40a070",

        Generic.Heading:           "bold #000080",
        Generic.Subheading:        "bold #800080",
        Generic.Deleted:           "#A00000",
        Generic.Inserted:          "#00A000",
        Generic.Error:             "#FF0000",
        Generic.Emph:              "italic",
        Generic.Strong:            "bold",
        Generic.Prompt:            "bold #c65d09",
        Generic.Output:            "#888",
        Generic.Traceback:         "#04D",

        Error:                     "#a40000 bg:#fbe3e4"
    }
