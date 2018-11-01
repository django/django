from django.forms.models import ModelForm, inlineformset_factory
from django.test import TestCase, skipUnlessDBFeature

from .models import Child, Parent, Poem, Poet, School


class DeletionTests(TestCase):

    def test_deletion(self):
        PoemFormSet = inlineformset_factory(Poet, Poem, can_delete=True, fields="__all__")
        poet = Poet.objects.create(name='test')
        poem = poet.poem_set.create(name='test poem')
        data = {
            'poem_set-TOTAL_FORMS': '1',
            'poem_set-INITIAL_FORMS': '1',
            'poem_set-MAX_NUM_FORMS': '0',
            'poem_set-0-id': str(poem.pk),
            'poem_set-0-poet': str(poet.pk),
            'poem_set-0-name': 'test',
            'poem_set-0-DELETE': 'on',
        }
        formset = PoemFormSet(data, instance=poet)
        formset.save()
        self.assertTrue(formset.is_valid())
        self.assertEqual(Poem.objects.count(), 0)

    def test_add_form_deletion_when_invalid(self):
        """
        Make sure that an add form that is filled out, but marked for deletion
        doesn't cause validation errors.
        """
        PoemFormSet = inlineformset_factory(Poet, Poem, can_delete=True, fields="__all__")
        poet = Poet.objects.create(name='test')
        data = {
            'poem_set-TOTAL_FORMS': '1',
            'poem_set-INITIAL_FORMS': '0',
            'poem_set-MAX_NUM_FORMS': '0',
            'poem_set-0-id': '',
            'poem_set-0-poem': '1',
            'poem_set-0-name': 'x' * 1000,
        }
        formset = PoemFormSet(data, instance=poet)
        # Make sure this form doesn't pass validation.
        self.assertIs(formset.is_valid(), False)
        self.assertEqual(Poem.objects.count(), 0)

        # Then make sure that it *does* pass validation and delete the object,
        # even though the data isn't actually valid.
        data['poem_set-0-DELETE'] = 'on'
        formset = PoemFormSet(data, instance=poet)
        self.assertIs(formset.is_valid(), True)
        formset.save()
        self.assertEqual(Poem.objects.count(), 0)

    def test_change_form_deletion_when_invalid(self):
        """
        Make sure that a change form that is filled out, but marked for deletion
        doesn't cause validation errors.
        """
        PoemFormSet = inlineformset_factory(Poet, Poem, can_delete=True, fields="__all__")
        poet = Poet.objects.create(name='test')
        poem = poet.poem_set.create(name='test poem')
        data = {
            'poem_set-TOTAL_FORMS': '1',
            'poem_set-INITIAL_FORMS': '1',
            'poem_set-MAX_NUM_FORMS': '0',
            'poem_set-0-id': str(poem.id),
            'poem_set-0-poem': str(poem.id),
            'poem_set-0-name': 'x' * 1000,
        }
        formset = PoemFormSet(data, instance=poet)
        # Make sure this form doesn't pass validation.
        self.assertIs(formset.is_valid(), False)
        self.assertEqual(Poem.objects.count(), 1)

        # Then make sure that it *does* pass validation and delete the object,
        # even though the data isn't actually valid.
        data['poem_set-0-DELETE'] = 'on'
        formset = PoemFormSet(data, instance=poet)
        self.assertIs(formset.is_valid(), True)
        formset.save()
        self.assertEqual(Poem.objects.count(), 0)

    def test_save_new(self):
        """
        Make sure inlineformsets respect commit=False
        regression for #10750
        """
        # exclude some required field from the forms
        ChildFormSet = inlineformset_factory(School, Child, exclude=['father', 'mother'])
        school = School.objects.create(name='test')
        mother = Parent.objects.create(name='mother')
        father = Parent.objects.create(name='father')
        data = {
            'child_set-TOTAL_FORMS': '1',
            'child_set-INITIAL_FORMS': '0',
            'child_set-MAX_NUM_FORMS': '0',
            'child_set-0-name': 'child',
        }
        formset = ChildFormSet(data, instance=school)
        self.assertIs(formset.is_valid(), True)
        objects = formset.save(commit=False)
        for obj in objects:
            obj.mother = mother
            obj.father = father
            obj.save()
        self.assertEqual(school.child_set.count(), 1)


