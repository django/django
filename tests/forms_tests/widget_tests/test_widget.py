from django import forms
from django.contrib.auth.models import User
from django.forms import Widget
from django.forms.widgets import Input
from django.test import TestCase

from .base import WidgetTest


class WidgetTests(WidgetTest):
    def test_format_value(self):
        widget = Widget()
        self.assertIsNone(widget.format_value(None))
        self.assertIsNone(widget.format_value(""))
        self.assertEqual(widget.format_value("español"), "español")
        self.assertEqual(widget.format_value(42.5), "42.5")

    def test_value_omitted_from_data(self):
        widget = Widget()
        self.assertIs(widget.value_omitted_from_data({}, {}, "field"), True)
        self.assertIs(
            widget.value_omitted_from_data({"field": "value"}, {}, "field"),
            False,
        )

    def test_no_trailing_newline_in_attrs(self):
        self.check_html(
            Input(),
            "name",
            "value",
            strict=True,
            html='<input type="None" name="name" value="value">',
        )

    def test_attr_false_not_rendered(self):
        html = '<input type="None" name="name" value="value">'
        self.check_html(Input(), "name", "value", html=html, attrs={"readonly": False})


class SelectUseRequiredAttributeTests(TestCase):
    def test_does_not_trigger_query_with_model_choice_iterator(self):
        # Create test data
        User.objects.create(username="a")
        User.objects.create(username="b")

        class TestForm(forms.Form):
            field = forms.ModelChoiceField(
                queryset=User.objects.all(),
                empty_label="Select one",
            )

        form = TestForm()
        widget = form.fields["field"].widget

        # Should NOT trigger any DB queries
        with self.assertNumQueries(0):
            widget.use_required_attribute(initial=None)
