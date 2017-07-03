# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

import sys
from datetime import time
from unittest import skipIf

from django.forms import TimeInput
from django.test import override_settings
from django.utils import translation

from .base import WidgetTest


class TimeInputTest(WidgetTest):
    widget = TimeInput()

    def test_render_none(self):
        self.check_html(self.widget, 'time', None, html='<input type="text" name="time" />')

    def test_render_value(self):
        """
        The microseconds are trimmed on display, by default.
        """
        t = time(12, 51, 34, 482548)
        self.assertEqual(str(t), '12:51:34.482548')
        self.check_html(self.widget, 'time', t, html='<input type="text" name="time" value="12:51:34" />')
        self.check_html(self.widget, 'time', time(12, 51, 34), html=(
            '<input type="text" name="time" value="12:51:34" />'
        ))
        self.check_html(self.widget, 'time', time(12, 51), html=(
            '<input type="text" name="time" value="12:51:00" />'
        ))

    def test_string(self):
        """
        We should be able to initialize from a unicode value.
        """
        self.check_html(self.widget, 'time', '13:12:11', html=(
            '<input type="text" name="time" value="13:12:11" />'
        ))

    def test_format(self):
        """
        Use 'format' to change the way a value is displayed.
        """
        t = time(12, 51, 34, 482548)
        widget = TimeInput(format='%H:%M', attrs={'type': 'time'})
        self.check_html(widget, 'time', t, html='<input type="time" name="time" value="12:51" />')

    # Test fails on Windows due to http://bugs.python.org/issue8304#msg222667
    @skipIf(sys.platform.startswith('win'), 'Fails with UnicodeEncodeError error on Windows.')
    def test_non_ascii_format(self):
        widget = TimeInput(format='τ-%H:%M')
        self.check_html(widget, 'time', time(10, 10), '<input type="text" name="time" value="\u03c4-10:10" />')

    @override_settings(USE_L10N=True)
    @translation.override('de-at')
    def test_l10n(self):
        t = time(12, 51, 34, 482548)
        self.check_html(self.widget, 'time', t, html='<input type="text" name="time" value="12:51:34" />')
