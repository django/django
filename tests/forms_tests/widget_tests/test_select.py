import copy
import datetime

from django.forms import Select
from django.test import override_settings
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

    @override_settings(USE_L10N=True, USE_THOUSAND_SEPARATOR=True)
    def test_doesnt_localize_option_value(self):
        choices = [
            (1, 'One'),
            (1000, 'One thousand'),
            (1000000, 'One million'),
        ]
        html = """
        <select name="number">
        <option value="1">One</option>
        <option value="1000">One thousand</option>
        <option value="1000000">One million</option>
        </select>
        """
        self.check_html(self.widget(choices=choices), 'number', None, html=html)

        choices = [
            (datetime.time(0, 0), 'midnight'),
            (datetime.time(12, 0), 'noon'),
        ]
        html = """
        <select name="time">
        <option value="00:00:00">midnight</option>
        <option value="12:00:00">noon</option>
        </select>
        """
        self.check_html(self.widget(choices=choices), 'time', None, html=html)

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
        audio, video, unknown = groups
        label, options, index = audio
        self.assertEqual(label, 'Audio')
        self.assertEqual(
            options,
            [{
                'value': 'vinyl',
                'type': 'select',
                'attrs': {},
                'index': '0_0',
                'label': 'Vinyl',
                'template_name': 'django/forms/widgets/select_option.html',
                'name': 'name',
                'selected': False,
            }, {
                'value': 'cd',
                'type': 'select',
                'attrs': {},
                'index': '0_1',
                'label': 'CD',
                'template_name': 'django/forms/widgets/select_option.html',
                'name': 'name',
                'selected': False,
            }]
        )
        self.assertEqual(index, 0)
        label, options, index = video
        self.assertEqual(label, 'Video')
        self.assertEqual(
            options,
            [{
                'value': 'vhs',
                'template_name': 'django/forms/widgets/select_option.html',
                'label': 'VHS Tape',
                'attrs': {'selected': True},
                'index': '1_0',
                'name': 'name',
                'selected': True,
                'type': 'select',
            }, {
                'value': 'dvd',
                'template_name': 'django/forms/widgets/select_option.html',
                'label': 'DVD',
                'attrs': {},
                'index': '1_1',
                'name': 'name',
                'selected': False,
                'type': 'select',
            }]
        )
        self.assertEqual(index, 1)
        label, options, index = unknown
        self.assertEqual(label, None)
        self.assertEqual(
            options,
            [{
                'value': 'unknown',
                'selected': False,
                'template_name': 'django/forms/widgets/select_option.html',
                'label': 'Unknown',
                'attrs': {},
                'index': '2',
                'name': 'name',
                'type': 'select',
            }]
        )
        self.assertEqual(index, 2)

    def test_optgroups_integer_choices(self):
        """The option 'value' is the same type as what's in `choices`."""
        groups = list(self.widget(choices=[[0, 'choice text']]).optgroups('name', ['vhs']))
        label, options, index = groups[0]
        self.assertEqual(options[0]['value'], 0)

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
