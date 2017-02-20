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
            <option value="J" selected>John</option>
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
            <option value="0" selected>0</option>
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
              <option value="2" selected>2</option>
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
                <option value="2" selected>2</option>
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
                <option value="2" selected>2</option>
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
                <option value="2" selected>2</option>
                <option value="3">3</option>
                </select>"""
            ),
        )

    def test_choices_constuctor(self):
        widget = Select(choices=[(1, 1), (2, 2), (3, 3)])
        self.check_html(widget, 'num', 2, html=(
            """<select name="num">
            <option value="1">1</option>
            <option value="2" selected>2</option>
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
            <option value="2" selected>2</option>
            <option value="3">3</option>
            <option value="4">4</option>
            </select>"""
        ))
        self.check_html(widget, 'num', 3, html=(
            """<select name="num">
            <option value="0">0</option>
            <option value="1">1</option>
            <option value="2">2</option>
            <option value="3" selected>3</option>
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
                <option value="\u0160\u0110\u0106\u017d\u0107\u017e\u0161\u0111" selected>
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
            <option value="outer1" selected>Outer 1</option>
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
            <option value="inner1" selected>Inner 1</option>
            <option value="inner2">Inner 2</option>
            </optgroup>
            </select>"""
        ))

    def test_options(self):
        options = list(self.widget(choices=self.beatles).options(
            'name', ['J'], attrs={'class': 'super'},
        ))
        self.assertEqual(len(options), 4)
        self.assertEqual(options[0]['name'], 'name')
        self.assertEqual(options[0]['value'], 'J')
        self.assertEqual(options[0]['label'], 'John')
        self.assertEqual(options[0]['index'], '0')
        self.assertEqual(options[0]['selected'], True)
        # Template-related attributes
        self.assertEqual(options[1]['name'], 'name')
        self.assertEqual(options[1]['value'], 'P')
        self.assertEqual(options[1]['label'], 'Paul')
        self.assertEqual(options[1]['index'], '1')
        self.assertEqual(options[1]['selected'], False)

    def test_optgroups(self):
        choices = [
            ('Audio', [
                ('vinyl', 'Vinyl'),
                ('cd', 'CD'),
            ]),
            ('Video', [
                ('vhs', 'VHS Tape'),
                ('dvd', 'DVD'),
            ]),
            ('unknown', 'Unknown'),
        ]
        groups = list(self.widget(choices=choices).optgroups(
            'name', ['vhs'], attrs={'class': 'super'},
        ))
        self.assertEqual(len(groups), 3)
        self.assertEqual(groups[0][0], None)
        self.assertEqual(groups[0][2], 0)
        self.assertEqual(len(groups[0][1]), 1)
        options = groups[0][1]
        self.assertEqual(options[0]['name'], 'name')
        self.assertEqual(options[0]['value'], 'unknown')
        self.assertEqual(options[0]['label'], 'Unknown')
        self.assertEqual(options[0]['index'], '0')
        self.assertEqual(options[0]['selected'], False)
        self.assertEqual(groups[1][0], 'Audio')
        self.assertEqual(groups[1][2], 1)
        self.assertEqual(len(groups[1][1]), 2)
        options = groups[1][1]
        self.assertEqual(options[0]['name'], 'name')
        self.assertEqual(options[0]['value'], 'vinyl')
        self.assertEqual(options[0]['label'], 'Vinyl')
        self.assertEqual(options[0]['index'], '1_0')
        self.assertEqual(options[1]['index'], '1_1')
        self.assertEqual(groups[2][0], 'Video')
        self.assertEqual(groups[2][2], 2)
        self.assertEqual(len(groups[2][1]), 2)
        options = groups[2][1]
        self.assertEqual(options[0]['name'], 'name')
        self.assertEqual(options[0]['value'], 'vhs')
        self.assertEqual(options[0]['label'], 'VHS Tape')
        self.assertEqual(options[0]['index'], '2_0')
        self.assertEqual(options[0]['selected'], True)
        self.assertEqual(options[1]['index'], '2_1')

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

    def test_doesnt_render_required_when_impossible_to_select_empty_field(self):
        widget = self.widget(choices=[('J', 'John'), ('P', 'Paul')])
        self.assertIs(widget.use_required_attribute(initial=None), False)

    def test_renders_required_when_possible_to_select_empty_field_str(self):
        widget = self.widget(choices=[('', 'select please'), ('P', 'Paul')])
        self.assertIs(widget.use_required_attribute(initial=None), True)

    def test_renders_required_when_possible_to_select_empty_field_list(self):
        widget = self.widget(choices=[['', 'select please'], ['P', 'Paul']])
        self.assertIs(widget.use_required_attribute(initial=None), True)

    def test_renders_required_when_possible_to_select_empty_field_none(self):
        widget = self.widget(choices=[(None, 'select please'), ('P', 'Paul')])
        self.assertIs(widget.use_required_attribute(initial=None), True)

    def test_doesnt_render_required_when_no_choices_are_available(self):
        widget = self.widget(choices=[])
        self.assertIs(widget.use_required_attribute(initial=None), False)
