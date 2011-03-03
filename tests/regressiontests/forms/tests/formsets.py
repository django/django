# -*- coding: utf-8 -*-
from django.forms import Form, CharField, IntegerField, ValidationError, DateField
from django.forms.formsets import formset_factory, BaseFormSet
from django.utils.unittest import TestCase


class Choice(Form):
    choice = CharField()
    votes = IntegerField()


# FormSet allows us to use multiple instance of the same form on 1 page. For now,
# the best way to create a FormSet is by using the formset_factory function.
ChoiceFormSet = formset_factory(Choice)


class FavoriteDrinkForm(Form):
    name = CharField()


class BaseFavoriteDrinksFormSet(BaseFormSet):
    def clean(self):
        seen_drinks = []

        for drink in self.cleaned_data:
            if drink['name'] in seen_drinks:
                raise ValidationError('You may only specify a drink once.')

            seen_drinks.append(drink['name'])


class EmptyFsetWontValidate(BaseFormSet):
    def clean(self):
        raise ValidationError("Clean method called")


# Let's define a FormSet that takes a list of favorite drinks, but raises an
# error if there are any duplicates. Used in ``test_clean_hook``,
# ``test_regression_6926`` & ``test_regression_12878``.
FavoriteDrinksFormSet = formset_factory(FavoriteDrinkForm,
    formset=BaseFavoriteDrinksFormSet, extra=3)


