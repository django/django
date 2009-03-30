# -*- coding: utf-8 -*-
tests = """
# Basic FormSet creation and usage ############################################

FormSet allows us to use multiple instance of the same form on 1 page. For now,
the best way to create a FormSet is by using the formset_factory function.

>>> from django.forms import Form, CharField, IntegerField, ValidationError
>>> from django.forms.formsets import formset_factory, BaseFormSet

>>> class Choice(Form):
...     choice = CharField()
...     votes = IntegerField()

>>> ChoiceFormSet = formset_factory(Choice)

A FormSet constructor takes the same arguments as Form. Let's create a FormSet
for adding data. By default, it displays 1 blank form. It can display more,
but we'll look at how to do so later.

>>> formset = ChoiceFormSet(auto_id=False, prefix='choices')
>>> print formset
<input type="hidden" name="choices-TOTAL_FORMS" value="1" /><input type="hidden" name="choices-INITIAL_FORMS" value="0" />
<tr><th>Choice:</th><td><input type="text" name="choices-0-choice" /></td></tr>
<tr><th>Votes:</th><td><input type="text" name="choices-0-votes" /></td></tr>


On thing to note is that there needs to be a special value in the data. This
value tells the FormSet how many forms were displayed so it can tell how
many forms it needs to clean and validate. You could use javascript to create
new forms on the client side, but they won't get validated unless you increment
the TOTAL_FORMS field appropriately.

>>> data = {
...     'choices-TOTAL_FORMS': '1', # the number of forms rendered
...     'choices-INITIAL_FORMS': '0', # the number of forms with initial data
...     'choices-0-choice': 'Calexico',
...     'choices-0-votes': '100',
... }

We treat FormSet pretty much like we would treat a normal Form. FormSet has an
is_valid method, and a cleaned_data or errors attribute depending on whether all
the forms passed validation. However, unlike a Form instance, cleaned_data and
errors will be a list of dicts rather than just a single dict.

>>> formset = ChoiceFormSet(data, auto_id=False, prefix='choices')
>>> formset.is_valid()
True
>>> [form.cleaned_data for form in formset.forms]
[{'votes': 100, 'choice': u'Calexico'}]

If a FormSet was not passed any data, its is_valid method should return False.
>>> formset = ChoiceFormSet()
>>> formset.is_valid()
False

FormSet instances can also have an error attribute if validation failed for
any of the forms.

>>> data = {
...     'choices-TOTAL_FORMS': '1', # the number of forms rendered
...     'choices-INITIAL_FORMS': '0', # the number of forms with initial data
...     'choices-0-choice': 'Calexico',
...     'choices-0-votes': '',
... }

>>> formset = ChoiceFormSet(data, auto_id=False, prefix='choices')
>>> formset.is_valid()
False
>>> formset.errors
[{'votes': [u'This field is required.']}]


We can also prefill a FormSet with existing data by providing an ``initial``
argument to the constructor. ``initial`` should be a list of dicts. By default,
an extra blank form is included.

>>> initial = [{'choice': u'Calexico', 'votes': 100}]
>>> formset = ChoiceFormSet(initial=initial, auto_id=False, prefix='choices')
>>> for form in formset.forms:
...    print form.as_ul()
<li>Choice: <input type="text" name="choices-0-choice" value="Calexico" /></li>
<li>Votes: <input type="text" name="choices-0-votes" value="100" /></li>
<li>Choice: <input type="text" name="choices-1-choice" /></li>
<li>Votes: <input type="text" name="choices-1-votes" /></li>


Let's simulate what would happen if we submitted this form.

>>> data = {
...     'choices-TOTAL_FORMS': '2', # the number of forms rendered
...     'choices-INITIAL_FORMS': '1', # the number of forms with initial data
...     'choices-0-choice': 'Calexico',
...     'choices-0-votes': '100',
...     'choices-1-choice': '',
...     'choices-1-votes': '',
... }

>>> formset = ChoiceFormSet(data, auto_id=False, prefix='choices')
>>> formset.is_valid()
True
>>> [form.cleaned_data for form in formset.forms]
[{'votes': 100, 'choice': u'Calexico'}, {}]

But the second form was blank! Shouldn't we get some errors? No. If we display
a form as blank, it's ok for it to be submitted as blank. If we fill out even
one of the fields of a blank form though, it will be validated. We may want to
required that at least x number of forms are completed, but we'll show how to
handle that later.

>>> data = {
...     'choices-TOTAL_FORMS': '2', # the number of forms rendered
...     'choices-INITIAL_FORMS': '1', # the number of forms with initial data
...     'choices-0-choice': 'Calexico',
...     'choices-0-votes': '100',
...     'choices-1-choice': 'The Decemberists',
...     'choices-1-votes': '', # missing value
... }

>>> formset = ChoiceFormSet(data, auto_id=False, prefix='choices')
>>> formset.is_valid()
False
>>> formset.errors
[{}, {'votes': [u'This field is required.']}]

If we delete data that was pre-filled, we should get an error. Simply removing
data from form fields isn't the proper way to delete it. We'll see how to
handle that case later.

>>> data = {
...     'choices-TOTAL_FORMS': '2', # the number of forms rendered
...     'choices-INITIAL_FORMS': '1', # the number of forms with initial data
...     'choices-0-choice': '', # deleted value
...     'choices-0-votes': '', # deleted value
...     'choices-1-choice': '',
...     'choices-1-votes': '',
... }

>>> formset = ChoiceFormSet(data, auto_id=False, prefix='choices')
>>> formset.is_valid()
False
>>> formset.errors
[{'votes': [u'This field is required.'], 'choice': [u'This field is required.']}, {}]


# Displaying more than 1 blank form ###########################################

We can also display more than 1 empty form at a time. To do so, pass a
extra argument to formset_factory.

>>> ChoiceFormSet = formset_factory(Choice, extra=3)

>>> formset = ChoiceFormSet(auto_id=False, prefix='choices')
>>> for form in formset.forms:
...    print form.as_ul()
<li>Choice: <input type="text" name="choices-0-choice" /></li>
<li>Votes: <input type="text" name="choices-0-votes" /></li>
<li>Choice: <input type="text" name="choices-1-choice" /></li>
<li>Votes: <input type="text" name="choices-1-votes" /></li>
<li>Choice: <input type="text" name="choices-2-choice" /></li>
<li>Votes: <input type="text" name="choices-2-votes" /></li>

Since we displayed every form as blank, we will also accept them back as blank.
This may seem a little strange, but later we will show how to require a minimum
number of forms to be completed.

>>> data = {
...     'choices-TOTAL_FORMS': '3', # the number of forms rendered
...     'choices-INITIAL_FORMS': '0', # the number of forms with initial data
...     'choices-0-choice': '',
...     'choices-0-votes': '',
...     'choices-1-choice': '',
...     'choices-1-votes': '',
...     'choices-2-choice': '',
...     'choices-2-votes': '',
... }

>>> formset = ChoiceFormSet(data, auto_id=False, prefix='choices')
>>> formset.is_valid()
True
>>> [form.cleaned_data for form in formset.forms]
[{}, {}, {}]


We can just fill out one of the forms.

>>> data = {
...     'choices-TOTAL_FORMS': '3', # the number of forms rendered
...     'choices-INITIAL_FORMS': '0', # the number of forms with initial data
...     'choices-0-choice': 'Calexico',
...     'choices-0-votes': '100',
...     'choices-1-choice': '',
...     'choices-1-votes': '',
...     'choices-2-choice': '',
...     'choices-2-votes': '',
... }

>>> formset = ChoiceFormSet(data, auto_id=False, prefix='choices')
>>> formset.is_valid()
True
>>> [form.cleaned_data for form in formset.forms]
[{'votes': 100, 'choice': u'Calexico'}, {}, {}]


And once again, if we try to partially complete a form, validation will fail.

>>> data = {
...     'choices-TOTAL_FORMS': '3', # the number of forms rendered
...     'choices-INITIAL_FORMS': '0', # the number of forms with initial data
...     'choices-0-choice': 'Calexico',
...     'choices-0-votes': '100',
...     'choices-1-choice': 'The Decemberists',
...     'choices-1-votes': '', # missing value
...     'choices-2-choice': '',
...     'choices-2-votes': '',
... }

>>> formset = ChoiceFormSet(data, auto_id=False, prefix='choices')
>>> formset.is_valid()
False
>>> formset.errors
[{}, {'votes': [u'This field is required.']}, {}]


The extra argument also works when the formset is pre-filled with initial
data.

>>> initial = [{'choice': u'Calexico', 'votes': 100}]
>>> formset = ChoiceFormSet(initial=initial, auto_id=False, prefix='choices')
>>> for form in formset.forms:
...    print form.as_ul()
<li>Choice: <input type="text" name="choices-0-choice" value="Calexico" /></li>
<li>Votes: <input type="text" name="choices-0-votes" value="100" /></li>
<li>Choice: <input type="text" name="choices-1-choice" /></li>
<li>Votes: <input type="text" name="choices-1-votes" /></li>
<li>Choice: <input type="text" name="choices-2-choice" /></li>
<li>Votes: <input type="text" name="choices-2-votes" /></li>
<li>Choice: <input type="text" name="choices-3-choice" /></li>
<li>Votes: <input type="text" name="choices-3-votes" /></li>


# FormSets with deletion ######################################################

We can easily add deletion ability to a FormSet with an argument to
formset_factory. This will add a boolean field to each form instance. When
that boolean field is True, the form will be in formset.deleted_forms

>>> ChoiceFormSet = formset_factory(Choice, can_delete=True)

>>> initial = [{'choice': u'Calexico', 'votes': 100}, {'choice': u'Fergie', 'votes': 900}]
>>> formset = ChoiceFormSet(initial=initial, auto_id=False, prefix='choices')
>>> for form in formset.forms:
...    print form.as_ul()
<li>Choice: <input type="text" name="choices-0-choice" value="Calexico" /></li>
<li>Votes: <input type="text" name="choices-0-votes" value="100" /></li>
<li>Delete: <input type="checkbox" name="choices-0-DELETE" /></li>
<li>Choice: <input type="text" name="choices-1-choice" value="Fergie" /></li>
<li>Votes: <input type="text" name="choices-1-votes" value="900" /></li>
<li>Delete: <input type="checkbox" name="choices-1-DELETE" /></li>
<li>Choice: <input type="text" name="choices-2-choice" /></li>
<li>Votes: <input type="text" name="choices-2-votes" /></li>
<li>Delete: <input type="checkbox" name="choices-2-DELETE" /></li>

To delete something, we just need to set that form's special delete field to
'on'. Let's go ahead and delete Fergie.

>>> data = {
...     'choices-TOTAL_FORMS': '3', # the number of forms rendered
...     'choices-INITIAL_FORMS': '2', # the number of forms with initial data
...     'choices-0-choice': 'Calexico',
...     'choices-0-votes': '100',
...     'choices-0-DELETE': '',
...     'choices-1-choice': 'Fergie',
...     'choices-1-votes': '900',
...     'choices-1-DELETE': 'on',
...     'choices-2-choice': '',
...     'choices-2-votes': '',
...     'choices-2-DELETE': '',
... }

>>> formset = ChoiceFormSet(data, auto_id=False, prefix='choices')
>>> formset.is_valid()
True
>>> [form.cleaned_data for form in formset.forms]
[{'votes': 100, 'DELETE': False, 'choice': u'Calexico'}, {'votes': 900, 'DELETE': True, 'choice': u'Fergie'}, {}]
>>> [form.cleaned_data for form in formset.deleted_forms]
[{'votes': 900, 'DELETE': True, 'choice': u'Fergie'}]

If we fill a form with something and then we check the can_delete checkbox for
that form, that form's errors should not make the entire formset invalid since
it's going to be deleted.

>>> class CheckForm(Form):
...    field = IntegerField(min_value=100)

>>> data = {
...     'check-TOTAL_FORMS': '3', # the number of forms rendered
...     'check-INITIAL_FORMS': '2', # the number of forms with initial data
...     'check-0-field': '200',
...     'check-0-DELETE': '',
...     'check-1-field': '50',
...     'check-1-DELETE': 'on',
...     'check-2-field': '',
...     'check-2-DELETE': '',
... }
>>> CheckFormSet = formset_factory(CheckForm, can_delete=True)
>>> formset = CheckFormSet(data, prefix='check')
>>> formset.is_valid()
True

If we remove the deletion flag now we will have our validation back.

>>> data['check-1-DELETE'] = ''
>>> formset = CheckFormSet(data, prefix='check')
>>> formset.is_valid()
False

# FormSets with ordering ######################################################

We can also add ordering ability to a FormSet with an agrument to
formset_factory. This will add a integer field to each form instance. When
form validation succeeds, [form.cleaned_data for form in formset.forms] will have the data in the correct
order specified by the ordering fields. If a number is duplicated in the set
of ordering fields, for instance form 0 and form 3 are both marked as 1, then
the form index used as a secondary ordering criteria. In order to put
something at the front of the list, you'd need to set it's order to 0.

>>> ChoiceFormSet = formset_factory(Choice, can_order=True)

>>> initial = [{'choice': u'Calexico', 'votes': 100}, {'choice': u'Fergie', 'votes': 900}]
>>> formset = ChoiceFormSet(initial=initial, auto_id=False, prefix='choices')
>>> for form in formset.forms:
...    print form.as_ul()
<li>Choice: <input type="text" name="choices-0-choice" value="Calexico" /></li>
<li>Votes: <input type="text" name="choices-0-votes" value="100" /></li>
<li>Order: <input type="text" name="choices-0-ORDER" value="1" /></li>
<li>Choice: <input type="text" name="choices-1-choice" value="Fergie" /></li>
<li>Votes: <input type="text" name="choices-1-votes" value="900" /></li>
<li>Order: <input type="text" name="choices-1-ORDER" value="2" /></li>
<li>Choice: <input type="text" name="choices-2-choice" /></li>
<li>Votes: <input type="text" name="choices-2-votes" /></li>
<li>Order: <input type="text" name="choices-2-ORDER" /></li>

>>> data = {
...     'choices-TOTAL_FORMS': '3', # the number of forms rendered
...     'choices-INITIAL_FORMS': '2', # the number of forms with initial data
...     'choices-0-choice': 'Calexico',
...     'choices-0-votes': '100',
...     'choices-0-ORDER': '1',
...     'choices-1-choice': 'Fergie',
...     'choices-1-votes': '900',
...     'choices-1-ORDER': '2',
...     'choices-2-choice': 'The Decemberists',
...     'choices-2-votes': '500',
...     'choices-2-ORDER': '0',
... }

>>> formset = ChoiceFormSet(data, auto_id=False, prefix='choices')
>>> formset.is_valid()
True
>>> for form in formset.ordered_forms:
...    print form.cleaned_data
{'votes': 500, 'ORDER': 0, 'choice': u'The Decemberists'}
{'votes': 100, 'ORDER': 1, 'choice': u'Calexico'}
{'votes': 900, 'ORDER': 2, 'choice': u'Fergie'}

Ordering fields are allowed to be left blank, and if they *are* left blank,
they will be sorted below everything else.

>>> data = {
...     'choices-TOTAL_FORMS': '4', # the number of forms rendered
...     'choices-INITIAL_FORMS': '3', # the number of forms with initial data
...     'choices-0-choice': 'Calexico',
...     'choices-0-votes': '100',
...     'choices-0-ORDER': '1',
...     'choices-1-choice': 'Fergie',
...     'choices-1-votes': '900',
...     'choices-1-ORDER': '2',
...     'choices-2-choice': 'The Decemberists',
...     'choices-2-votes': '500',
...     'choices-2-ORDER': '',
...     'choices-3-choice': 'Basia Bulat',
...     'choices-3-votes': '50',
...     'choices-3-ORDER': '',
... }

>>> formset = ChoiceFormSet(data, auto_id=False, prefix='choices')
>>> formset.is_valid()
True
>>> for form in formset.ordered_forms:
...    print form.cleaned_data
{'votes': 100, 'ORDER': 1, 'choice': u'Calexico'}
{'votes': 900, 'ORDER': 2, 'choice': u'Fergie'}
{'votes': 500, 'ORDER': None, 'choice': u'The Decemberists'}
{'votes': 50, 'ORDER': None, 'choice': u'Basia Bulat'}


# FormSets with ordering + deletion ###########################################

Let's try throwing ordering and deletion into the same form.

>>> ChoiceFormSet = formset_factory(Choice, can_order=True, can_delete=True)

>>> initial = [
...     {'choice': u'Calexico', 'votes': 100},
...     {'choice': u'Fergie', 'votes': 900},
...     {'choice': u'The Decemberists', 'votes': 500},
... ]
>>> formset = ChoiceFormSet(initial=initial, auto_id=False, prefix='choices')
>>> for form in formset.forms:
...    print form.as_ul()
<li>Choice: <input type="text" name="choices-0-choice" value="Calexico" /></li>
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
<li>Delete: <input type="checkbox" name="choices-3-DELETE" /></li>

Let's delete Fergie, and put The Decemberists ahead of Calexico.

>>> data = {
...     'choices-TOTAL_FORMS': '4', # the number of forms rendered
...     'choices-INITIAL_FORMS': '3', # the number of forms with initial data
...     'choices-0-choice': 'Calexico',
...     'choices-0-votes': '100',
...     'choices-0-ORDER': '1',
...     'choices-0-DELETE': '',
...     'choices-1-choice': 'Fergie',
...     'choices-1-votes': '900',
...     'choices-1-ORDER': '2',
...     'choices-1-DELETE': 'on',
...     'choices-2-choice': 'The Decemberists',
...     'choices-2-votes': '500',
...     'choices-2-ORDER': '0',
...     'choices-2-DELETE': '',
...     'choices-3-choice': '',
...     'choices-3-votes': '',
...     'choices-3-ORDER': '',
...     'choices-3-DELETE': '',
... }

>>> formset = ChoiceFormSet(data, auto_id=False, prefix='choices')
>>> formset.is_valid()
True
>>> for form in formset.ordered_forms:
...    print form.cleaned_data
{'votes': 500, 'DELETE': False, 'ORDER': 0, 'choice': u'The Decemberists'}
{'votes': 100, 'DELETE': False, 'ORDER': 1, 'choice': u'Calexico'}
>>> [form.cleaned_data for form in formset.deleted_forms]
[{'votes': 900, 'DELETE': True, 'ORDER': 2, 'choice': u'Fergie'}]


# FormSet clean hook ##########################################################

FormSets have a hook for doing extra validation that shouldn't be tied to any
particular form. It follows the same pattern as the clean hook on Forms.

Let's define a FormSet that takes a list of favorite drinks, but raises am
error if there are any duplicates.

>>> class FavoriteDrinkForm(Form):
...     name = CharField()
...

>>> class BaseFavoriteDrinksFormSet(BaseFormSet):
...     def clean(self):
...         seen_drinks = []
...         for drink in self.cleaned_data:
...             if drink['name'] in seen_drinks:
...                 raise ValidationError('You may only specify a drink once.')
...             seen_drinks.append(drink['name'])
...

>>> FavoriteDrinksFormSet = formset_factory(FavoriteDrinkForm,
...     formset=BaseFavoriteDrinksFormSet, extra=3)

We start out with a some duplicate data.

>>> data = {
...     'drinks-TOTAL_FORMS': '2', # the number of forms rendered
...     'drinks-INITIAL_FORMS': '0', # the number of forms with initial data
...     'drinks-0-name': 'Gin and Tonic',
...     'drinks-1-name': 'Gin and Tonic',
... }

>>> formset = FavoriteDrinksFormSet(data, prefix='drinks')
>>> formset.is_valid()
False

Any errors raised by formset.clean() are available via the
formset.non_form_errors() method.

>>> for error in formset.non_form_errors():
...     print error
You may only specify a drink once.


Make sure we didn't break the valid case.

>>> data = {
...     'drinks-TOTAL_FORMS': '2', # the number of forms rendered
...     'drinks-INITIAL_FORMS': '0', # the number of forms with initial data
...     'drinks-0-name': 'Gin and Tonic',
...     'drinks-1-name': 'Bloody Mary',
... }

>>> formset = FavoriteDrinksFormSet(data, prefix='drinks')
>>> formset.is_valid()
True
>>> for error in formset.non_form_errors():
...     print error

# Limiting the maximum number of forms ########################################

# Base case for max_num.

>>> LimitedFavoriteDrinkFormSet = formset_factory(FavoriteDrinkForm, extra=5, max_num=2)
>>> formset = LimitedFavoriteDrinkFormSet()
>>> for form in formset.forms:
...     print form
<tr><th><label for="id_form-0-name">Name:</label></th><td><input type="text" name="form-0-name" id="id_form-0-name" /></td></tr>
<tr><th><label for="id_form-1-name">Name:</label></th><td><input type="text" name="form-1-name" id="id_form-1-name" /></td></tr>

# Ensure the that max_num has no affect when extra is less than max_forms.

>>> LimitedFavoriteDrinkFormSet = formset_factory(FavoriteDrinkForm, extra=1, max_num=2)
>>> formset = LimitedFavoriteDrinkFormSet()
>>> for form in formset.forms:
...     print form
<tr><th><label for="id_form-0-name">Name:</label></th><td><input type="text" name="form-0-name" id="id_form-0-name" /></td></tr>

# max_num with initial data

# More initial forms than max_num will result in only the first max_num of
# them to be displayed with no extra forms.

>>> initial = [
...     {'name': 'Gin Tonic'},
...     {'name': 'Bloody Mary'},
...     {'name': 'Jack and Coke'},
... ]
>>> LimitedFavoriteDrinkFormSet = formset_factory(FavoriteDrinkForm, extra=1, max_num=2)
>>> formset = LimitedFavoriteDrinkFormSet(initial=initial)
>>> for form in formset.forms:
...     print form
<tr><th><label for="id_form-0-name">Name:</label></th><td><input type="text" name="form-0-name" value="Gin Tonic" id="id_form-0-name" /></td></tr>
<tr><th><label for="id_form-1-name">Name:</label></th><td><input type="text" name="form-1-name" value="Bloody Mary" id="id_form-1-name" /></td></tr>

# One form from initial and extra=3 with max_num=2 should result in the one
# initial form and one extra.

>>> initial = [
...     {'name': 'Gin Tonic'},
... ]
>>> LimitedFavoriteDrinkFormSet = formset_factory(FavoriteDrinkForm, extra=3, max_num=2)
>>> formset = LimitedFavoriteDrinkFormSet(initial=initial)
>>> for form in formset.forms:
...     print form
<tr><th><label for="id_form-0-name">Name:</label></th><td><input type="text" name="form-0-name" value="Gin Tonic" id="id_form-0-name" /></td></tr>
<tr><th><label for="id_form-1-name">Name:</label></th><td><input type="text" name="form-1-name" id="id_form-1-name" /></td></tr>


# Regression test for #6926 ##################################################

Make sure the management form has the correct prefix.

>>> formset = FavoriteDrinksFormSet()
>>> formset.management_form.prefix
'form'

>>> formset = FavoriteDrinksFormSet(data={})
>>> formset.management_form.prefix
'form'

>>> formset = FavoriteDrinksFormSet(initial={})
>>> formset.management_form.prefix
'form'

"""
