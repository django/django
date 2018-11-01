import datetime

from django import forms
from django.forms import CheckboxSelectMultiple
from django.test import override_settings

from .base import WidgetTest


class CheckboxSelectMultipleTest(WidgetTest):
    widget = CheckboxSelectMultiple

    def test_render_value(self):
        self.check_html(self.widget(choices=self.beatles), 'beatles', ['J'], html=(
            """<ul>
            <li><label><input checked type="checkbox" name="beatles" value="J"> John</label></li>
            <li><label><input type="checkbox" name="beatles" value="P"> Paul</label></li>
            <li><label><input type="checkbox" name="beatles" value="G"> George</label></li>
            <li><label><input type="checkbox" name="beatles" value="R"> Ringo</label></li>
            </ul>"""
        ))

    def test_render_value_multiple(self):
        self.check_html(self.widget(choices=self.beatles), 'beatles', ['J', 'P'], html=(
            """<ul>
            <li><label><input checked type="checkbox" name="beatles" value="J"> John</label></li>
            <li><label><input checked type="checkbox" name="beatles" value="P"> Paul</label></li>
            <li><label><input type="checkbox" name="beatles" value="G"> George</label></li>
            <li><label><input type="checkbox" name="beatles" value="R"> Ringo</label></li>
            </ul>"""
        ))

    def test_render_none(self):
        """
        If the value is None, none of the options are selected, even if the
        choices have an empty option.
        """
        self.check_html(self.widget(choices=(('', 'Unknown'),) + self.beatles), 'beatles', None, html=(
            """<ul>
            <li><label><input type="checkbox" name="beatles" value=""> Unknown</label></li>
            <li><label><input type="checkbox" name="beatles" value="J"> John</label></li>
            <li><label><input type="checkbox" name="beatles" value="P"> Paul</label></li>
            <li><label><input type="checkbox" name="beatles" value="G"> George</label></li>
            <li><label><input type="checkbox" name="beatles" value="R"> Ringo</label></li>
            </ul>"""
        ))

    def test_nested_choices(self):
        nested_choices = (
            ('unknown', 'Unknown'),
            ('Audio', (('vinyl', 'Vinyl'), ('cd', 'CD'))),
            ('Video', (('vhs', 'VHS'), ('dvd', 'DVD'))),
        )
        html = """
        <ul id="media">
        <li>
        <label for="media_0"><input id="media_0" name="nestchoice" type="checkbox" value="unknown"> Unknown</label>
        </li>
        <li>Audio<ul id="media_1">
        <li>
        <label for="media_1_0">
        <input checked id="media_1_0" name="nestchoice" type="checkbox" value="vinyl"> Vinyl
        </label>
        </li>
        <li>
        <label for="media_1_1"><input id="media_1_1" name="nestchoice" type="checkbox" value="cd"> CD</label>
        </li>
        </ul></li>
        <li>Video<ul id="media_2">
        <li>
        <label for="media_2_0"><input id="media_2_0" name="nestchoice" type="checkbox" value="vhs"> VHS</label>
        </li>
        <li>
        <label for="media_2_1">
        <input checked id="media_2_1" name="nestchoice" type="checkbox" value="dvd"> DVD
        </label>
        </li>
        </ul></li>
        </ul>
        """
        self.check_html(
            self.widget(choices=nested_choices), 'nestchoice', ('vinyl', 'dvd'),
            attrs={'id': 'media'}, html=html,
        )

    def test_nested_choices_without_id(self):
        nested_choices = (
            ('unknown', 'Unknown'),
            ('Audio', (('vinyl', 'Vinyl'), ('cd', 'CD'))),
            ('Video', (('vhs', 'VHS'), ('dvd', 'DVD'))),
        )
        html = """
        <ul>
        <li>
        <label><input name="nestchoice" type="checkbox" value="unknown"> Unknown</label>
        </li>
        <li>Audio<ul>
        <li>
        <label>
        <input checked name="nestchoice" type="checkbox" value="vinyl"> Vinyl
        </label>
        </li>
        <li>
        <label><input name="nestchoice" type="checkbox" value="cd"> CD</label>
        </li>
        </ul></li>
        <li>Video<ul>
        <li>
        <label><input name="nestchoice" type="checkbox" value="vhs"> VHS</label>
        </li>
        <li>
        <label>
        <input checked name="nestchoice" type="checkbox" value="dvd"> DVD
        </label>
        </li>
        </ul></li>
        </ul>
        """
        self.check_html(self.widget(choices=nested_choices), 'nestchoice', ('vinyl', 'dvd'), html=html)

    def test_separate_ids(self):
        """
        Each input gets a separate ID.
        """
        choices = [('a', 'A'), ('b', 'B'), ('c', 'C')]
        html = """
        <ul id="abc">
        <li>
        <label for="abc_0"><input checked type="checkbox" name="letters" value="a" id="abc_0"> A</label>
        </li>
        <li><label for="abc_1"><input type="checkbox" name="letters" value="b" id="abc_1"> B</label></li>
        <li>
        <label for="abc_2"><input checked type="checkbox" name="letters" value="c" id="abc_2"> C</label>
        </li>
        </ul>
        """
        self.check_html(self.widget(choices=choices), 'letters', ['a', 'c'], attrs={'id': 'abc'}, html=html)

    def test_separate_ids_constructor(self):
        """
        Each input gets a separate ID when the ID is passed to the constructor.
        """
        widget = CheckboxSelectMultiple(attrs={'id': 'abc'}, choices=[('a', 'A'), ('b', 'B'), ('c', 'C')])
        html = """
        <ul id="abc">
        <li>
        <label for="abc_0"><input checked type="checkbox" name="letters" value="a" id="abc_0"> A</label>
        </li>
        <li><label for="abc_1"><input type="checkbox" name="letters" value="b" id="abc_1"> B</label></li>
        <li>
        <label for="abc_2"><input checked type="checkbox" name="letters" value="c" id="abc_2"> C</label>
        </li>
        </ul>
        """
        self.check_html(widget, 'letters', ['a', 'c'], html=html)

    @override_settings(USE_L10N=True, USE_THOUSAND_SEPARATOR=True)
    def test_doesnt_localize_input_value(self):
        choices = [
            (1, 'One'),
            (1000, 'One thousand'),
            (1000000, 'One million'),
        ]
        html = """
        <ul>
        <li><label><input type="checkbox" name="numbers" value="1"> One</label></li>
        <li><label><input type="checkbox" name="numbers" value="1000"> One thousand</label></li>
        <li><label><input type="checkbox" name="numbers" value="1000000"> One million</label></li>
        </ul>
        """
        self.check_html(self.widget(choices=choices), 'numbers', None, html=html)

        choices = [
            (datetime.time(0, 0), 'midnight'),
            (datetime.time(12, 0), 'noon'),
        ]
        html = """
        <ul>
        <li><label><input type="checkbox" name="times" value="00:00:00"> midnight</label></li>
        <li><label><input type="checkbox" name="times" value="12:00:00"> noon</label></li>
        </ul>
        """
        self.check_html(self.widget(choices=choices), 'times', None, html=html)

    def test_use_required_attribute(self):
        widget = self.widget(choices=self.beatles)
        # Always False because browser validation would require all checkboxes
        # to be checked instead of at least one.
        self.assertIs(widget.use_required_attribute(None), False)
        self.assertIs(widget.use_required_attribute([]), False)
        self.assertIs(widget.use_required_attribute(['J', 'P']), False)

    def test_value_omitted_from_data(self):
        widget = self.widget(choices=self.beatles)
        self.assertIs(widget.value_omitted_from_data({}, {}, 'field'), False)
        self.assertIs(widget.value_omitted_from_data({'field': 'value'}, {}, 'field'), False)

    def test_label(self):
        """"
        CheckboxSelectMultiple doesn't contain 'for="field_0"' in the <label>
        because clicking that would toggle the first checkbox.
        """
        class TestForm(forms.Form):
            f = forms.MultipleChoiceField(widget=CheckboxSelectMultiple)

        bound_field = TestForm()['f']
        self.assertEqual(bound_field.field.widget.id_for_label('id'), '')
        self.assertEqual(bound_field.label_tag(), '<label>F:</label>')