class FormsFormsetTestCase(TestCase):
    def test_basic_formset(self):
        # A FormSet constructor takes the same arguments as Form. Let's create a FormSet
        # for adding data. By default, it displays 1 blank form. It can display more,
        # but we'll look at how to do so later.
        formset = ChoiceFormSet(auto_id=False, prefix='choices')
        self.assertEqual(str(formset), """<input type="hidden" name="choices-TOTAL_FORMS" value="1" /><input type="hidden" name="choices-INITIAL_FORMS" value="0" /><input type="hidden" name="choices-MAX_NUM_FORMS" />
<tr><th>Choice:</th><td><input type="text" name="choices-0-choice" /></td></tr>
<tr><th>Votes:</th><td><input type="text" name="choices-0-votes" /></td></tr>""")

        # On thing to note is that there needs to be a special value in the data. This
        # value tells the FormSet how many forms were displayed so it can tell how
        # many forms it needs to clean and validate. You could use javascript to create
        # new forms on the client side, but they won't get validated unless you increment
        # the TOTAL_FORMS field appropriately.

        data = {
            'choices-TOTAL_FORMS': '1', # the number of forms rendered
            'choices-INITIAL_FORMS': '0', # the number of forms with initial data
            'choices-MAX_NUM_FORMS': '0', # max number of forms
            'choices-0-choice': 'Calexico',
            'choices-0-votes': '100',
        }
        # We treat FormSet pretty much like we would treat a normal Form. FormSet has an
        # is_valid method, and a cleaned_data or errors attribute depending on whether all
        # the forms passed validation. However, unlike a Form instance, cleaned_data and
        # errors will be a list of dicts rather than just a single dict.

        formset = ChoiceFormSet(data, auto_id=False, prefix='choices')
        self.assertTrue(formset.is_valid())
        self.assertEqual([form.cleaned_data for form in formset.forms], [{'votes': 100, 'choice': u'Calexico'}])

        # If a FormSet was not passed any data, its is_valid method should return False.
        formset = ChoiceFormSet()
        self.assertFalse(formset.is_valid())

    def test_formset_validation(self):
        # FormSet instances can also have an error attribute if validation failed for
        # any of the forms.

        data = {
            'choices-TOTAL_FORMS': '1', # the number of forms rendered
            'choices-INITIAL_FORMS': '0', # the number of forms with initial data
            'choices-MAX_NUM_FORMS': '0', # max number of forms
            'choices-0-choice': 'Calexico',
            'choices-0-votes': '',
        }

        formset = ChoiceFormSet(data, auto_id=False, prefix='choices')
        self.assertFalse(formset.is_valid())
        self.assertEqual(formset.errors, [{'votes': [u'This field is required.']}])

    def test_formset_initial_data(self):
        # We can also prefill a FormSet with existing data by providing an ``initial``
        # argument to the constructor. ``initial`` should be a list of dicts. By default,
        # an extra blank form is included.

        initial = [{'choice': u'Calexico', 'votes': 100}]
        formset = ChoiceFormSet(initial=initial, auto_id=False, prefix='choices')
        form_output = []

        for form in formset.forms:
            form_output.append(form.as_ul())

        self.assertEqual('\n'.join(form_output), """<li>Choice: <input type="text" name="choices-0-choice" value="Calexico" /></li>
<li>Votes: <input type="text" name="choices-0-votes" value="100" /></li>
<li>Choice: <input type="text" name="choices-1-choice" /></li>
<li>Votes: <input type="text" name="choices-1-votes" /></li>""")

        # Let's simulate what would happen if we submitted this form.

        data = {
            'choices-TOTAL_FORMS': '2', # the number of forms rendered
            'choices-INITIAL_FORMS': '1', # the number of forms with initial data
            'choices-MAX_NUM_FORMS': '0', # max number of forms
            'choices-0-choice': 'Calexico',
            'choices-0-votes': '100',
            'choices-1-choice': '',
            'choices-1-votes': '',
        }

        formset = ChoiceFormSet(data, auto_id=False, prefix='choices')
        self.assertTrue(formset.is_valid())
        self.assertEqual([form.cleaned_data for form in formset.forms], [{'votes': 100, 'choice': u'Calexico'}, {}])

    def test_second_form_partially_filled(self):
        # But the second form was blank! Shouldn't we get some errors? No. If we display
        # a form as blank, it's ok for it to be submitted as blank. If we fill out even
        # one of the fields of a blank form though, it will be validated. We may want to
        # required that at least x number of forms are completed, but we'll show how to
        # handle that later.

        data = {
            'choices-TOTAL_FORMS': '2', # the number of forms rendered
            'choices-INITIAL_FORMS': '1', # the number of forms with initial data
            'choices-MAX_NUM_FORMS': '0', # max number of forms
            'choices-0-choice': 'Calexico',
            'choices-0-votes': '100',
            'choices-1-choice': 'The Decemberists',
            'choices-1-votes': '', # missing value
        }

        formset = ChoiceFormSet(data, auto_id=False, prefix='choices')
        self.assertFalse(formset.is_valid())
        self.assertEqual(formset.errors, [{}, {'votes': [u'This field is required.']}])

    def test_delete_prefilled_data(self):
        # If we delete data that was pre-filled, we should get an error. Simply removing
        # data from form fields isn't the proper way to delete it. We'll see how to
        # handle that case later.

        data = {
            'choices-TOTAL_FORMS': '2', # the number of forms rendered
            'choices-INITIAL_FORMS': '1', # the number of forms with initial data
            'choices-MAX_NUM_FORMS': '0', # max number of forms
            'choices-0-choice': '', # deleted value
            'choices-0-votes': '', # deleted value
            'choices-1-choice': '',
            'choices-1-votes': '',
        }

        formset = ChoiceFormSet(data, auto_id=False, prefix='choices')
        self.assertFalse(formset.is_valid())
        self.assertEqual(formset.errors, [{'votes': [u'This field is required.'], 'choice': [u'This field is required.']}, {}])

    def test_displaying_more_than_one_blank_form(self):
        # Displaying more than 1 blank form ###########################################
        # We can also display more than 1 empty form at a time. To do so, pass a
        # extra argument to formset_factory.
        ChoiceFormSet = formset_factory(Choice, extra=3)

        formset = ChoiceFormSet(auto_id=False, prefix='choices')
        form_output = []

        for form in formset.forms:
            form_output.append(form.as_ul())

        self.assertEqual('\n'.join(form_output), """<li>Choice: <input type="text" name="choices-0-choice" /></li>
<li>Votes: <input type="text" name="choices-0-votes" /></li>
<li>Choice: <input type="text" name="choices-1-choice" /></li>
<li>Votes: <input type="text" name="choices-1-votes" /></li>
<li>Choice: <input type="text" name="choices-2-choice" /></li>
<li>Votes: <input type="text" name="choices-2-votes" /></li>""")

        # Since we displayed every form as blank, we will also accept them back as blank.
        # This may seem a little strange, but later we will show how to require a minimum
        # number of forms to be completed.

        data = {
            'choices-TOTAL_FORMS': '3', # the number of forms rendered
            'choices-INITIAL_FORMS': '0', # the number of forms with initial data
            'choices-MAX_NUM_FORMS': '0', # max number of forms
            'choices-0-choice': '',
            'choices-0-votes': '',
            'choices-1-choice': '',
            'choices-1-votes': '',
            'choices-2-choice': '',
            'choices-2-votes': '',
        }

        formset = ChoiceFormSet(data, auto_id=False, prefix='choices')
        self.assertTrue(formset.is_valid())
        self.assertEqual([form.cleaned_data for form in formset.forms], [{}, {}, {}])

    def test_single_form_completed(self):
        # We can just fill out one of the forms.

        data = {
            'choices-TOTAL_FORMS': '3', # the number of forms rendered
            'choices-INITIAL_FORMS': '0', # the number of forms with initial data
            'choices-MAX_NUM_FORMS': '0', # max number of forms
            'choices-0-choice': 'Calexico',
            'choices-0-votes': '100',
            'choices-1-choice': '',
            'choices-1-votes': '',
            'choices-2-choice': '',
            'choices-2-votes': '',
        }

        ChoiceFormSet = formset_factory(Choice, extra=3)
        formset = ChoiceFormSet(data, auto_id=False, prefix='choices')
        self.assertTrue(formset.is_valid())
        self.assertEqual([form.cleaned_data for form in formset.forms], [{'votes': 100, 'choice': u'Calexico'}, {}, {}])

    def test_second_form_partially_filled_2(self):
        # And once again, if we try to partially complete a form, validation will fail.

        data = {
            'choices-TOTAL_FORMS': '3', # the number of forms rendered
            'choices-INITIAL_FORMS': '0', # the number of forms with initial data
            'choices-MAX_NUM_FORMS': '0', # max number of forms
            'choices-0-choice': 'Calexico',
            'choices-0-votes': '100',
            'choices-1-choice': 'The Decemberists',
            'choices-1-votes': '', # missing value
            'choices-2-choice': '',
            'choices-2-votes': '',
        }

        ChoiceFormSet = formset_factory(Choice, extra=3)
        formset = ChoiceFormSet(data, auto_id=False, prefix='choices')
        self.assertFalse(formset.is_valid())
        self.assertEqual(formset.errors, [{}, {'votes': [u'This field is required.']}, {}])

    def test_more_initial_data(self):
        # The extra argument also works when the formset is pre-filled with initial
        # data.

        data = {
            'choices-TOTAL_FORMS': '3', # the number of forms rendered
            'choices-INITIAL_FORMS': '0', # the number of forms with initial data
            'choices-MAX_NUM_FORMS': '0', # max number of forms
            'choices-0-choice': 'Calexico',
            'choices-0-votes': '100',
            'choices-1-choice': '',
            'choices-1-votes': '', # missing value
            'choices-2-choice': '',
            'choices-2-votes': '',
        }

        initial = [{'choice': u'Calexico', 'votes': 100}]
        ChoiceFormSet = formset_factory(Choice, extra=3)
        formset = ChoiceFormSet(initial=initial, auto_id=False, prefix='choices')
        form_output = []

        for form in formset.forms:
            form_output.append(form.as_ul())

        self.assertEqual('\n'.join(form_output), """<li>Choice: <input type="text" name="choices-0-choice" value="Calexico" /></li>
<li>Votes: <input type="text" name="choices-0-votes" value="100" /></li>
<li>Choice: <input type="text" name="choices-1-choice" /></li>
<li>Votes: <input type="text" name="choices-1-votes" /></li>
<li>Choice: <input type="text" name="choices-2-choice" /></li>
<li>Votes: <input type="text" name="choices-2-votes" /></li>
<li>Choice: <input type="text" name="choices-3-choice" /></li>
<li>Votes: <input type="text" name="choices-3-votes" /></li>""")

        # Make sure retrieving an empty form works, and it shows up in the form list

        self.assertTrue(formset.empty_form.empty_permitted)
        self.assertEqual(formset.empty_form.as_ul(), """<li>Choice: <input type="text" name="choices-__prefix__-choice" /></li>
<li>Votes: <input type="text" name="choices-__prefix__-votes" /></li>""")

    def test_formset_with_deletion(self):
        # FormSets with deletion ######################################################
        # We can easily add deletion ability to a FormSet with an argument to
        # formset_factory. This will add a boolean field to each form instance. When
        # that boolean field is True, the form will be in formset.deleted_forms

        ChoiceFormSet = formset_factory(Choice, can_delete=True)

        initial = [{'choice': u'Calexico', 'votes': 100}, {'choice': u'Fergie', 'votes': 900}]
        formset = ChoiceFormSet(initial=initial, auto_id=False, prefix='choices')
        form_output = []

        for form in formset.forms:
            form_output.append(form.as_ul())

        self.assertEqual('\n'.join(form_output), """<li>Choice: <input type="text" name="choices-0-choice" value="Calexico" /></li>
<li>Votes: <input type="text" name="choices-0-votes" value="100" /></li>
<li>Delete: <input type="checkbox" name="choices-0-DELETE" /></li>
<li>Choice: <input type="text" name="choices-1-choice" value="Fergie" /></li>
<li>Votes: <input type="text" name="choices-1-votes" value="900" /></li>
<li>Delete: <input type="checkbox" name="choices-1-DELETE" /></li>
<li>Choice: <input type="text" name="choices-2-choice" /></li>
<li>Votes: <input type="text" name="choices-2-votes" /></li>
<li>Delete: <input type="checkbox" name="choices-2-DELETE" /></li>""")

        # To delete something, we just need to set that form's special delete field to
        # 'on'. Let's go ahead and delete Fergie.

        data = {
            'choices-TOTAL_FORMS': '3', # the number of forms rendered
            'choices-INITIAL_FORMS': '2', # the number of forms with initial data
            'choices-MAX_NUM_FORMS': '0', # max number of forms
            'choices-0-choice': 'Calexico',
            'choices-0-votes': '100',
            'choices-0-DELETE': '',
            'choices-1-choice': 'Fergie',
            'choices-1-votes': '900',
            'choices-1-DELETE': 'on',
            'choices-2-choice': '',
            'choices-2-votes': '',
            'choices-2-DELETE': '',
        }

        formset = ChoiceFormSet(data, auto_id=False, prefix='choices')
        self.assertTrue(formset.is_valid())
        self.assertEqual([form.cleaned_data for form in formset.forms], [{'votes': 100, 'DELETE': False, 'choice': u'Calexico'}, {'votes': 900, 'DELETE': True, 'choice': u'Fergie'}, {}])
        self.assertEqual([form.cleaned_data for form in formset.deleted_forms], [{'votes': 900, 'DELETE': True, 'choice': u'Fergie'}])

        # If we fill a form with something and then we check the can_delete checkbox for
        # that form, that form's errors should not make the entire formset invalid since
        # it's going to be deleted.

        class CheckForm(Form):
           field = IntegerField(min_value=100)

        data = {
            'check-TOTAL_FORMS': '3', # the number of forms rendered
            'check-INITIAL_FORMS': '2', # the number of forms with initial data
            'check-MAX_NUM_FORMS': '0', # max number of forms
            'check-0-field': '200',
            'check-0-DELETE': '',
            'check-1-field': '50',
            'check-1-DELETE': 'on',
            'check-2-field': '',
            'check-2-DELETE': '',
        }
        CheckFormSet = formset_factory(CheckForm, can_delete=True)
        formset = CheckFormSet(data, prefix='check')
        self.assertTrue(formset.is_valid())

        # If we remove the deletion flag now we will have our validation back.
        data['check-1-DELETE'] = ''
        formset = CheckFormSet(data, prefix='check')
        self.assertFalse(formset.is_valid())

        # Should be able to get deleted_forms from a valid formset even if a
        # deleted form would have been invalid.

        class Person(Form):
            name = CharField()

        PeopleForm = formset_factory(
            form=Person,
            can_delete=True)

        p = PeopleForm(
            {'form-0-name': u'', 'form-0-DELETE': u'on', # no name!
             'form-TOTAL_FORMS': 1, 'form-INITIAL_FORMS': 1,
             'form-MAX_NUM_FORMS': 1})

        self.assertTrue(p.is_valid())
        self.assertEqual(len(p.deleted_forms), 1)

    def test_formsets_with_ordering(self):
        # FormSets with ordering ######################################################
        # We can also add ordering ability to a FormSet with an argument to
        # formset_factory. This will add a integer field to each form instance. When
        # form validation succeeds, [form.cleaned_data for form in formset.forms] will have the data in the correct
        # order specified by the ordering fields. If a number is duplicated in the set
        # of ordering fields, for instance form 0 and form 3 are both marked as 1, then
        # the form index used as a secondary ordering criteria. In order to put
        # something at the front of the list, you'd need to set it's order to 0.

        ChoiceFormSet = formset_factory(Choice, can_order=True)

        initial = [{'choice': u'Calexico', 'votes': 100}, {'choice': u'Fergie', 'votes': 900}]
        formset = ChoiceFormSet(initial=initial, auto_id=False, prefix='choices')
        form_output = []

        for form in formset.forms:
            form_output.append(form.as_ul())

        self.assertEqual('\n'.join(form_output), """<li>Choice: <input type="text" name="choices-0-choice" value="Calexico" /></li>
<li>Votes: <input type="text" name="choices-0-votes" value="100" /></li>
<li>Order: <input type="text" name="choices-0-ORDER" value="1" /></li>
<li>Choice: <input type="text" name="choices-1-choice" value="Fergie" /></li>
<li>Votes: <input type="text" name="choices-1-votes" value="900" /></li>
<li>Order: <input type="text" name="choices-1-ORDER" value="2" /></li>
<li>Choice: <input type="text" name="choices-2-choice" /></li>
<li>Votes: <input type="text" name="choices-2-votes" /></li>
<li>Order: <input type="text" name="choices-2-ORDER" /></li>""")

        data = {
            'choices-TOTAL_FORMS': '3', # the number of forms rendered
            'choices-INITIAL_FORMS': '2', # the number of forms with initial data
            'choices-MAX_NUM_FORMS': '0', # max number of forms
            'choices-0-choice': 'Calexico',
            'choices-0-votes': '100',
            'choices-0-ORDER': '1',
            'choices-1-choice': 'Fergie',
            'choices-1-votes': '900',
            'choices-1-ORDER': '2',
            'choices-2-choice': 'The Decemberists',
            'choices-2-votes': '500',
            'choices-2-ORDER': '0',
        }

        formset = ChoiceFormSet(data, auto_id=False, prefix='choices')
        self.assertTrue(formset.is_valid())
        form_output = []

        for form in formset.ordered_forms:
            form_output.append(form.cleaned_data)

        self.assertEqual(form_output, [
            {'votes': 500, 'ORDER': 0, 'choice': u'The Decemberists'},
            {'votes': 100, 'ORDER': 1, 'choice': u'Calexico'},
            {'votes': 900, 'ORDER': 2, 'choice': u'Fergie'},
        ])

    def test_empty_ordered_fields(self):
        # Ordering fields are allowed to be left blank, and if they *are* left blank,
        # they will be sorted below everything else.

        data = {
            'choices-TOTAL_FORMS': '4', # the number of forms rendered
            'choices-INITIAL_FORMS': '3', # the number of forms with initial data
            'choices-MAX_NUM_FORMS': '0', # max number of forms
            'choices-0-choice': 'Calexico',
            'choices-0-votes': '100',
            'choices-0-ORDER': '1',
            'choices-1-choice': 'Fergie',
            'choices-1-votes': '900',
            'choices-1-ORDER': '2',
            'choices-2-choice': 'The Decemberists',
            'choices-2-votes': '500',
            'choices-2-ORDER': '',
            'choices-3-choice': 'Basia Bulat',
            'choices-3-votes': '50',
            'choices-3-ORDER': '',
        }

        ChoiceFormSet = formset_factory(Choice, can_order=True)
        formset = ChoiceFormSet(data, auto_id=False, prefix='choices')
        self.assertTrue(formset.is_valid())
        form_output = []

        for form in formset.ordered_forms:
            form_output.append(form.cleaned_data)

        self.assertEqual(form_output, [
            {'votes': 100, 'ORDER': 1, 'choice': u'Calexico'},
            {'votes': 900, 'ORDER': 2, 'choice': u'Fergie'},
            {'votes': 500, 'ORDER': None, 'choice': u'The Decemberists'},
            {'votes': 50, 'ORDER': None, 'choice': u'Basia Bulat'},
        ])

    def test_ordering_blank_fieldsets(self):
        # Ordering should work with blank fieldsets.

        data = {
            'choices-TOTAL_FORMS': '3', # the number of forms rendered
            'choices-INITIAL_FORMS': '0', # the number of forms with initial data
            'choices-MAX_NUM_FORMS': '0', # max number of forms
        }

        ChoiceFormSet = formset_factory(Choice, can_order=True)
        formset = ChoiceFormSet(data, auto_id=False, prefix='choices')
        self.assertTrue(formset.is_valid())
        form_output = []

        for form in formset.ordered_forms:
            form_output.append(form.cleaned_data)

        self.assertEqual(form_output, [])

    def test_formset_with_ordering_and_deletion(self):
        # FormSets with ordering + deletion ###########################################
        # Let's try throwing ordering and deletion into the same form.

        ChoiceFormSet = formset_factory(Choice, can_order=True, can_delete=True)

        initial = [
            {'choice': u'Calexico', 'votes': 100},
            {'choice': u'Fergie', 'votes': 900},
            {'choice': u'The Decemberists', 'votes': 500},
        ]
        formset = ChoiceFormSet(initial=initial, auto_id=False, prefix='choices')
        form_output = []

        for form in formset.forms:
            form_output.append(form.as_ul())

        self.assertEqual('\n'.join(form_output), """<li>Choice: <input type="text" name="choices-0-choice" value="Calexico" /></li>
<li>Votes: <input type="text" name="choices-0-votes" value="100" /></li>
<li>Order: <input type="text" name="choices-0-ORDER" value="1" /></li>
<li>Delete: <input type="checkbox" name="choices-0-DELETE" /></li>
<li>Choice: <input type="text" name="choices-1-choice" value="Fergie" /></li>
<li>Votes: <input type="text" name="choices-1-votes" value="900" /></li>
<li>Order: <input type="text" name="choices-1-ORDER" value="2" /></li>
<li>Delete: <input type="checkbox" name="choices-1-DELETE" /></li>
<li>Choice: <input type="text" name="choices-2-choice" value="The Decemberists" /></li>
<li>Votes: <input type="text" name="choices-2-votes" value="500" /></li>
<li>Order: <input type="text" name="choices-2-ORDER" value="3" /></li>
<li>Delete: <input type="checkbox" name="choices-2-DELETE" /></li>
<li>Choice: <input type="text" name="choices-3-choice" /></li>
<li>Votes: <input type="text" name="choices-3-votes" /></li>
<li>Order: <input type="text" name="choices-3-ORDER" /></li>
<li>Delete: <input type="checkbox" name="choices-3-DELETE" /></li>""")

        # Let's delete Fergie, and put The Decemberists ahead of Calexico.

        data = {
            'choices-TOTAL_FORMS': '4', # the number of forms rendered
            'choices-INITIAL_FORMS': '3', # the number of forms with initial data
            'choices-MAX_NUM_FORMS': '0', # max number of forms
            'choices-0-choice': 'Calexico',
            'choices-0-votes': '100',
            'choices-0-ORDER': '1',
            'choices-0-DELETE': '',
            'choices-1-choice': 'Fergie',
            'choices-1-votes': '900',
            'choices-1-ORDER': '2',
            'choices-1-DELETE': 'on',
            'choices-2-choice': 'The Decemberists',
            'choices-2-votes': '500',
            'choices-2-ORDER': '0',
            'choices-2-DELETE': '',
            'choices-3-choice': '',
            'choices-3-votes': '',
            'choices-3-ORDER': '',
            'choices-3-DELETE': '',
        }

        formset = ChoiceFormSet(data, auto_id=False, prefix='choices')
        self.assertTrue(formset.is_valid())
        form_output = []

        for form in formset.ordered_forms:
            form_output.append(form.cleaned_data)

        self.assertEqual(form_output, [
            {'votes': 500, 'DELETE': False, 'ORDER': 0, 'choice': u'The Decemberists'},
            {'votes': 100, 'DELETE': False, 'ORDER': 1, 'choice': u'Calexico'},
        ])
        self.assertEqual([form.cleaned_data for form in formset.deleted_forms], [{'votes': 900, 'DELETE': True, 'ORDER': 2, 'choice': u'Fergie'}])

    def test_invalid_deleted_form_with_ordering(self):
        # Should be able to get ordered forms from a valid formset even if a
        # deleted form would have been invalid.

        class Person(Form):
            name = CharField()

        PeopleForm = formset_factory(form=Person, can_delete=True, can_order=True)

        p = PeopleForm({
            'form-0-name': u'',
            'form-0-DELETE': u'on', # no name!
            'form-TOTAL_FORMS': 1,
            'form-INITIAL_FORMS': 1,
            'form-MAX_NUM_FORMS': 1
        })

        self.assertTrue(p.is_valid())
        self.assertEqual(p.ordered_forms, [])

    def test_clean_hook(self):
        # FormSet clean hook ##########################################################
        # FormSets have a hook for doing extra validation that shouldn't be tied to any
        # particular form. It follows the same pattern as the clean hook on Forms.

        # We start out with a some duplicate data.

        data = {
            'drinks-TOTAL_FORMS': '2', # the number of forms rendered
            'drinks-INITIAL_FORMS': '0', # the number of forms with initial data
            'drinks-MAX_NUM_FORMS': '0', # max number of forms
            'drinks-0-name': 'Gin and Tonic',
            'drinks-1-name': 'Gin and Tonic',
        }

        formset = FavoriteDrinksFormSet(data, prefix='drinks')
        self.assertFalse(formset.is_valid())

        # Any errors raised by formset.clean() are available via the
        # formset.non_form_errors() method.

        for error in formset.non_form_errors():
            self.assertEqual(str(error), 'You may only specify a drink once.')

        # Make sure we didn't break the valid case.

        data = {
            'drinks-TOTAL_FORMS': '2', # the number of forms rendered
            'drinks-INITIAL_FORMS': '0', # the number of forms with initial data
            'drinks-MAX_NUM_FORMS': '0', # max number of forms
            'drinks-0-name': 'Gin and Tonic',
            'drinks-1-name': 'Bloody Mary',
        }

        formset = FavoriteDrinksFormSet(data, prefix='drinks')
        self.assertTrue(formset.is_valid())
        self.assertEqual(formset.non_form_errors(), [])

    def test_limiting_max_forms(self):
        # Limiting the maximum number of forms ########################################
        # Base case for max_num.

        # When not passed, max_num will take its default value of None, i.e. unlimited
        # number of forms, only controlled by the value of the extra parameter.

        LimitedFavoriteDrinkFormSet = formset_factory(FavoriteDrinkForm, extra=3)
        formset = LimitedFavoriteDrinkFormSet()
        form_output = []

        for form in formset.forms:
            form_output.append(str(form))

        self.assertEqual('\n'.join(form_output), """<tr><th><label for="id_form-0-name">Name:</label></th><td><input type="text" name="form-0-name" id="id_form-0-name" /></td></tr>
<tr><th><label for="id_form-1-name">Name:</label></th><td><input type="text" name="form-1-name" id="id_form-1-name" /></td></tr>
<tr><th><label for="id_form-2-name">Name:</label></th><td><input type="text" name="form-2-name" id="id_form-2-name" /></td></tr>""")

        # If max_num is 0 then no form is rendered at all.
        LimitedFavoriteDrinkFormSet = formset_factory(FavoriteDrinkForm, extra=3, max_num=0)
        formset = LimitedFavoriteDrinkFormSet()
        form_output = []

        for form in formset.forms:
            form_output.append(str(form))

        self.assertEqual('\n'.join(form_output), "")

        LimitedFavoriteDrinkFormSet = formset_factory(FavoriteDrinkForm, extra=5, max_num=2)
        formset = LimitedFavoriteDrinkFormSet()
        form_output = []

        for form in formset.forms:
            form_output.append(str(form))

        self.assertEqual('\n'.join(form_output), """<tr><th><label for="id_form-0-name">Name:</label></th><td><input type="text" name="form-0-name" id="id_form-0-name" /></td></tr>
<tr><th><label for="id_form-1-name">Name:</label></th><td><input type="text" name="form-1-name" id="id_form-1-name" /></td></tr>""")

        # Ensure that max_num has no effect when extra is less than max_num.

        LimitedFavoriteDrinkFormSet = formset_factory(FavoriteDrinkForm, extra=1, max_num=2)
        formset = LimitedFavoriteDrinkFormSet()
        form_output = []

        for form in formset.forms:
            form_output.append(str(form))

        self.assertEqual('\n'.join(form_output), """<tr><th><label for="id_form-0-name">Name:</label></th><td><input type="text" name="form-0-name" id="id_form-0-name" /></td></tr>""")

    def test_max_num_with_initial_data(self):
        # max_num with initial data

        # When not passed, max_num will take its default value of None, i.e. unlimited
        # number of forms, only controlled by the values of the initial and extra
        # parameters.

        initial = [
            {'name': 'Fernet and Coke'},
        ]
        LimitedFavoriteDrinkFormSet = formset_factory(FavoriteDrinkForm, extra=1)
        formset = LimitedFavoriteDrinkFormSet(initial=initial)
        form_output = []

        for form in formset.forms:
            form_output.append(str(form))

        self.assertEqual('\n'.join(form_output), """<tr><th><label for="id_form-0-name">Name:</label></th><td><input type="text" name="form-0-name" value="Fernet and Coke" id="id_form-0-name" /></td></tr>
<tr><th><label for="id_form-1-name">Name:</label></th><td><input type="text" name="form-1-name" id="id_form-1-name" /></td></tr>""")

    def test_max_num_zero(self):
        # If max_num is 0 then no form is rendered at all, even if extra and initial
        # are specified.

        initial = [
            {'name': 'Fernet and Coke'},
            {'name': 'Bloody Mary'},
        ]
        LimitedFavoriteDrinkFormSet = formset_factory(FavoriteDrinkForm, extra=1, max_num=0)
        formset = LimitedFavoriteDrinkFormSet(initial=initial)
        form_output = []

        for form in formset.forms:
            form_output.append(str(form))

        self.assertEqual('\n'.join(form_output), "")

    def test_more_initial_than_max_num(self):
        # More initial forms than max_num will result in only the first max_num of
        # them to be displayed with no extra forms.

        initial = [
            {'name': 'Gin Tonic'},
            {'name': 'Bloody Mary'},
            {'name': 'Jack and Coke'},
        ]
        LimitedFavoriteDrinkFormSet = formset_factory(FavoriteDrinkForm, extra=1, max_num=2)
        formset = LimitedFavoriteDrinkFormSet(initial=initial)
        form_output = []

        for form in formset.forms:
            form_output.append(str(form))

        self.assertEqual('\n'.join(form_output), """<tr><th><label for="id_form-0-name">Name:</label></th><td><input type="text" name="form-0-name" value="Gin Tonic" id="id_form-0-name" /></td></tr>
<tr><th><label for="id_form-1-name">Name:</label></th><td><input type="text" name="form-1-name" value="Bloody Mary" id="id_form-1-name" /></td></tr>""")

        # One form from initial and extra=3 with max_num=2 should result in the one
        # initial form and one extra.
        initial = [
            {'name': 'Gin Tonic'},
        ]
        LimitedFavoriteDrinkFormSet = formset_factory(FavoriteDrinkForm, extra=3, max_num=2)
        formset = LimitedFavoriteDrinkFormSet(initial=initial)
        form_output = []

        for form in formset.forms:
            form_output.append(str(form))

        self.assertEqual('\n'.join(form_output), """<tr><th><label for="id_form-0-name">Name:</label></th><td><input type="text" name="form-0-name" value="Gin Tonic" id="id_form-0-name" /></td></tr>
<tr><th><label for="id_form-1-name">Name:</label></th><td><input type="text" name="form-1-name" id="id_form-1-name" /></td></tr>""")

    def test_regression_6926(self):
        # Regression test for #6926 ##################################################
        # Make sure the management form has the correct prefix.

        formset = FavoriteDrinksFormSet()
        self.assertEqual(formset.management_form.prefix, 'form')

        data = {
            'form-TOTAL_FORMS': '2',
            'form-INITIAL_FORMS': '0',
            'form-MAX_NUM_FORMS': '0',
        }
        formset = FavoriteDrinksFormSet(data=data)
        self.assertEqual(formset.management_form.prefix, 'form')

        formset = FavoriteDrinksFormSet(initial={})
        self.assertEqual(formset.management_form.prefix, 'form')

    def test_regression_12878(self):
        # Regression test for #12878 #################################################

        data = {
            'drinks-TOTAL_FORMS': '2', # the number of forms rendered
            'drinks-INITIAL_FORMS': '0', # the number of forms with initial data
            'drinks-MAX_NUM_FORMS': '0', # max number of forms
            'drinks-0-name': 'Gin and Tonic',
            'drinks-1-name': 'Gin and Tonic',
        }

        formset = FavoriteDrinksFormSet(data, prefix='drinks')
        self.assertFalse(formset.is_valid())
        self.assertEqual(formset.non_form_errors(), [u'You may only specify a drink once.'])

    def test_formset_iteration(self):
        # Regression tests for #16455 -- formset instances are iterable
        ChoiceFormset = formset_factory(Choice, extra=3)
        formset = ChoiceFormset()

        # confirm iterated formset yields formset.forms
        forms = list(formset)
        self.assertEqual(forms, formset.forms)
        self.assertEqual(len(formset), len(forms))

        # confirm indexing of formset
        self.assertEqual(formset[0], forms[0])
        try:
            formset[3]
            self.fail('Requesting an invalid formset index should raise an exception')
        except IndexError:
            pass

        # Formets can override the default iteration order
        class BaseReverseFormSet(BaseFormSet):
            def __iter__(self):
                for form in reversed(self.forms):
                    yield form

        ReverseChoiceFormset = formset_factory(Choice, BaseReverseFormSet, extra=3)
        reverse_formset = ReverseChoiceFormset()

        # confirm that __iter__ modifies rendering order
        # compare forms from "reverse" formset with forms from original formset
        self.assertEqual(str(reverse_formset[0]), str(forms[-1]))
        self.assertEqual(str(reverse_formset[1]), str(forms[-2]))
        self.assertEqual(len(reverse_formset), len(forms))

