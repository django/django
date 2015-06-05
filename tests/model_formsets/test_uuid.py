from django.forms.models import inlineformset_factory
from django.test import TestCase

from .models import (
    UUIDPKChild, UUIDPKParent, AutoPKChildOfUUIDPKParent, AutoPKParent,
    UUIDPKChildOfAutoPKParent, ChildWithEditablePK, ParentWithUUIDAlternateKey,
    ChildRelatedViaAK
)


class InlineFormsetTests(TestCase):
    def test_inlineformset_factory_nulls_default_pks(self):
        """
        #24377 - If we're adding a new object, a parent's auto-generated pk
        from the model field default should be ignored as it's regenerated on
        the save request.

        Tests the case where both the parent and child have a UUID pk.
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

    def test_inlineformset_factory_nulls_default_pks_uuid_parent_auto_child(self):
        """
        #24377 - If we're adding a new object, a parent's auto-generated pk
        from the model field default should be ignored as it's regenerated on
        the save request.

        Tests the case of a parent object with a UUID primary key and a child
        object with an AutoField primary key.
        """
        FormSet = inlineformset_factory(UUIDPKParent, AutoPKChildOfUUIDPKParent,
                                        fields='__all__')
        formset = FormSet()
        self.assertIsNone(formset.forms[0].fields['parent'].initial)

    def test_inlineformset_factory_ignores_default_pks_on_submit_uuid_parent_auto_child(self):
        """
        #24377 - Inlines with a model field default should ignore that default
        value to avoid triggering validation on empty forms.

        Tests the case of a parent object with a UUID primary key and a child
        object with an AutoField primary key.
        """
        FormSet = inlineformset_factory(UUIDPKParent, AutoPKChildOfUUIDPKParent,
                                        fields='__all__')
        formset = FormSet({
            'autopkchildofuuidpkparent_set-TOTAL_FORMS': 3,
            'autopkchildofuuidpkparent_set-INITIAL_FORMS': 0,
            'autopkchildofuuidpkparent_set-MAX_NUM_FORMS': '',
            'autopkchildofuuidpkparent_set-0-name': 'Foo',
            'autopkchildofuuidpkparent_set-1-name': '',
            'autopkchildofuuidpkparent_set-2-name': '',
        })
        self.assertTrue(formset.is_valid())

    def test_inlineformset_factory_nulls_default_pks_auto_parent_uuid_child(self):
        """
        #24377 - If we're adding a new object, a parent's auto-generated pk
        from the model field default should be ignored as it's regenerated on
        the save request.

        Tests the case of a parent object with an AutoField primary key and a
        child object with a UUID primary key.
        """
        FormSet = inlineformset_factory(AutoPKParent, UUIDPKChildOfAutoPKParent,
                                        fields='__all__')
        formset = FormSet()
        self.assertIsNone(formset.forms[0].fields['parent'].initial)

    def test_inlineformset_factory_ignores_default_pks_on_submit_auto_parent_uuid_child(self):
        """
        #24377 - Inlines with a model field default should ignore that default
        value to avoid triggering validation on empty forms.

        Tests the case of a parent object with an AutoField primary key and a
        child object with a UUID primary key.
        """
        FormSet = inlineformset_factory(AutoPKParent, UUIDPKChildOfAutoPKParent,
                                        fields='__all__')
        formset = FormSet({
            'uuidpkchildofautopkparent_set-TOTAL_FORMS': 3,
            'uuidpkchildofautopkparent_set-INITIAL_FORMS': 0,
            'uuidpkchildofautopkparent_set-MAX_NUM_FORMS': '',
            'uuidpkchildofautopkparent_set-0-name': 'Foo',
            'uuidpkchildofautopkparent_set-1-name': '',
            'uuidpkchildofautopkparent_set-2-name': '',
        })
        self.assertTrue(formset.is_valid())

    def test_inlineformset_factory_nulls_default_pks_child_editable_pk(self):
        """
        #24377 - If we're adding a new object, a parent's auto-generated pk
        from the model field default should be ignored as it's regenerated on
        the save request.

        Tests the case of a parent object with a UUID primary key and a
        child object with an editable natural key for a primary key.
        """
        FormSet = inlineformset_factory(UUIDPKParent, ChildWithEditablePK, fields='__all__')
        formset = FormSet()
        self.assertIsNone(formset.forms[0].fields['parent'].initial)

    def test_inlineformset_factory_ignores_default_pks_on_submit_child_editable_pk(self):
        """
        #24377 - Inlines with a model field default should ignore that default
        value to avoid triggering validation on empty forms.

        Tests the case of a parent object with a UUID primary key and a
        child object with an editable natural key for a primary key.
        """
        FormSet = inlineformset_factory(UUIDPKParent, ChildWithEditablePK, fields='__all__')
        formset = FormSet({
            'childwitheditablepk_set-TOTAL_FORMS': 3,
            'childwitheditablepk_set-INITIAL_FORMS': 0,
            'childwitheditablepk_set-MAX_NUM_FORMS': '',
            'childwitheditablepk_set-0-name': 'Foo',
            'childwitheditablepk_set-1-name': '',
            'childwitheditablepk_set-2-name': '',
        })
        self.assertTrue(formset.is_valid())

    def test_inlineformset_factory_nulls_default_pks_alternate_key_relation(self):
        """
        #24377 - If we're adding a new object, a parent's auto-generated pk
        from the model field default should be ignored as it's regenerated on
        the save request.

        Tests the case of a parent object with a UUID alternate key and a
        child object that related to that alternate ky.
        """
        FormSet = inlineformset_factory(ParentWithUUIDAlternateKey, ChildRelatedViaAK, fields='__all__')
        formset = FormSet()
        self.assertIsNone(formset.forms[0].fields['parent'].initial)

    def test_inlineformset_factory_ignores_default_pks_on_submit_alternate_key_relation(self):
        """
        #24377 - Inlines with a model field default should ignore that default
        value to avoid triggering validation on empty forms.

        Tests the case of a parent object with a UUID alternate key and a
        child object that related to that alternate ky.
        """
        FormSet = inlineformset_factory(ParentWithUUIDAlternateKey, ChildRelatedViaAK, fields='__all__')
        formset = FormSet({
            'childrelatedviaak_set-TOTAL_FORMS': 3,
            'childrelatedviaak_set-INITIAL_FORMS': 0,
            'childrelatedviaak_set-MAX_NUM_FORMS': '',
            'childrelatedviaak_set-0-name': 'Foo',
            'childrelatedviaak_set-1-name': '',
            'childrelatedviaak_set-2-name': '',
        })
        self.assertTrue(formset.is_valid())
