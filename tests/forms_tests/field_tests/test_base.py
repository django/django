from django.forms import Field
from django.test import SimpleTestCase


class BasicFieldsTests(SimpleTestCase):

    def test_field_sets_widget_is_required(self):
        self.assertTrue(Field(required=True).widget.is_required)
        self.assertFalse(Field(required=False).widget.is_required)

    def test_cooperative_multiple_inheritance(self):
        class A(object):
            def __init__(self):
                self.class_a_var = True
                super(A, self).__init__()

        class ComplexField(Field, A):
            def __init__(self):
                super(ComplexField, self).__init__()

        f = ComplexField()
        self.assertTrue(f.class_a_var)