data = {
    'choices-TOTAL_FORMS': '1', # the number of forms rendered
    'choices-INITIAL_FORMS': '0', # the number of forms with initial data
    'choices-MAX_NUM_FORMS': '0', # max number of forms
    'choices-0-choice': 'Calexico',
    'choices-0-votes': '100',
}

class Choice(Form):
    choice = CharField()
    votes = IntegerField()

ChoiceFormSet = formset_factory(Choice)

class FormsetAsFooTests(TestCase):
    def test_as_table(self):
        formset = ChoiceFormSet(data, auto_id=False, prefix='choices')
        self.assertEqual(formset.as_table(),"""<input type="hidden" name="choices-TOTAL_FORMS" value="1" /><input type="hidden" name="choices-INITIAL_FORMS" value="0" /><input type="hidden" name="choices-MAX_NUM_FORMS" value="0" />
<tr><th>Choice:</th><td><input type="text" name="choices-0-choice" value="Calexico" /></td></tr>
<tr><th>Votes:</th><td><input type="text" name="choices-0-votes" value="100" /></td></tr>""")

    def test_as_p(self):
        formset = ChoiceFormSet(data, auto_id=False, prefix='choices')
        self.assertEqual(formset.as_p(),"""<input type="hidden" name="choices-TOTAL_FORMS" value="1" /><input type="hidden" name="choices-INITIAL_FORMS" value="0" /><input type="hidden" name="choices-MAX_NUM_FORMS" value="0" />
<p>Choice: <input type="text" name="choices-0-choice" value="Calexico" /></p>
<p>Votes: <input type="text" name="choices-0-votes" value="100" /></p>""")

    def test_as_ul(self):
        formset = ChoiceFormSet(data, auto_id=False, prefix='choices')
        self.assertEqual(formset.as_ul(),"""<input type="hidden" name="choices-TOTAL_FORMS" value="1" /><input type="hidden" name="choices-INITIAL_FORMS" value="0" /><input type="hidden" name="choices-MAX_NUM_FORMS" value="0" />
<li>Choice: <input type="text" name="choices-0-choice" value="Calexico" /></li>
<li>Votes: <input type="text" name="choices-0-votes" value="100" /></li>""")


