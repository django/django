from django.forms import BoundField, Form, Field
from django.test import SimpleTestCase

class BoundFieldTest(SimpleTestCase):
    
    def test_boundfield_repr(self):
        form_instance = Form()
        field_instance = Field(label='input')
        name = 'test_input'
        f = BoundField(form_instance, field_instance, name)
        correct_response = f'<BoundField name={name} label=input>'

        self.assertEquals(f.__repr__(), correct_response)
