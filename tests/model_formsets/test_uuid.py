from django.forms.models import inlineformset_factory
from django.test import TestCase

from .models import UUIDPKChild, UUIDPKParent


class InlineFormsetTests(TestCase):
    def test_inlineformset_factory_nulls_default_pks(self):
        """
        #24377 - If we're adding a new object, a parent's auto-generated pk
        from the model field default should be ignored as it's regenerated on
        the save request.
        """
        FormSet = inlineformset_factory(UUIDPKParent, UUIDPKChild, fields='__all__')
        formset = FormSet()
        self.assertIsNone(formset.forms[0].fields['parent'].initial)

    def test_inlineformset_factory_ignores_default_pks_on_submit(self):
        """
        #24377 - Inlines with a model field default should ignore that default
        value to avoid triggering validation on empty forms.
        """
        FormSet = inlineformset_factory(UUIDPKParent, UUIDPKChild, fields='__all__')
        formset = FormSet({
            'uuidpkchild_set-TOTAL_FORMS': 3,
            'uuidpkchild_set-INITIAL_FORMS': 0,
            'uuidpkchild_set-MAX_NUM_FORMS': '',
            'uuidpkchild_set-0-name': 'Foo',
            'uuidpkchild_set-1-name': '',
            'uuidpkchild_set-2-name': '',
        })
        self.assertTrue(formset.is_valid())
