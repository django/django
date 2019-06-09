import json
import uuid

from django import forms
from django.core import exceptions
from django.core.serializers.json import DjangoJSONEncoder
from django.test import SimpleTestCase


class CustomDecoder(json.JSONDecoder):
    def __init__(self, object_hook=None, *args, **kwargs):
        return super().__init__(object_hook=self.object_hook, *args, **kwargs)

    def object_hook(self, dct):
        try:
            dct['uuid'] = uuid.UUID(dct['uuid'])
        except KeyError:
            pass
        return dct


class TestFormField(SimpleTestCase):

    def test_valid(self):
        field = forms.JSONField()
        value = field.clean('{"a": "b"}')
        self.assertEqual(value, {'a': 'b'})

    def test_valid_empty(self):
        field = forms.JSONField(required=False)
        value = field.clean('')
        self.assertIsNone(value)

    def test_invalid(self):
        field = forms.JSONField()
        with self.assertRaisesMessage(exceptions.ValidationError, 'Enter a valid JSON value.'):
            field.clean('{some badly formed: json}')

    def test_formfield_disabled(self):
        class JsonForm(forms.Form):
            name = forms.CharField()
            jfield = forms.JSONField(disabled=True)

        form = JsonForm({'name': 'xyz', 'jfield': '["bar"]'}, initial={'jfield': ['foo']})
        self.assertIn('[&quot;foo&quot;]</textarea>', form.as_p())

    def test_prepare_value(self):
        field = forms.JSONField()
        self.assertEqual(field.prepare_value({'a': 'b'}), '{"a": "b"}')
        self.assertEqual(field.prepare_value(None), 'null')
        self.assertEqual(field.prepare_value('foo'), '"foo"')

    def test_redisplay_wrong_input(self):
        """
        When displaying a bound form (typically due to invalid input), the form
        should not overquote JSONField inputs.
        """
        class JsonForm(forms.Form):
            name = forms.CharField(max_length=2)
            jfield = forms.JSONField()

        # JSONField input is fine, name is too long
        form = JsonForm({'name': 'xyz', 'jfield': '["foo"]'})
        self.assertNotIn('jfield', form.errors)
        self.assertIn('[&quot;foo&quot;]</textarea>', form.as_p())

        # This time, the JSONField input is wrong
        form = JsonForm({'name': 'xy', 'jfield': '{"foo"}'})
        self.assertIn('jfield', form.errors)
        self.assertIn('{&quot;foo&quot;}</textarea>', form.as_p())

    def test_widget(self):
        """The default widget of a JSONField is a Textarea."""
        field = forms.JSONField()
        self.assertIsInstance(field.widget, forms.widgets.Textarea)

    def test_custom_widget_kwarg(self):
        """The widget can be overridden with a kwarg."""
        field = forms.JSONField(widget=forms.widgets.Input)
        self.assertIsInstance(field.widget, forms.widgets.Input)

    def test_custom_widget_attribute(self):
        """The widget can be overridden with an attribute."""
        class CustomJSONField(forms.JSONField):
            widget = forms.widgets.Input

        field = CustomJSONField()
        self.assertIsInstance(field.widget, forms.widgets.Input)

    def test_already_converted_value(self):
        field = forms.JSONField(required=False)
        tests = [
            '["a", "b", "c"]', '{"a": 1, "b": 2}', '1', '1.5', '"foo"',
            'true', 'false', 'null',
        ]
        for json_string in tests:
            with self.subTest(json_string=json_string):
                val = field.clean(json_string)
                self.assertEqual(field.clean(val), val)

    def test_has_changed(self):
        field = forms.JSONField()
        self.assertIs(field.has_changed({'a': True}, '{"a": 1}'), True)
        self.assertIs(field.has_changed({'a': 1, 'b': 2}, '{"b": 2, "a": 1}'), False)

    def test_custom_encoder_decoder(self):
        value = {'uuid': uuid.UUID('{12345678-1234-5678-1234-567812345678}')}
        field = forms.JSONField(encoder=DjangoJSONEncoder, decoder=CustomDecoder)
        self.assertEqual(field.prepare_value(value), '{"uuid": "12345678-1234-5678-1234-567812345678"}')
        self.assertEqual(field.clean('{"uuid": "12345678-1234-5678-1234-567812345678"}'), value)
