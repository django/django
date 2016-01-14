# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.forms import TextInput
from django.utils.safestring import mark_safe

from .base import WidgetTest


class TextInputTest(WidgetTest):
    widget = TextInput()

    def test_render(self):
        self.check_html(self.widget, 'email', '', html='<input type="text" name="email" />')

    def test_render_none(self):
        self.check_html(self.widget, 'email', None, html='<input type="text" name="email" />')

    def test_render_value(self):
        self.check_html(self.widget, 'email', 'test@example.com', html=(
            '<input type="text" name="email" value="test@example.com" />'
        ))

    def test_render_boolean(self):
        """
        Boolean values are rendered to their string forms ("True" and
        "False").
        """
        self.check_html(self.widget, 'get_spam', False, html=(
            '<input type="text" name="get_spam" value="False" />'
        ))
        self.check_html(self.widget, 'get_spam', True, html=(
            '<input type="text" name="get_spam" value="True" />'
        ))

    def test_render_quoted(self):
        self.check_html(
            self.widget, 'email', 'some "quoted" & ampersanded value',
            html='<input type="text" name="email" value="some &quot;quoted&quot; &amp; ampersanded value" />',
        )

    def test_render_custom_attrs(self):
        self.check_html(
            self.widget, 'email', 'test@example.com', attrs={'class': 'fun'},
            html='<input type="text" name="email" value="test@example.com" class="fun" />',
        )

    def test_render_unicode(self):
        self.check_html(
            self.widget, 'email', 'ŠĐĆŽćžšđ', attrs={'class': 'fun'},
            html=(
                '<input type="text" name="email" '
                'value="\u0160\u0110\u0106\u017d\u0107\u017e\u0161\u0111" class="fun" />'
            ),
        )

    def test_constructor_attrs(self):
        widget = TextInput(attrs={'class': 'fun', 'type': 'email'})
        self.check_html(widget, 'email', '', html='<input type="email" class="fun" name="email" />')
        self.check_html(
            widget, 'email', 'foo@example.com',
            html='<input type="email" class="fun" value="foo@example.com" name="email" />',
        )

    def test_attrs_precedence(self):
        """
        `attrs` passed to render() get precedence over those passed to the
        constructor
        """
        widget = TextInput(attrs={'class': 'pretty'})
        self.check_html(
            widget, 'email', '', attrs={'class': 'special'},
            html='<input type="text" class="special" name="email" />',
        )

    def test_attrs_safestring(self):
        widget = TextInput(attrs={'onBlur': mark_safe("function('foo')")})
        self.check_html(widget, 'email', '', html='<input onBlur="function(\'foo\')" type="text" name="email" />')
