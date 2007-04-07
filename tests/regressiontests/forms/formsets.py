# -*- coding: utf-8 -*-
formset_tests = """
# Basic FormSet creation and usage ############################################

FormSet allows us to use multiple instance of the same form on 1 page. For now,
the best way to create a FormSet is by using the formset_for_form function.

>>> from django.newforms import Form, CharField, IntegerField
>>> from django.newforms.formsets import formset_for_form

>>> class Choice(Form):
...     choice = CharField()
...     votes = IntegerField()

>>> ChoiceFormSet = formset_for_form(Choice)


A FormSet constructor takes the same arguments as Form. Let's create a FormSet
for adding data. By default, it displays 1 blank form. It can display more,
but we'll look at how to do so later.

>>> formset = ChoiceFormSet(auto_id=False, prefix='choices')
>>> for form in formset.form_list:
...    print form.as_ul()
<li>Choice: <input type="text" name="choices-0-choice" /></li>
<li>Votes: <input type="text" name="choices-0-votes" /></li>

On thing to note is that there needs to be a special value in the data. This
value tells the FormSet how many forms were displayed so it can tell how
many forms it needs to clean and validate. You could use javascript to create
new forms on the client side, but they won't get validated unless you increment
the COUNT field appropriately.

>>> data = {
...     'choices-COUNT': '1', # the number of forms rendered
...     'choices-0-choice': 'Calexico',
...     'choices-0-votes': '100',
... }

We treat FormSet pretty much like we would treat a normal Form. FormSet has an
is_valid method, and a clean_data or errors attribute depending on whether all
the forms passed validation. However, unlike a Form instance, clean_data and
errors will be a list of dicts rather than just a single dict.

>>> formset = ChoiceFormSet(data, auto_id=False, prefix='choices')
>>> formset.is_valid()
True
>>> formset.clean_data
[{'votes': 100, 'choice': u'Calexico'}]


FormSet instances can also have an error attribute if validation failed for
any of the forms.

>>> data = {
...     'choices-COUNT': '1', # the number of forms rendered
...     'choices-0-choice': 'Calexico',
...     'choices-0-votes': '',
... }

>>> formset = ChoiceFormSet(data, auto_id=False, prefix='choices')
>>> formset.is_valid()
False
>>> formset.errors
[{'votes': [u'This field is required.']}]

Like a Form instance, clean_data won't exist if the formset wasn't validated.

>>> formset.clean_data
Traceback (most recent call last):
...
AttributeError: 'ChoiceFormSet' object has no attribute 'clean_data'


We can also prefill a FormSet with existing data by providing an ``initial``
argument to the constructor. ``initial`` should be a list of dicts. By default,
an extra blank form is included.

>>> initial = [{'choice': u'Calexico', 'votes': 100}]
>>> formset = ChoiceFormSet(initial=initial, auto_id=False, prefix='choices')
>>> for form in formset.form_list:
...    print form.as_ul()
<li>Choice: <input type="text" name="choices-0-choice" value="Calexico" /></li>
<li>Votes: <input type="text" name="choices-0-votes" value="100" /></li>
<li>Choice: <input type="text" name="choices-1-choice" /></li>
<li>Votes: <input type="text" name="choices-1-votes" /></li>


Let's simulate what would happen if we submitted this form.

>>> data = {
...     'choices-COUNT': '2', # the number of forms rendered
...     'choices-0-choice': 'Calexico',
...     'choices-0-votes': '100',
...     'choices-1-choice': '',
...     'choices-1-votes': '',
... }

>>> formset = ChoiceFormSet(data, auto_id=False, prefix='choices')
>>> formset.is_valid()
True
>>> formset.clean_data
[{'votes': 100, 'choice': u'Calexico'}]

But the second form was blank! Shouldn't we get some errors? No. If we display
a form as blank, it's ok for it to be submitted as blank. If we fill out even
one of the fields of a blank form though, it will be validated. We may want to
required that at least x number of forms are completed, but we'll show how to
handle that later.

>>> data = {
...     'choices-COUNT': '2', # the number of forms rendered
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
...     'choices-COUNT': '2', # the number of forms rendered
...     'choices-0-choice': '', # deleted value
...     'choices-0-votes': '', # deleted value
...     'choices-1-choice': '',
...     'choices-1-votes': '',
... }

>>> formset = ChoiceFormSet(data, auto_id=False, prefix='choices')
>>> formset.is_valid()
False
>>> formset.errors
[{'votes': [u'This field is required.'], 'choice': [u'This field is required.']}]


# Displaying more than 1 blank form ###########################################

We can also display more than 1 empty form at a time. To do so, pass a
num_extra argument to formset_for_form.

>>> ChoiceFormSet = formset_for_form(Choice, num_extra=3)

>>> formset = ChoiceFormSet(auto_id=False, prefix='choices')
>>> for form in formset.form_list:
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
...     'choices-COUNT': '3', # the number of forms rendered
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
>>> formset.clean_data
[]


We can just fill out one of the forms.

>>> data = {
...     'choices-COUNT': '3', # the number of forms rendered
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
>>> formset.clean_data
[{'votes': 100, 'choice': u'Calexico'}]


And once again, if we try to partially complete a form, validation will fail.

>>> data = {
...     'choices-COUNT': '3', # the number of forms rendered
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
[{}, {'votes': [u'This field is required.']}]


The num_extra argument also works when the formset is pre-filled with initial
data.

>>> initial = [{'choice': u'Calexico', 'votes': 100}]
>>> formset = ChoiceFormSet(initial=initial, auto_id=False, prefix='choices')
>>> for form in formset.form_list:
...    print form.as_ul()
<li>Choice: <input type="text" name="choices-0-choice" value="Calexico" /></li>
<li>Votes: <input type="text" name="choices-0-votes" value="100" /></li>
<li>Choice: <input type="text" name="choices-1-choice" /></li>
<li>Votes: <input type="text" name="choices-1-votes" /></li>
<li>Choice: <input type="text" name="choices-2-choice" /></li>
<li>Votes: <input type="text" name="choices-2-votes" /></li>
<li>Choice: <input type="text" name="choices-3-choice" /></li>
<li>Votes: <input type="text" name="choices-3-votes" /></li>


If we try to skip a form, even if it was initially displayed as blank, we will
get an error.

>>> data = {
...     'choices-COUNT': '4', # the number of forms rendered
...     'choices-0-choice': 'Calexico',
...     'choices-0-votes': '100',
...     'choices-1-choice': '',
...     'choices-1-votes': '',
...     'choices-2-choice': 'The Decemberists',
...     'choices-2-votes': '12',
...     'choices-3-choice': '',
...     'choices-3-votes': '',
... }

>>> formset = ChoiceFormSet(data, auto_id=False, prefix='choices')
>>> formset.is_valid()
False
>>> formset.errors
[{}, {'votes': [u'This field is required.'], 'choice': [u'This field is required.']}, {}]


# FormSets with deletion ######################################################

We can easily add deletion ability to a FormSet with an agrument to
formset_for_form. This will add a boolean field to each form instance. When
that boolean field is True, the cleaned data will be in formset.deleted_data
rather than formset.clean_data

>>> ChoiceFormSet = formset_for_form(Choice, deletable=True)

>>> initial = [{'choice': u'Calexico', 'votes': 100}, {'choice': u'Fergie', 'votes': 900}]
>>> formset = ChoiceFormSet(initial=initial, auto_id=False, prefix='choices')
>>> for form in formset.form_list:
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
...     'choices-COUNT': '3', # the number of forms rendered
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
>>> formset.clean_data
[{'votes': 100, 'DELETE': False, 'choice': u'Calexico'}]
>>> formset.deleted_data
[{'votes': 900, 'DELETE': True, 'choice': u'Fergie'}]

# FormSets with ordering ######################################################

We can also add ordering ability to a FormSet with an agrument to
formset_for_form. This will add a integer field to each form instance. When
form validation succeeds, formset.clean_data will have the data in the correct
order specified by the ordering fields. If a number is duplicated in the set
of ordering fields, for instance form 0 and form 3 are both marked as 1, then
the form index used as a secondary ordering criteria. In order to put
something at the front of the list, you'd need to set it's order to 0.

>>> ChoiceFormSet = formset_for_form(Choice, orderable=True)

>>> initial = [{'choice': u'Calexico', 'votes': 100}, {'choice': u'Fergie', 'votes': 900}]
>>> formset = ChoiceFormSet(initial=initial, auto_id=False, prefix='choices')
>>> for form in formset.form_list:
...    print form.as_ul()
<li>Choice: <input type="text" name="choices-0-choice" value="Calexico" /></li>
<li>Votes: <input type="text" name="choices-0-votes" value="100" /></li>
<li>Order: <input type="text" name="choices-0-ORDER" value="1" /></li>
<li>Choice: <input type="text" name="choices-1-choice" value="Fergie" /></li>
<li>Votes: <input type="text" name="choices-1-votes" value="900" /></li>
<li>Order: <input type="text" name="choices-1-ORDER" value="2" /></li>
<li>Choice: <input type="text" name="choices-2-choice" /></li>
<li>Votes: <input type="text" name="choices-2-votes" /></li>
<li>Order: <input type="text" name="choices-2-ORDER" value="3" /></li>

>>> data = {
...     'choices-COUNT': '3', # the number of forms rendered
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
>>> for clean_data in formset.clean_data:
...    print clean_data
{'votes': 500, 'ORDER': 0, 'choice': u'The Decemberists'}
{'votes': 100, 'ORDER': 1, 'choice': u'Calexico'}
{'votes': 900, 'ORDER': 2, 'choice': u'Fergie'}

# FormSets with ordering + deletion ###########################################

Let's try throwing ordering and deletion into the same form.

>>> ChoiceFormSet = formset_for_form(Choice, orderable=True, deletable=True)

>>> initial = [
...     {'choice': u'Calexico', 'votes': 100},
...     {'choice': u'Fergie', 'votes': 900},
...     {'choice': u'The Decemberists', 'votes': 500},
... ]
>>> formset = ChoiceFormSet(initial=initial, auto_id=False, prefix='choices')
>>> for form in formset.form_list:
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
<li>Order: <input type="text" name="choices-3-ORDER" value="4" /></li>
<li>Delete: <input type="checkbox" name="choices-3-DELETE" /></li>

Let's delete Fergie, and put The Decemberists ahead of Calexico.

>>> data = {
...     'choices-COUNT': '4', # the number of forms rendered
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
...     'choices-3-ORDER': '4',
...     'choices-3-DELETE': '',
... }

>>> formset = ChoiceFormSet(data, auto_id=False, prefix='choices')
>>> formset.is_valid()
True
>>> for clean_data in formset.clean_data:
...    print clean_data
{'votes': 500, 'DELETE': False, 'ORDER': 0, 'choice': u'The Decemberists'}
{'votes': 100, 'DELETE': False, 'ORDER': 1, 'choice': u'Calexico'}
>>> formset.deleted_data
[{'votes': 900, 'DELETE': True, 'ORDER': 2, 'choice': u'Fergie'}]


"""
