# -*- coding: utf-8 -*-
"""
    pygments.styles.rrt
    ~~~~~~~~~~~~~~~~~~~

    pygments "rrt" theme, based on Zap and Emacs defaults.

    :copyright: Copyright 2006-2017 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from pygments.style import Style
from pygments.token import Comment, Name, Keyword, String


class RrtStyle(Style):
    """
    Minimalistic "rrt" theme, based on Zap and Emacs defaults.
    """

    background_color = '#000000'
    highlight_color = '#0000ff'

    styles = {
        Comment:            '#00ff00',
        Name.Function:      '#ffff00',
        Name.Variable:      '#eedd82',
        Name.Constant:      '#7fffd4',
        Keyword:            '#ff0000',
        Comment.Preproc:    '#e5e5e5',
        String:             '#87ceeb',
        Keyword.Type:       '#ee82ee',
    }