# Regression test for #11418 #################################################
class ArticleForm(Form):
    title = CharField()
    pub_date = DateField()

ArticleFormSet = formset_factory(ArticleForm)

class TestIsBoundBehavior(TestCase):
    def test_no_data_raises_validation_error(self):
        self.assertRaises(ValidationError, ArticleFormSet, {})

    def test_with_management_data_attrs_work_fine(self):
        data = {
            'form-TOTAL_FORMS': u'1',
            'form-INITIAL_FORMS': u'0',
        }
        formset = ArticleFormSet(data)
        self.assertEqual(0, formset.initial_form_count())
        self.assertEqual(1, formset.total_form_count())
        self.assertTrue(formset.is_bound)
        self.assertTrue(formset.forms[0].is_bound)
        self.assertTrue(formset.is_valid())
        self.assertTrue(formset.forms[0].is_valid())
        self.assertEqual([{}], formset.cleaned_data)


    def test_form_errors_are_cought_by_formset(self):
        data = {
            'form-TOTAL_FORMS': u'2',
            'form-INITIAL_FORMS': u'0',
            'form-0-title': u'Test',
            'form-0-pub_date': u'1904-06-16',
            'form-1-title': u'Test',
            'form-1-pub_date': u'', # <-- this date is missing but required
        }
        formset = ArticleFormSet(data)
        self.assertFalse(formset.is_valid())
        self.assertEqual([{}, {'pub_date': [u'This field is required.']}], formset.errors)

    def test_empty_forms_are_unbound(self):
        data = {
            'form-TOTAL_FORMS': u'1',
            'form-INITIAL_FORMS': u'0',
            'form-0-title': u'Test',
            'form-0-pub_date': u'1904-06-16',
        }
        unbound_formset = ArticleFormSet()
        bound_formset = ArticleFormSet(data)

        empty_forms = []

        empty_forms.append(unbound_formset.empty_form)
        empty_forms.append(bound_formset.empty_form)

        # Empty forms should be unbound
        self.assertFalse(empty_forms[0].is_bound)
        self.assertFalse(empty_forms[1].is_bound)

        # The empty forms should be equal.
        self.assertEqual(empty_forms[0].as_p(), empty_forms[1].as_p())

class TestEmptyFormSet(TestCase): 
    "Test that an empty formset still calls clean()"
    def test_empty_formset_is_valid(self): 
        EmptyFsetWontValidateFormset = formset_factory(FavoriteDrinkForm, extra=0, formset=EmptyFsetWontValidate) 
        formset = EmptyFsetWontValidateFormset(data={'form-INITIAL_FORMS':'0', 'form-TOTAL_FORMS':'0'},prefix="form") 
        formset2 = EmptyFsetWontValidateFormset(data={'form-INITIAL_FORMS':'0', 'form-TOTAL_FORMS':'1', 'form-0-name':'bah' },prefix="form") 
        self.assertFalse(formset.is_valid()) 
        self.assertFalse(formset2.is_valid()) 

