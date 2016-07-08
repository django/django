# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import copy

from django.forms import Select
from django.utils.safestring import mark_safe

from .base import WidgetTest


class SelectTest(WidgetTest):
    widget = Select
    nested_widget = Select(choices=(
        ('outer1', 'Outer 1'),
        ('Group "1"', (('inner1', 'Inner 1'), ('inner2', 'Inner 2'))),
    ))

    def test_render(self):
        self.check_html(self.widget(choices=self.beatles), 'beatle', 'J', html=(
            """<select name="beatle">
            <option value="J" selected="selected">John</option>
            <option value="P">Paul</option>
            <option value="G">George</option>
            <option value="R">Ringo</option>
            </select>"""
        ))

    def test_render_none(self):
        """
        If the value is None, none of the options are selected.
        """
        self.check_html(self.widget(choices=self.beatles), 'beatle', None, html=(
            """<select name="beatle">
            <option value="J">John</option>
            <option value="P">Paul</option>
            <option value="G">George</option>
            <option value="R">Ringo</option>
            </select>"""
        ))

    def test_render_label_value(self):
        """
        If the value corresponds to a label (but not to an option value), none
        of the options are selected.
        """
        self.check_html(self.widget(choices=self.beatles), 'beatle', 'John', html=(
            """<select name="beatle">
            <option value="J">John</option>
            <option value="P">Paul</option>
            <option value="G">George</option>
            <option value="R">Ringo</option>
            </select>"""
        ))

    def test_render_selected(self):
        """
        Only one option can be selected (#8103).
        """
        choices = [('0', '0'), ('1', '1'), ('2', '2'), ('3', '3'), ('0', 'extra')]

        self.check_html(self.widget(choices=choices), 'choices', '0', html=(
            """<select name="choices">
            <option value="0" selected="selected">0</option>
            <option value="1">1</option>
            <option value="2">2</option>
            <option value="3">3</option>
            <option value="0">extra</option>
            </select>"""
        ))

    def test_constructor_attrs(self):
        """
        Select options shouldn't inherit the parent widget attrs.
        """
        widget = Select(
            attrs={'class': 'super', 'id': 'super'},
            choices=[(1, 1), (2, 2), (3, 3)],
        )
        self.check_html(widget, 'num', 2, html=(
            """<select name="num" class="super" id="super">
              <option value="1">1</option>
              <option value="2" selected="selected">2</option>
              <option value="3">3</option>
            </select>"""
        ))

    def test_compare_to_str(self):
        """
        The value is compared to its str().
        """
        self.check_html(
            self.widget(choices=[('1', '1'), ('2', '2'), ('3', '3')]),
            'num', 2,
            html=(
                """<select name="num">
                <option value="1">1</option>
                <option value="2" selected="selected">2</option>
                <option value="3">3</option>
                </select>"""
            ),
        )
        self.check_html(
            self.widget(choices=[(1, 1), (2, 2), (3, 3)]),
            'num', '2',
            html=(
                """<select name="num">
                <option value="1">1</option>
                <option value="2" selected="selected">2</option>
                <option value="3">3</option>
                </select>"""
            ),
        )
        self.check_html(
            self.widget(choices=[(1, 1), (2, 2), (3, 3)]),
            'num', 2,
            html=(
                """<select name="num">
                <option value="1">1</option>
                <option value="2" selected="selected">2</option>
                <option value="3">3</option>
                </select>"""
            ),
        )

    def test_choices_constuctor(self):
        widget = Select(choices=[(1, 1), (2, 2), (3, 3)])
        self.check_html(widget, 'num', 2, html=(
            """<select name="num">
            <option value="1">1</option>
            <option value="2" selected="selected">2</option>
            <option value="3">3</option>
            </select>"""
        ))

    def test_choices_constructor_generator(self):
        """
        If choices is passed to the constructor and is a generator, it can be
        iterated over multiple times without getting consumed.
        """
        def get_choices():
            for i in range(5):
                yield (i, i)

        widget = Select(choices=get_choices())
        self.check_html(widget, 'num', 2, html=(
            """<select name="num">
            <option value="0">0</option>
            <option value="1">1</option>
            <option value="2" selected="selected">2</option>
            <option value="3">3</option>
            <option value="4">4</option>
            </select>"""
        ))
        self.check_html(widget, 'num', 3, html=(
            """<select name="num">
            <option value="0">0</option>
            <option value="1">1</option>
            <option value="2">2</option>
            <option value="3" selected="selected">3</option>
            <option value="4">4</option>
            </select>"""
        ))

    def test_choices_escaping(self):
        choices = (('bad', 'you & me'), ('good', mark_safe('you &gt; me')))
        self.check_html(self.widget(choices=choices), 'escape', None, html=(
            """<select name="escape">
            <option value="bad">you &amp; me</option>
            <option value="good">you &gt; me</option>
            </select>"""
        ))

    def test_choices_unicode(self):
        self.check_html(
            self.widget(choices=[('ŠĐĆŽćžšđ', 'ŠĐabcĆŽćžšđ'), ('ćžšđ', 'abcćžšđ')]),
            'email', 'ŠĐĆŽćžšđ',
            html=(
                """<select name="email">
                <option value="\u0160\u0110\u0106\u017d\u0107\u017e\u0161\u0111" selected="selected">
                    \u0160\u0110abc\u0106\u017d\u0107\u017e\u0161\u0111
                </option>
                <option value="\u0107\u017e\u0161\u0111">abc\u0107\u017e\u0161\u0111</option>
                </select>"""
            ),
        )

    def test_choices_optgroup(self):
        """
        Choices can be nested one level in order to create HTML optgroups.
        """
        self.check_html(self.nested_widget, 'nestchoice', None, html=(
            """<select name="nestchoice">
            <option value="outer1">Outer 1</option>
            <optgroup label="Group &quot;1&quot;">
            <option value="inner1">Inner 1</option>
            <option value="inner2">Inner 2</option>
            </optgroup>
            </select>"""
        ))

    def test_choices_select_outer(self):
        self.check_html(self.nested_widget, 'nestchoice', 'outer1', html=(
            """<select name="nestchoice">
            <option value="outer1" selected="selected">Outer 1</option>
            <optgroup label="Group &quot;1&quot;">
            <option value="inner1">Inner 1</option>
            <option value="inner2">Inner 2</option>
            </optgroup>
            </select>"""
        ))

    def test_choices_select_inner(self):
        self.check_html(self.nested_widget, 'nestchoice', 'inner1', html=(
            """<select name="nestchoice">
            <option value="outer1">Outer 1</option>
            <optgroup label="Group &quot;1&quot;">
            <option value="inner1" selected="selected">Inner 1</option>
            <option value="inner2">Inner 2</option>
            </optgroup>
            </select>"""
        ))

    def test_deepcopy(self):
        """
        __deepcopy__() should copy all attributes properly (#25085).
        """
        widget = Select()
        obj = copy.deepcopy(widget)
        self.assertIsNot(widget, obj)
        self.assertEqual(widget.choices, obj.choices)
        self.assertIsNot(widget.choices, obj.choices)
        self.assertEqual(widget.attrs, obj.attrs)
        self.assertIsNot(widget.attrs, obj.attrs)
