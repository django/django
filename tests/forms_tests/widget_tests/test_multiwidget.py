import copy
from datetime import datetime

from django.forms import (
    CharField, FileInput, MultipleChoiceField, MultiValueField, MultiWidget,
    RadioSelect, SelectMultiple, SplitDateTimeField, SplitDateTimeWidget,
    TextInput,
)

from .base import WidgetTest


class MyMultiWidget(MultiWidget):
    def decompress(self, value):
        if value:
            return value.split('__')
        return ['', '']


class ComplexMultiWidget(MultiWidget):
    def __init__(self, attrs=None):
        widgets = (
            TextInput(),
            SelectMultiple(choices=WidgetTest.beatles),
            SplitDateTimeWidget(),
        )
        super().__init__(widgets, attrs)

    def decompress(self, value):
        if value:
            data = value.split(',')
            return [
                data[0], list(data[1]), datetime.strptime(data[2], "%Y-%m-%d %H:%M:%S")
            ]
        return [None, None, None]


class ComplexField(MultiValueField):
    def __init__(self, required=True, widget=None, label=None, initial=None):
        fields = (
            CharField(),
            MultipleChoiceField(choices=WidgetTest.beatles),
            SplitDateTimeField(),
        )
        super().__init__(fields, required, widget, label, initial)

    def compress(self, data_list):
        if data_list:
            return '%s,%s,%s' % (
                data_list[0], ''.join(data_list[1]), data_list[2],
            )
        return None


class DeepCopyWidget(MultiWidget):
    """
    Used to test MultiWidget.__deepcopy__().
    """
    def __init__(self, choices=[]):
        widgets = [
            RadioSelect(choices=choices),
            TextInput,
        ]
        super().__init__(widgets)

    def _set_choices(self, choices):
        """
        When choices are set for this widget, we want to pass those along to
        the Select widget.
        """
        self.widgets[0].choices = choices

    def _get_choices(self):
        """
        The choices for this widget are the Select widget's choices.
        """
        return self.widgets[0].choices
    choices = property(_get_choices, _set_choices)


class MultiWidgetTest(WidgetTest):

    def test_text_inputs(self):
        widget = MyMultiWidget(
            widgets=(
                TextInput(attrs={'class': 'big'}),
                TextInput(attrs={'class': 'small'}),
            )
        )
        self.check_html(widget, 'name', ['john', 'lennon'], html=(
            '<input type="text" class="big" value="john" name="name_0">'
            '<input type="text" class="small" value="lennon" name="name_1">'
        ))
        self.check_html(widget, 'name', 'john__lennon', html=(
            '<input type="text" class="big" value="john" name="name_0">'
            '<input type="text" class="small" value="lennon" name="name_1">'
        ))
        self.check_html(widget, 'name', 'john__lennon', attrs={'id': 'foo'}, html=(
            '<input id="foo_0" type="text" class="big" value="john" name="name_0">'
            '<input id="foo_1" type="text" class="small" value="lennon" name="name_1">'
        ))

    def test_constructor_attrs(self):
        widget = MyMultiWidget(
            widgets=(
                TextInput(attrs={'class': 'big'}),
                TextInput(attrs={'class': 'small'}),
            ),
            attrs={'id': 'bar'},
        )
        self.check_html(widget, 'name', ['john', 'lennon'], html=(
            '<input id="bar_0" type="text" class="big" value="john" name="name_0">'
            '<input id="bar_1" type="text" class="small" value="lennon" name="name_1">'
        ))

    def test_constructor_attrs_with_type(self):
        attrs = {'type': 'number'}
        widget = MyMultiWidget(widgets=(TextInput, TextInput()), attrs=attrs)
        self.check_html(widget, 'code', ['1', '2'], html=(
            '<input type="number" value="1" name="code_0">'
            '<input type="number" value="2" name="code_1">'
        ))
        widget = MyMultiWidget(widgets=(TextInput(attrs), TextInput(attrs)), attrs={'class': 'bar'})
        self.check_html(widget, 'code', ['1', '2'], html=(
            '<input type="number" value="1" name="code_0" class="bar">'
            '<input type="number" value="2" name="code_1" class="bar">'
        ))

    def test_value_omitted_from_data(self):
        widget = MyMultiWidget(widgets=(TextInput(), TextInput()))
        self.assertIs(widget.value_omitted_from_data({}, {}, 'field'), True)
        self.assertIs(widget.value_omitted_from_data({'field_0': 'x'}, {}, 'field'), False)
        self.assertIs(widget.value_omitted_from_data({'field_1': 'y'}, {}, 'field'), False)
        self.assertIs(widget.value_omitted_from_data({'field_0': 'x', 'field_1': 'y'}, {}, 'field'), False)

    def test_needs_multipart_true(self):
        """
        needs_multipart_form should be True if any widgets need it.
        """
        widget = MyMultiWidget(widgets=(TextInput(), FileInput()))
        self.assertTrue(widget.needs_multipart_form)

    def test_needs_multipart_false(self):
        """
        needs_multipart_form should be False if no widgets need it.
        """
        widget = MyMultiWidget(widgets=(TextInput(), TextInput()))
        self.assertFalse(widget.needs_multipart_form)

    def test_nested_multiwidget(self):
        """
        MultiWidgets can be composed of other MultiWidgets.
        """
        widget = ComplexMultiWidget()
        self.check_html(widget, 'name', 'some text,JP,2007-04-25 06:24:00', html=(
            """
            <input type="text" name="name_0" value="some text">
            <select multiple name="name_1">
                <option value="J" selected>John</option>
                <option value="P" selected>Paul</option>
                <option value="G">George</option>
                <option value="R">Ringo</option>
            </select>
            <input type="text" name="name_2_0" value="2007-04-25">
            <input type="text" name="name_2_1" value="06:24:00">
            """
        ))

    def test_no_whitespace_between_widgets(self):
        widget = MyMultiWidget(widgets=(TextInput, TextInput()))
        self.check_html(widget, 'code', None, html=(
            '<input type="text" name="code_0">'
            '<input type="text" name="code_1">'
        ), strict=True)

    def test_deepcopy(self):
        """
        MultiWidget should define __deepcopy__() (#12048).
        """
        w1 = DeepCopyWidget(choices=[1, 2, 3])
        w2 = copy.deepcopy(w1)
        w2.choices = [4, 5, 6]
        # w2 ought to be independent of w1, since MultiWidget ought
        # to make a copy of its sub-widgets when it is copied.
        self.assertEqual(w1.choices, [1, 2, 3])
