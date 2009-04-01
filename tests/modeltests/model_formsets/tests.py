from django.test import TestCase
from django.forms.models import modelformset_factory
from modeltests.model_formsets.models import Poet, Poem

class DeletionTests(TestCase):
    def test_deletion(self):
        PoetFormSet = modelformset_factory(Poet, can_delete=True)
        poet = Poet.objects.create(name='test')
        data = {
            'form-TOTAL_FORMS': u'1',
            'form-INITIAL_FORMS': u'1',
            'form-0-id': str(poet.pk),
            'form-0-name': u'test',
            'form-0-DELETE': u'on',
        }
        formset = PoetFormSet(data, queryset=Poet.objects.all())
        formset.save()
        self.assertTrue(formset.is_valid())
        self.assertEqual(Poet.objects.count(), 0)

    def test_add_form_deletion_when_invalid(self):
        """
        Make sure that an add form that is filled out, but marked for deletion
        doesn't cause validation errors.
        """
        PoetFormSet = modelformset_factory(Poet, can_delete=True)
        data = {
            'form-TOTAL_FORMS': u'1',
            'form-INITIAL_FORMS': u'0',
            'form-0-id': u'',
            'form-0-name': u'x' * 1000,
        }
        formset = PoetFormSet(data, queryset=Poet.objects.all())
        # Make sure this form doesn't pass validation.
        self.assertEqual(formset.is_valid(), False)
        self.assertEqual(Poet.objects.count(), 0)

        # Then make sure that it *does* pass validation and delete the object,
        # even though the data isn't actually valid.
        data['form-0-DELETE'] = 'on'
        formset = PoetFormSet(data, queryset=Poet.objects.all())
        self.assertEqual(formset.is_valid(), True)
        formset.save()
        self.assertEqual(Poet.objects.count(), 0)

    def test_change_form_deletion_when_invalid(self):
        """
        Make sure that an add form that is filled out, but marked for deletion
        doesn't cause validation errors.
        """
        PoetFormSet = modelformset_factory(Poet, can_delete=True)
        poet = Poet.objects.create(name='test')
        data = {
            'form-TOTAL_FORMS': u'1',
            'form-INITIAL_FORMS': u'1',
            'form-0-id': u'1',
            'form-0-name': u'x' * 1000,
        }
        formset = PoetFormSet(data, queryset=Poet.objects.all())
        # Make sure this form doesn't pass validation.
        self.assertEqual(formset.is_valid(), False)
        self.assertEqual(Poet.objects.count(), 1)

        # Then make sure that it *does* pass validation and delete the object,
        # even though the data isn't actually valid.
        data['form-0-DELETE'] = 'on'
        formset = PoetFormSet(data, queryset=Poet.objects.all())
        self.assertEqual(formset.is_valid(), True)
        formset.save()
        self.assertEqual(Poet.objects.count(), 0)
