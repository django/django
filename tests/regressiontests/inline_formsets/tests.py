from django.test import TestCase
from django.forms.models import inlineformset_factory
from regressiontests.inline_formsets.models import Poet, Poem

class DeletionTests(TestCase):
    def test_deletion(self):
        PoemFormSet = inlineformset_factory(Poet, Poem, can_delete=True)
        poet = Poet.objects.create(name='test')
        poem = poet.poem_set.create(name='test poem')
        data = {
            'poem_set-TOTAL_FORMS': u'1',
            'poem_set-INITIAL_FORMS': u'1',
            'poem_set-0-id': str(poem.pk),
            'poem_set-0-poet': str(poet.pk),
            'poem_set-0-name': u'test',
            'poem_set-0-DELETE': u'on',
        }
        formset = PoemFormSet(data, instance=poet)
        formset.save()
        self.failUnless(formset.is_valid())
        self.assertEqual(Poem.objects.count(), 0)

    def test_add_form_deletion_when_invalid(self):
        """
        Make sure that an add form that is filled out, but marked for deletion
        doesn't cause validation errors.
        """
        PoemFormSet = inlineformset_factory(Poet, Poem, can_delete=True)
        poet = Poet.objects.create(name='test')
        data = {
            'poem_set-TOTAL_FORMS': u'1',
            'poem_set-INITIAL_FORMS': u'0',
            'poem_set-0-id': u'',
            'poem_set-0-poem': u'1',
            'poem_set-0-name': u'x' * 1000,
        }
        formset = PoemFormSet(data, instance=poet)
        # Make sure this form doesn't pass validation.
        self.assertEqual(formset.is_valid(), False)
        self.assertEqual(Poem.objects.count(), 0)

        # Then make sure that it *does* pass validation and delete the object,
        # even though the data isn't actually valid.
        data['poem_set-0-DELETE'] = 'on'
        formset = PoemFormSet(data, instance=poet)
        self.assertEqual(formset.is_valid(), True)
        formset.save()
        self.assertEqual(Poem.objects.count(), 0)

    def test_change_form_deletion_when_invalid(self):
        """
        Make sure that a change form that is filled out, but marked for deletion
        doesn't cause validation errors.
        """
        PoemFormSet = inlineformset_factory(Poet, Poem, can_delete=True)
        poet = Poet.objects.create(name='test')
        poet.poem_set.create(name='test poem')
        data = {
            'poem_set-TOTAL_FORMS': u'1',
            'poem_set-INITIAL_FORMS': u'1',
            'poem_set-0-id': u'1',
            'poem_set-0-poem': u'1',
            'poem_set-0-name': u'x' * 1000,
        }
        formset = PoemFormSet(data, instance=poet)
        # Make sure this form doesn't pass validation.
        self.assertEqual(formset.is_valid(), False)
        self.assertEqual(Poem.objects.count(), 1)

        # Then make sure that it *does* pass validation and delete the object,
        # even though the data isn't actually valid.
        data['poem_set-0-DELETE'] = 'on'
        formset = PoemFormSet(data, instance=poet)
        self.assertEqual(formset.is_valid(), True)
        formset.save()
        self.assertEqual(Poem.objects.count(), 0)