class InlineFormsetFactoryTest(TestCase):
    def test_inline_formset_factory(self):
        """
        These should both work without a problem.
        """
        inlineformset_factory(Parent, Child, fk_name='mother', fields="__all__")
        inlineformset_factory(Parent, Child, fk_name='father', fields="__all__")

    def test_exception_on_unspecified_foreign_key(self):
        """
        Child has two ForeignKeys to Parent, so if we don't specify which one
        to use for the inline formset, we should get an exception.
        """
        msg = "'inline_formsets.Child' has more than one ForeignKey to 'inline_formsets.Parent'."
        with self.assertRaisesMessage(ValueError, msg):
            inlineformset_factory(Parent, Child)

    def test_fk_name_not_foreign_key_field_from_child(self):
        """
        If we specify fk_name, but it isn't a ForeignKey from the child model
        to the parent model, we should get an exception.
        """
        msg = "fk_name 'school' is not a ForeignKey to 'inline_formsets.Parent'."
        with self.assertRaisesMessage(ValueError, msg):
            inlineformset_factory(Parent, Child, fk_name='school')

    def test_non_foreign_key_field(self):
        """
        If the field specified in fk_name is not a ForeignKey, we should get an
        exception.
        """
        with self.assertRaisesMessage(ValueError, "'inline_formsets.Child' has no field named 'test'."):
            inlineformset_factory(Parent, Child, fk_name='test')

    def test_any_iterable_allowed_as_argument_to_exclude(self):
        # Regression test for #9171.
        inlineformset_factory(
            Parent, Child, exclude=['school'], fk_name='mother'
        )

        inlineformset_factory(
            Parent, Child, exclude=('school',), fk_name='mother'
        )

    @skipUnlessDBFeature('allows_auto_pk_0')
    def test_zero_primary_key(self):
        # Regression test for #21472
        poet = Poet.objects.create(id=0, name='test')
        poet.poem_set.create(name='test poem')
        PoemFormSet = inlineformset_factory(Poet, Poem, fields="__all__", extra=0)
        formset = PoemFormSet(None, instance=poet)
        self.assertEqual(len(formset.forms), 1)

    def test_unsaved_fk_validate_unique(self):
        poet = Poet(name='unsaved')
        PoemFormSet = inlineformset_factory(Poet, Poem, fields=['name'])
        data = {
            'poem_set-TOTAL_FORMS': '2',
            'poem_set-INITIAL_FORMS': '0',
            'poem_set-MAX_NUM_FORMS': '2',
            'poem_set-0-name': 'Poem',
            'poem_set-1-name': 'Poem',
        }
        formset = PoemFormSet(data, instance=poet)
        self.assertFalse(formset.is_valid())
        self.assertEqual(formset.non_form_errors(), ['Please correct the duplicate data for name.'])

    def test_fk_not_duplicated_in_form_fields(self):
        """
        A foreign key name isn't duplicated in form._meta fields (#21332).
        """
        poet = Poet.objects.create(name='test')
        poet.poem_set.create(name='first test poem')
        poet.poem_set.create(name='second test poem')
        poet.poem_set.create(name='third test poem')
        PoemFormSet = inlineformset_factory(Poet, Poem, fields=('name',), extra=0)
        formset = PoemFormSet(None, instance=poet)
        self.assertEqual(len(formset.forms), 3)
        self.assertEqual(['name', 'poet'], PoemFormSet.form._meta.fields)

    def test_fk_in_all_formset_forms(self):
        """
        A foreign key field is in Meta for all forms in the formset (#26538).
        """
        class PoemModelForm(ModelForm):
            def __init__(self, *args, **kwargs):
                assert 'poet' in self._meta.fields
                super().__init__(*args, **kwargs)

        poet = Poet.objects.create(name='test')
        poet.poem_set.create(name='first test poem')
        poet.poem_set.create(name='second test poem')
        PoemFormSet = inlineformset_factory(Poet, Poem, form=PoemModelForm, fields=('name',), extra=0)
        formset = PoemFormSet(None, instance=poet)
        formset.forms  # Trigger form instantiation to run the assert above.
