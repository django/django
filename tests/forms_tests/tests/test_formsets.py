import datetime
from collections import Counter
from unittest import mock

from django.core.exceptions import ValidationError
from django.forms import (
    BaseForm,
    CharField,
    DateField,
    FileField,
    Form,
    IntegerField,
    SplitDateTimeField,
    formsets,
)
from django.forms.formsets import (
    INITIAL_FORM_COUNT,
    MAX_NUM_FORM_COUNT,
    MIN_NUM_FORM_COUNT,
    TOTAL_FORM_COUNT,
    BaseFormSet,
    ManagementForm,
    all_valid,
    formset_factory,
)
from django.forms.renderers import TemplatesSetting
from django.forms.utils import ErrorList
from django.forms.widgets import HiddenInput
from django.test import SimpleTestCase

from . import jinja2_tests


class Choice(Form):
    choice = CharField()
    votes = IntegerField()


ChoiceFormSet = formset_factory(Choice)


class ChoiceFormsetWithNonFormError(ChoiceFormSet):
    def clean(self):
        super().clean()
        raise ValidationError("non-form error")


class FavoriteDrinkForm(Form):
    name = CharField()


class BaseFavoriteDrinksFormSet(BaseFormSet):
    def clean(self):
        seen_drinks = []

        for drink in self.cleaned_data:
            if drink["name"] in seen_drinks:
                raise ValidationError("You may only specify a drink once.")

            seen_drinks.append(drink["name"])


# A FormSet that takes a list of favorite drinks and raises an error if
# there are any duplicates.
FavoriteDrinksFormSet = formset_factory(
    FavoriteDrinkForm, formset=BaseFavoriteDrinksFormSet, extra=3
)


class CustomKwargForm(Form):
    def __init__(self, *args, custom_kwarg, **kwargs):
        self.custom_kwarg = custom_kwarg
        super().__init__(*args, **kwargs)


class FormsFormsetTestCase(SimpleTestCase):
    def make_choiceformset(
        self,
        formset_data=None,
        formset_class=ChoiceFormSet,
        total_forms=None,
        initial_forms=0,
        max_num_forms=0,
        min_num_forms=0,
        **kwargs,
    ):
        """
        Make a ChoiceFormset from the given formset_data.
        The data should be given as a list of (choice, votes) tuples.
        """
        kwargs.setdefault("prefix", "choices")
        kwargs.setdefault("auto_id", False)

        if formset_data is None:
            return formset_class(**kwargs)

        if total_forms is None:
            total_forms = len(formset_data)

        def prefixed(*args):
            args = (kwargs["prefix"],) + args
            return "-".join(args)

        data = {
            prefixed("TOTAL_FORMS"): str(total_forms),
            prefixed("INITIAL_FORMS"): str(initial_forms),
            prefixed("MAX_NUM_FORMS"): str(max_num_forms),
            prefixed("MIN_NUM_FORMS"): str(min_num_forms),
        }
        for i, (choice, votes) in enumerate(formset_data):
            data[prefixed(str(i), "choice")] = choice
            data[prefixed(str(i), "votes")] = votes

        return formset_class(data, **kwargs)

    def test_basic_formset(self):
        """
        A FormSet constructor takes the same arguments as Form. Create a
        FormSet for adding data. By default, it displays 1 blank form.
        """
        formset = self.make_choiceformset()
        self.assertHTMLEqual(
            str(formset),
            """<input type="hidden" name="choices-TOTAL_FORMS" value="1">
<input type="hidden" name="choices-INITIAL_FORMS" value="0">
<input type="hidden" name="choices-MIN_NUM_FORMS" value="0">
<input type="hidden" name="choices-MAX_NUM_FORMS" value="1000">
<div>Choice:<input type="text" name="choices-0-choice"></div>
<div>Votes:<input type="number" name="choices-0-votes"></div>""",
        )
        # FormSet are treated similarly to Forms. FormSet has an is_valid()
        # method, and a cleaned_data or errors attribute depending on whether
        # all the forms passed validation. However, unlike a Form, cleaned_data
        # and errors will be a list of dicts rather than a single dict.
        formset = self.make_choiceformset([("Calexico", "100")])
        self.assertTrue(formset.is_valid())
        self.assertEqual(
            [form.cleaned_data for form in formset.forms],
            [{"votes": 100, "choice": "Calexico"}],
        )

        # If a FormSet wasn't passed any data, is_valid() and has_changed()
        # return False.
        formset = self.make_choiceformset()
        self.assertFalse(formset.is_valid())
        self.assertFalse(formset.has_changed())

    def test_form_kwargs_formset(self):
        """
        Custom kwargs set on the formset instance are passed to the
        underlying forms.
        """
        FormSet = formset_factory(CustomKwargForm, extra=2)
        formset = FormSet(form_kwargs={"custom_kwarg": 1})
        for form in formset:
            self.assertTrue(hasattr(form, "custom_kwarg"))
            self.assertEqual(form.custom_kwarg, 1)

    def test_form_kwargs_formset_dynamic(self):
        """Form kwargs can be passed dynamically in a formset."""

        class DynamicBaseFormSet(BaseFormSet):
            def get_form_kwargs(self, index):
                return {"custom_kwarg": index}

        DynamicFormSet = formset_factory(
            CustomKwargForm, formset=DynamicBaseFormSet, extra=2
        )
        formset = DynamicFormSet(form_kwargs={"custom_kwarg": "ignored"})
        for i, form in enumerate(formset):
            self.assertTrue(hasattr(form, "custom_kwarg"))
            self.assertEqual(form.custom_kwarg, i)

    def test_form_kwargs_empty_form(self):
        FormSet = formset_factory(CustomKwargForm)
        formset = FormSet(form_kwargs={"custom_kwarg": 1})
        self.assertTrue(hasattr(formset.empty_form, "custom_kwarg"))
        self.assertEqual(formset.empty_form.custom_kwarg, 1)

    def test_empty_permitted_ignored_empty_form(self):
        formset = ArticleFormSet(form_kwargs={"empty_permitted": False})
        self.assertIs(formset.empty_form.empty_permitted, True)

    def test_formset_validation(self):
        # FormSet instances can also have an error attribute if validation failed for
        # any of the forms.
        formset = self.make_choiceformset([("Calexico", "")])
        self.assertFalse(formset.is_valid())
        self.assertEqual(formset.errors, [{"votes": ["This field is required."]}])

    def test_formset_validation_count(self):
        """
        A formset's ManagementForm is validated once per FormSet.is_valid()
        call and each form of the formset is cleaned once.
        """

        def make_method_counter(func):
            """Add a counter to func for the number of times it's called."""
            counter = Counter()
            counter.call_count = 0

            def mocked_func(*args, **kwargs):
                counter.call_count += 1
                return func(*args, **kwargs)

            return mocked_func, counter

        mocked_is_valid, is_valid_counter = make_method_counter(
            formsets.ManagementForm.is_valid
        )
        mocked_full_clean, full_clean_counter = make_method_counter(BaseForm.full_clean)
        formset = self.make_choiceformset(
            [("Calexico", "100"), ("Any1", "42"), ("Any2", "101")]
        )

        with mock.patch(
            "django.forms.formsets.ManagementForm.is_valid", mocked_is_valid
        ), mock.patch("django.forms.forms.BaseForm.full_clean", mocked_full_clean):
            self.assertTrue(formset.is_valid())
        self.assertEqual(is_valid_counter.call_count, 1)
        self.assertEqual(full_clean_counter.call_count, 4)

    def test_formset_has_changed(self):
        """
        FormSet.has_changed() is True if any data is passed to its forms, even
        if the formset didn't validate.
        """
        blank_formset = self.make_choiceformset([("", "")])
        self.assertFalse(blank_formset.has_changed())
        # invalid formset
        invalid_formset = self.make_choiceformset([("Calexico", "")])
        self.assertFalse(invalid_formset.is_valid())
        self.assertTrue(invalid_formset.has_changed())
        # valid formset
        valid_formset = self.make_choiceformset([("Calexico", "100")])
        self.assertTrue(valid_formset.is_valid())
        self.assertTrue(valid_formset.has_changed())

    def test_formset_initial_data(self):
        """
        A FormSet can be prefilled with existing data by providing a list of
        dicts to the `initial` argument. By default, an extra blank form is
        included.
        """
        formset = self.make_choiceformset(
            initial=[{"choice": "Calexico", "votes": 100}]
        )
        self.assertHTMLEqual(
            "\n".join(form.as_ul() for form in formset.forms),
            '<li>Choice: <input type="text" name="choices-0-choice" value="Calexico">'
            "</li>"
            '<li>Votes: <input type="number" name="choices-0-votes" value="100"></li>'
            '<li>Choice: <input type="text" name="choices-1-choice"></li>'
            '<li>Votes: <input type="number" name="choices-1-votes"></li>',
        )

    def test_blank_form_unfilled(self):
        """A form that's displayed as blank may be submitted as blank."""
        formset = self.make_choiceformset(
            [("Calexico", "100"), ("", "")], initial_forms=1
        )
        self.assertTrue(formset.is_valid())
        self.assertEqual(
            [form.cleaned_data for form in formset.forms],
            [{"votes": 100, "choice": "Calexico"}, {}],
        )

    def test_second_form_partially_filled(self):
        """
        If at least one field is filled out on a blank form, it will be
        validated.
        """
        formset = self.make_choiceformset(
            [("Calexico", "100"), ("The Decemberists", "")], initial_forms=1
        )
        self.assertFalse(formset.is_valid())
        self.assertEqual(formset.errors, [{}, {"votes": ["This field is required."]}])

    def test_delete_prefilled_data(self):
        """
        Deleting prefilled data is an error. Removing data from form fields
        isn't the proper way to delete it.
        """
        formset = self.make_choiceformset([("", ""), ("", "")], initial_forms=1)
        self.assertFalse(formset.is_valid())
        self.assertEqual(
            formset.errors,
            [
                {
                    "votes": ["This field is required."],
                    "choice": ["This field is required."],
                },
                {},
            ],
        )

    def test_displaying_more_than_one_blank_form(self):
        """
        More than 1 empty form can be displayed using formset_factory's
        `extra` argument.
        """
        ChoiceFormSet = formset_factory(Choice, extra=3)
        formset = ChoiceFormSet(auto_id=False, prefix="choices")
        self.assertHTMLEqual(
            "\n".join(form.as_ul() for form in formset.forms),
            """<li>Choice: <input type="text" name="choices-0-choice"></li>
<li>Votes: <input type="number" name="choices-0-votes"></li>
<li>Choice: <input type="text" name="choices-1-choice"></li>
<li>Votes: <input type="number" name="choices-1-votes"></li>
<li>Choice: <input type="text" name="choices-2-choice"></li>
<li>Votes: <input type="number" name="choices-2-votes"></li>""",
        )
        # Since every form was displayed as blank, they are also accepted as
        # blank. This may seem a little strange, but min_num is used to require
        # a minimum number of forms to be completed.
        data = {
            "choices-TOTAL_FORMS": "3",  # the number of forms rendered
            "choices-INITIAL_FORMS": "0",  # the number of forms with initial data
            "choices-MIN_NUM_FORMS": "0",  # min number of forms
            "choices-MAX_NUM_FORMS": "0",  # max number of forms
            "choices-0-choice": "",
            "choices-0-votes": "",
            "choices-1-choice": "",
            "choices-1-votes": "",
            "choices-2-choice": "",
            "choices-2-votes": "",
        }
        formset = ChoiceFormSet(data, auto_id=False, prefix="choices")
        self.assertTrue(formset.is_valid())
        self.assertEqual([form.cleaned_data for form in formset.forms], [{}, {}, {}])

    def test_min_num_displaying_more_than_one_blank_form(self):
        """
        More than 1 empty form can also be displayed using formset_factory's
        min_num argument. It will (essentially) increment the extra argument.
        """
        ChoiceFormSet = formset_factory(Choice, extra=1, min_num=1)
        formset = ChoiceFormSet(auto_id=False, prefix="choices")
        # Min_num forms are required; extra forms can be empty.
        self.assertFalse(formset.forms[0].empty_permitted)
        self.assertTrue(formset.forms[1].empty_permitted)
        self.assertHTMLEqual(
            "\n".join(form.as_ul() for form in formset.forms),
            """<li>Choice: <input type="text" name="choices-0-choice"></li>
<li>Votes: <input type="number" name="choices-0-votes"></li>
<li>Choice: <input type="text" name="choices-1-choice"></li>
<li>Votes: <input type="number" name="choices-1-votes"></li>""",
        )

    def test_min_num_displaying_more_than_one_blank_form_with_zero_extra(self):
        """More than 1 empty form can be displayed using min_num."""
        ChoiceFormSet = formset_factory(Choice, extra=0, min_num=3)
        formset = ChoiceFormSet(auto_id=False, prefix="choices")
        self.assertHTMLEqual(
            "\n".join(form.as_ul() for form in formset.forms),
            """<li>Choice: <input type="text" name="choices-0-choice"></li>
<li>Votes: <input type="number" name="choices-0-votes"></li>
<li>Choice: <input type="text" name="choices-1-choice"></li>
<li>Votes: <input type="number" name="choices-1-votes"></li>
<li>Choice: <input type="text" name="choices-2-choice"></li>
<li>Votes: <input type="number" name="choices-2-votes"></li>""",
        )

    def test_single_form_completed(self):
        """Just one form may be completed."""
        data = {
            "choices-TOTAL_FORMS": "3",  # the number of forms rendered
            "choices-INITIAL_FORMS": "0",  # the number of forms with initial data
            "choices-MIN_NUM_FORMS": "0",  # min number of forms
            "choices-MAX_NUM_FORMS": "0",  # max number of forms
            "choices-0-choice": "Calexico",
            "choices-0-votes": "100",
            "choices-1-choice": "",
            "choices-1-votes": "",
            "choices-2-choice": "",
            "choices-2-votes": "",
        }
        ChoiceFormSet = formset_factory(Choice, extra=3)
        formset = ChoiceFormSet(data, auto_id=False, prefix="choices")
        self.assertTrue(formset.is_valid())
        self.assertEqual(
            [form.cleaned_data for form in formset.forms],
            [{"votes": 100, "choice": "Calexico"}, {}, {}],
        )

    def test_formset_validate_max_flag(self):
        """
        If validate_max is set and max_num is less than TOTAL_FORMS in the
        data, a ValidationError is raised. MAX_NUM_FORMS in the data is
        irrelevant here (it's output as a hint for the client but its value
        in the returned data is not checked).
        """
        data = {
            "choices-TOTAL_FORMS": "2",  # the number of forms rendered
            "choices-INITIAL_FORMS": "0",  # the number of forms with initial data
            "choices-MIN_NUM_FORMS": "0",  # min number of forms
            "choices-MAX_NUM_FORMS": "2",  # max number of forms - should be ignored
            "choices-0-choice": "Zero",
            "choices-0-votes": "0",
            "choices-1-choice": "One",
            "choices-1-votes": "1",
        }
        ChoiceFormSet = formset_factory(Choice, extra=1, max_num=1, validate_max=True)
        formset = ChoiceFormSet(data, auto_id=False, prefix="choices")
        self.assertFalse(formset.is_valid())
        self.assertEqual(formset.non_form_errors(), ["Please submit at most 1 form."])
        self.assertEqual(
            str(formset.non_form_errors()),
            '<ul class="errorlist nonform"><li>Please submit at most 1 form.</li></ul>',
        )

    def test_formset_validate_max_flag_custom_error(self):
        data = {
            "choices-TOTAL_FORMS": "2",
            "choices-INITIAL_FORMS": "0",
            "choices-MIN_NUM_FORMS": "0",
            "choices-MAX_NUM_FORMS": "2",
            "choices-0-choice": "Zero",
            "choices-0-votes": "0",
            "choices-1-choice": "One",
            "choices-1-votes": "1",
        }
        ChoiceFormSet = formset_factory(Choice, extra=1, max_num=1, validate_max=True)
        formset = ChoiceFormSet(
            data,
            auto_id=False,
            prefix="choices",
            error_messages={
                "too_many_forms": "Number of submitted forms should be at most %(num)d."
            },
        )
        self.assertFalse(formset.is_valid())
        self.assertEqual(
            formset.non_form_errors(),
            ["Number of submitted forms should be at most 1."],
        )
        self.assertEqual(
            str(formset.non_form_errors()),
            '<ul class="errorlist nonform">'
            "<li>Number of submitted forms should be at most 1.</li></ul>",
        )

    def test_formset_validate_min_flag(self):
        """
        If validate_min is set and min_num is more than TOTAL_FORMS in the
        data, a ValidationError is raised. MIN_NUM_FORMS in the data is
        irrelevant here (it's output as a hint for the client but its value
        in the returned data is not checked).
        """
        data = {
            "choices-TOTAL_FORMS": "2",  # the number of forms rendered
            "choices-INITIAL_FORMS": "0",  # the number of forms with initial data
            "choices-MIN_NUM_FORMS": "0",  # min number of forms
            "choices-MAX_NUM_FORMS": "0",  # max number of forms - should be ignored
            "choices-0-choice": "Zero",
            "choices-0-votes": "0",
            "choices-1-choice": "One",
            "choices-1-votes": "1",
        }
        ChoiceFormSet = formset_factory(Choice, extra=1, min_num=3, validate_min=True)
        formset = ChoiceFormSet(data, auto_id=False, prefix="choices")
        self.assertFalse(formset.is_valid())
        self.assertEqual(formset.non_form_errors(), ["Please submit at least 3 forms."])
        self.assertEqual(
            str(formset.non_form_errors()),
            '<ul class="errorlist nonform"><li>'
            "Please submit at least 3 forms.</li></ul>",
        )

    def test_formset_validate_min_flag_custom_formatted_error(self):
        data = {
            "choices-TOTAL_FORMS": "2",
            "choices-INITIAL_FORMS": "0",
            "choices-MIN_NUM_FORMS": "0",
            "choices-MAX_NUM_FORMS": "0",
            "choices-0-choice": "Zero",
            "choices-0-votes": "0",
            "choices-1-choice": "One",
            "choices-1-votes": "1",
        }
        ChoiceFormSet = formset_factory(Choice, extra=1, min_num=3, validate_min=True)
        formset = ChoiceFormSet(
            data,
            auto_id=False,
            prefix="choices",
            error_messages={
                "too_few_forms": "Number of submitted forms should be at least %(num)d."
            },
        )
        self.assertFalse(formset.is_valid())
        self.assertEqual(
            formset.non_form_errors(),
            ["Number of submitted forms should be at least 3."],
        )
        self.assertEqual(
            str(formset.non_form_errors()),
            '<ul class="errorlist nonform">'
            "<li>Number of submitted forms should be at least 3.</li></ul>",
        )

    def test_formset_validate_min_unchanged_forms(self):
        """
        min_num validation doesn't consider unchanged forms with initial data
        as "empty".
        """
        initial = [
            {"choice": "Zero", "votes": 0},
            {"choice": "One", "votes": 0},
        ]
        data = {
            "choices-TOTAL_FORMS": "2",
            "choices-INITIAL_FORMS": "2",
            "choices-MIN_NUM_FORMS": "0",
            "choices-MAX_NUM_FORMS": "2",
            "choices-0-choice": "Zero",
            "choices-0-votes": "0",
            "choices-1-choice": "One",
            "choices-1-votes": "1",  # changed from initial
        }
        ChoiceFormSet = formset_factory(Choice, min_num=2, validate_min=True)
        formset = ChoiceFormSet(data, auto_id=False, prefix="choices", initial=initial)
        self.assertFalse(formset.forms[0].has_changed())
        self.assertTrue(formset.forms[1].has_changed())
        self.assertTrue(formset.is_valid())

    def test_formset_validate_min_excludes_empty_forms(self):
        data = {
            "choices-TOTAL_FORMS": "2",
            "choices-INITIAL_FORMS": "0",
        }
        ChoiceFormSet = formset_factory(
            Choice, extra=2, min_num=1, validate_min=True, can_delete=True
        )
        formset = ChoiceFormSet(data, prefix="choices")
        self.assertFalse(formset.has_changed())
        self.assertFalse(formset.is_valid())
        self.assertEqual(formset.non_form_errors(), ["Please submit at least 1 form."])

    def test_second_form_partially_filled_2(self):
        """A partially completed form is invalid."""
        data = {
            "choices-TOTAL_FORMS": "3",  # the number of forms rendered
            "choices-INITIAL_FORMS": "0",  # the number of forms with initial data
            "choices-MIN_NUM_FORMS": "0",  # min number of forms
            "choices-MAX_NUM_FORMS": "0",  # max number of forms
            "choices-0-choice": "Calexico",
            "choices-0-votes": "100",
            "choices-1-choice": "The Decemberists",
            "choices-1-votes": "",  # missing value
            "choices-2-choice": "",
            "choices-2-votes": "",
        }
        ChoiceFormSet = formset_factory(Choice, extra=3)
        formset = ChoiceFormSet(data, auto_id=False, prefix="choices")
        self.assertFalse(formset.is_valid())
        self.assertEqual(
            formset.errors, [{}, {"votes": ["This field is required."]}, {}]
        )

    def test_more_initial_data(self):
        """
        The extra argument works when the formset is pre-filled with initial
        data.
        """
        initial = [{"choice": "Calexico", "votes": 100}]
        ChoiceFormSet = formset_factory(Choice, extra=3)
        formset = ChoiceFormSet(initial=initial, auto_id=False, prefix="choices")
        self.assertHTMLEqual(
            "\n".join(form.as_ul() for form in formset.forms),
            '<li>Choice: <input type="text" name="choices-0-choice" value="Calexico">'
            "</li>"
            '<li>Votes: <input type="number" name="choices-0-votes" value="100"></li>'
            '<li>Choice: <input type="text" name="choices-1-choice"></li>'
            '<li>Votes: <input type="number" name="choices-1-votes"></li>'
            '<li>Choice: <input type="text" name="choices-2-choice"></li>'
            '<li>Votes: <input type="number" name="choices-2-votes"></li>'
            '<li>Choice: <input type="text" name="choices-3-choice"></li>'
            '<li>Votes: <input type="number" name="choices-3-votes"></li>',
        )
        # Retrieving an empty form works. Tt shows up in the form list.
        self.assertTrue(formset.empty_form.empty_permitted)
        self.assertHTMLEqual(
            formset.empty_form.as_ul(),
            """<li>Choice: <input type="text" name="choices-__prefix__-choice"></li>
<li>Votes: <input type="number" name="choices-__prefix__-votes"></li>""",
        )

    def test_formset_with_deletion(self):
        """
        formset_factory's can_delete argument adds a boolean "delete" field to
        each form. When that boolean field is True, the form will be in
        formset.deleted_forms.
        """
        ChoiceFormSet = formset_factory(Choice, can_delete=True)
        initial = [
            {"choice": "Calexico", "votes": 100},
            {"choice": "Fergie", "votes": 900},
        ]
        formset = ChoiceFormSet(initial=initial, auto_id=False, prefix="choices")
        self.assertHTMLEqual(
            "\n".join(form.as_ul() for form in formset.forms),
            '<li>Choice: <input type="text" name="choices-0-choice" value="Calexico">'
            "</li>"
            '<li>Votes: <input type="number" name="choices-0-votes" value="100"></li>'
            '<li>Delete: <input type="checkbox" name="choices-0-DELETE"></li>'
            '<li>Choice: <input type="text" name="choices-1-choice" value="Fergie">'
            "</li>"
            '<li>Votes: <input type="number" name="choices-1-votes" value="900"></li>'
            '<li>Delete: <input type="checkbox" name="choices-1-DELETE"></li>'
            '<li>Choice: <input type="text" name="choices-2-choice"></li>'
            '<li>Votes: <input type="number" name="choices-2-votes"></li>'
            '<li>Delete: <input type="checkbox" name="choices-2-DELETE"></li>',
        )
        # To delete something, set that form's special delete field to 'on'.
        # Let's go ahead and delete Fergie.
        data = {
            "choices-TOTAL_FORMS": "3",  # the number of forms rendered
            "choices-INITIAL_FORMS": "2",  # the number of forms with initial data
            "choices-MIN_NUM_FORMS": "0",  # min number of forms
            "choices-MAX_NUM_FORMS": "0",  # max number of forms
            "choices-0-choice": "Calexico",
            "choices-0-votes": "100",
            "choices-0-DELETE": "",
            "choices-1-choice": "Fergie",
            "choices-1-votes": "900",
            "choices-1-DELETE": "on",
            "choices-2-choice": "",
            "choices-2-votes": "",
            "choices-2-DELETE": "",
        }
        formset = ChoiceFormSet(data, auto_id=False, prefix="choices")
        self.assertTrue(formset.is_valid())
        self.assertEqual(
            [form.cleaned_data for form in formset.forms],
            [
                {"votes": 100, "DELETE": False, "choice": "Calexico"},
                {"votes": 900, "DELETE": True, "choice": "Fergie"},
                {},
            ],
        )
        self.assertEqual(
            [form.cleaned_data for form in formset.deleted_forms],
            [{"votes": 900, "DELETE": True, "choice": "Fergie"}],
        )

    def test_formset_with_deletion_remove_deletion_flag(self):
        """
        If a form is filled with something and can_delete is also checked, that
        form's errors shouldn't make the entire formset invalid since it's
        going to be deleted.
        """

        class CheckForm(Form):
            field = IntegerField(min_value=100)

        data = {
            "check-TOTAL_FORMS": "3",  # the number of forms rendered
            "check-INITIAL_FORMS": "2",  # the number of forms with initial data
            "choices-MIN_NUM_FORMS": "0",  # min number of forms
            "check-MAX_NUM_FORMS": "0",  # max number of forms
            "check-0-field": "200",
            "check-0-DELETE": "",
            "check-1-field": "50",
            "check-1-DELETE": "on",
            "check-2-field": "",
            "check-2-DELETE": "",
        }
        CheckFormSet = formset_factory(CheckForm, can_delete=True)
        formset = CheckFormSet(data, prefix="check")
        self.assertTrue(formset.is_valid())
        # If the deletion flag is removed, validation is enabled.
        data["check-1-DELETE"] = ""
        formset = CheckFormSet(data, prefix="check")
        self.assertFalse(formset.is_valid())

    def test_formset_with_deletion_invalid_deleted_form(self):
        """
        deleted_forms works on a valid formset even if a deleted form would
        have been invalid.
        """
        FavoriteDrinkFormset = formset_factory(form=FavoriteDrinkForm, can_delete=True)
        formset = FavoriteDrinkFormset(
            {
                "form-0-name": "",
                "form-0-DELETE": "on",  # no name!
                "form-TOTAL_FORMS": 1,
                "form-INITIAL_FORMS": 1,
                "form-MIN_NUM_FORMS": 0,
                "form-MAX_NUM_FORMS": 1,
            }
        )
        self.assertTrue(formset.is_valid())
        self.assertEqual(formset._errors, [])
        self.assertEqual(len(formset.deleted_forms), 1)

    def test_formset_with_deletion_custom_widget(self):
        class DeletionAttributeFormSet(BaseFormSet):
            deletion_widget = HiddenInput

        class DeletionMethodFormSet(BaseFormSet):
            def get_deletion_widget(self):
                return HiddenInput(attrs={"class": "deletion"})

        tests = [
            (DeletionAttributeFormSet, '<input type="hidden" name="form-0-DELETE">'),
            (
                DeletionMethodFormSet,
                '<input class="deletion" type="hidden" name="form-0-DELETE">',
            ),
        ]
        for formset_class, delete_html in tests:
            with self.subTest(formset_class=formset_class.__name__):
                ArticleFormSet = formset_factory(
                    ArticleForm,
                    formset=formset_class,
                    can_delete=True,
                )
                formset = ArticleFormSet(auto_id=False)
                self.assertHTMLEqual(
                    "\n".join([form.as_ul() for form in formset.forms]),
                    (
                        f'<li>Title: <input type="text" name="form-0-title"></li>'
                        f'<li>Pub date: <input type="text" name="form-0-pub_date">'
                        f"{delete_html}</li>"
                    ),
                )

    def test_formsets_with_ordering(self):
        """
        formset_factory's can_order argument adds an integer field to each
        form. When form validation succeeds,
            [form.cleaned_data for form in formset.forms]
        will have the data in the correct order specified by the ordering
        fields. If a number is duplicated in the set of ordering fields, for
        instance form 0 and form 3 are both marked as 1, then the form index
        used as a secondary ordering criteria. In order to put something at the
        front of the list, you'd need to set its order to 0.
        """
        ChoiceFormSet = formset_factory(Choice, can_order=True)
        initial = [
            {"choice": "Calexico", "votes": 100},
            {"choice": "Fergie", "votes": 900},
        ]
        formset = ChoiceFormSet(initial=initial, auto_id=False, prefix="choices")
        self.assertHTMLEqual(
            "\n".join(form.as_ul() for form in formset.forms),
            '<li>Choice: <input type="text" name="choices-0-choice" value="Calexico">'
            "</li>"
            '<li>Votes: <input type="number" name="choices-0-votes" value="100"></li>'
            '<li>Order: <input type="number" name="choices-0-ORDER" value="1"></li>'
            '<li>Choice: <input type="text" name="choices-1-choice" value="Fergie">'
            "</li>"
            '<li>Votes: <input type="number" name="choices-1-votes" value="900"></li>'
            '<li>Order: <input type="number" name="choices-1-ORDER" value="2"></li>'
            '<li>Choice: <input type="text" name="choices-2-choice"></li>'
            '<li>Votes: <input type="number" name="choices-2-votes"></li>'
            '<li>Order: <input type="number" name="choices-2-ORDER"></li>',
        )
        data = {
            "choices-TOTAL_FORMS": "3",  # the number of forms rendered
            "choices-INITIAL_FORMS": "2",  # the number of forms with initial data
            "choices-MIN_NUM_FORMS": "0",  # min number of forms
            "choices-MAX_NUM_FORMS": "0",  # max number of forms
            "choices-0-choice": "Calexico",
            "choices-0-votes": "100",
            "choices-0-ORDER": "1",
            "choices-1-choice": "Fergie",
            "choices-1-votes": "900",
            "choices-1-ORDER": "2",
            "choices-2-choice": "The Decemberists",
            "choices-2-votes": "500",
            "choices-2-ORDER": "0",
        }
        formset = ChoiceFormSet(data, auto_id=False, prefix="choices")
        self.assertTrue(formset.is_valid())
        self.assertEqual(
            [form.cleaned_data for form in formset.ordered_forms],
            [
                {"votes": 500, "ORDER": 0, "choice": "The Decemberists"},
                {"votes": 100, "ORDER": 1, "choice": "Calexico"},
                {"votes": 900, "ORDER": 2, "choice": "Fergie"},
            ],
        )

    def test_formsets_with_ordering_custom_widget(self):
        class OrderingAttributeFormSet(BaseFormSet):
            ordering_widget = HiddenInput

        class OrderingMethodFormSet(BaseFormSet):
            def get_ordering_widget(self):
                return HiddenInput(attrs={"class": "ordering"})

        tests = (
            (OrderingAttributeFormSet, '<input type="hidden" name="form-0-ORDER">'),
            (
                OrderingMethodFormSet,
                '<input class="ordering" type="hidden" name="form-0-ORDER">',
            ),
        )
        for formset_class, order_html in tests:
            with self.subTest(formset_class=formset_class.__name__):
                ArticleFormSet = formset_factory(
                    ArticleForm, formset=formset_class, can_order=True
                )
                formset = ArticleFormSet(auto_id=False)
                self.assertHTMLEqual(
                    "\n".join(form.as_ul() for form in formset.forms),
                    (
                        '<li>Title: <input type="text" name="form-0-title"></li>'
                        '<li>Pub date: <input type="text" name="form-0-pub_date">'
                        "%s</li>" % order_html
                    ),
                )

    def test_empty_ordered_fields(self):
        """
        Ordering fields are allowed to be left blank. If they are left blank,
        they'll be sorted below everything else.
        """
        data = {
            "choices-TOTAL_FORMS": "4",  # the number of forms rendered
            "choices-INITIAL_FORMS": "3",  # the number of forms with initial data
            "choices-MIN_NUM_FORMS": "0",  # min number of forms
            "choices-MAX_NUM_FORMS": "0",  # max number of forms
            "choices-0-choice": "Calexico",
            "choices-0-votes": "100",
            "choices-0-ORDER": "1",
            "choices-1-choice": "Fergie",
            "choices-1-votes": "900",
            "choices-1-ORDER": "2",
            "choices-2-choice": "The Decemberists",
            "choices-2-votes": "500",
            "choices-2-ORDER": "",
            "choices-3-choice": "Basia Bulat",
            "choices-3-votes": "50",
            "choices-3-ORDER": "",
        }
        ChoiceFormSet = formset_factory(Choice, can_order=True)
        formset = ChoiceFormSet(data, auto_id=False, prefix="choices")
        self.assertTrue(formset.is_valid())
        self.assertEqual(
            [form.cleaned_data for form in formset.ordered_forms],
            [
                {"votes": 100, "ORDER": 1, "choice": "Calexico"},
                {"votes": 900, "ORDER": 2, "choice": "Fergie"},
                {"votes": 500, "ORDER": None, "choice": "The Decemberists"},
                {"votes": 50, "ORDER": None, "choice": "Basia Bulat"},
            ],
        )

    def test_ordering_blank_fieldsets(self):
        """Ordering works with blank fieldsets."""
        data = {
            "choices-TOTAL_FORMS": "3",  # the number of forms rendered
            "choices-INITIAL_FORMS": "0",  # the number of forms with initial data
            "choices-MIN_NUM_FORMS": "0",  # min number of forms
            "choices-MAX_NUM_FORMS": "0",  # max number of forms
        }
        ChoiceFormSet = formset_factory(Choice, can_order=True)
        formset = ChoiceFormSet(data, auto_id=False, prefix="choices")
        self.assertTrue(formset.is_valid())
        self.assertEqual(formset.ordered_forms, [])

    def test_formset_with_ordering_and_deletion(self):
        """FormSets with ordering + deletion."""
        ChoiceFormSet = formset_factory(Choice, can_order=True, can_delete=True)
        initial = [
            {"choice": "Calexico", "votes": 100},
            {"choice": "Fergie", "votes": 900},
            {"choice": "The Decemberists", "votes": 500},
        ]
        formset = ChoiceFormSet(initial=initial, auto_id=False, prefix="choices")
        self.assertHTMLEqual(
            "\n".join(form.as_ul() for form in formset.forms),
            '<li>Choice: <input type="text" name="choices-0-choice" value="Calexico">'
            "</li>"
            '<li>Votes: <input type="number" name="choices-0-votes" value="100"></li>'
            '<li>Order: <input type="number" name="choices-0-ORDER" value="1"></li>'
            '<li>Delete: <input type="checkbox" name="choices-0-DELETE"></li>'
            '<li>Choice: <input type="text" name="choices-1-choice" value="Fergie">'
            "</li>"
            '<li>Votes: <input type="number" name="choices-1-votes" value="900"></li>'
            '<li>Order: <input type="number" name="choices-1-ORDER" value="2"></li>'
            '<li>Delete: <input type="checkbox" name="choices-1-DELETE"></li>'
            '<li>Choice: <input type="text" name="choices-2-choice" '
            'value="The Decemberists"></li>'
            '<li>Votes: <input type="number" name="choices-2-votes" value="500"></li>'
            '<li>Order: <input type="number" name="choices-2-ORDER" value="3"></li>'
            '<li>Delete: <input type="checkbox" name="choices-2-DELETE"></li>'
            '<li>Choice: <input type="text" name="choices-3-choice"></li>'
            '<li>Votes: <input type="number" name="choices-3-votes"></li>'
            '<li>Order: <input type="number" name="choices-3-ORDER"></li>'
            '<li>Delete: <input type="checkbox" name="choices-3-DELETE"></li>',
        )
        # Let's delete Fergie, and put The Decemberists ahead of Calexico.
        data = {
            "choices-TOTAL_FORMS": "4",  # the number of forms rendered
            "choices-INITIAL_FORMS": "3",  # the number of forms with initial data
            "choices-MIN_NUM_FORMS": "0",  # min number of forms
            "choices-MAX_NUM_FORMS": "0",  # max number of forms
            "choices-0-choice": "Calexico",
            "choices-0-votes": "100",
            "choices-0-ORDER": "1",
            "choices-0-DELETE": "",
            "choices-1-choice": "Fergie",
            "choices-1-votes": "900",
            "choices-1-ORDER": "2",
            "choices-1-DELETE": "on",
            "choices-2-choice": "The Decemberists",
            "choices-2-votes": "500",
            "choices-2-ORDER": "0",
            "choices-2-DELETE": "",
            "choices-3-choice": "",
            "choices-3-votes": "",
            "choices-3-ORDER": "",
            "choices-3-DELETE": "",
        }
        formset = ChoiceFormSet(data, auto_id=False, prefix="choices")
        self.assertTrue(formset.is_valid())
        self.assertEqual(
            [form.cleaned_data for form in formset.ordered_forms],
            [
                {
                    "votes": 500,
                    "DELETE": False,
                    "ORDER": 0,
                    "choice": "The Decemberists",
                },
                {"votes": 100, "DELETE": False, "ORDER": 1, "choice": "Calexico"},
            ],
        )
        self.assertEqual(
            [form.cleaned_data for form in formset.deleted_forms],
            [{"votes": 900, "DELETE": True, "ORDER": 2, "choice": "Fergie"}],
        )

    def test_invalid_deleted_form_with_ordering(self):
        """
        Can get ordered_forms from a valid formset even if a deleted form
        would have been invalid.
        """
        FavoriteDrinkFormset = formset_factory(
            form=FavoriteDrinkForm, can_delete=True, can_order=True
        )
        formset = FavoriteDrinkFormset(
            {
                "form-0-name": "",
                "form-0-DELETE": "on",  # no name!
                "form-TOTAL_FORMS": 1,
                "form-INITIAL_FORMS": 1,
                "form-MIN_NUM_FORMS": 0,
                "form-MAX_NUM_FORMS": 1,
            }
        )
        self.assertTrue(formset.is_valid())
        self.assertEqual(formset.ordered_forms, [])

    def test_clean_hook(self):
        """
        FormSets have a clean() hook for doing extra validation that isn't tied
        to any form. It follows the same pattern as the clean() hook on Forms.
        """
        # Start out with a some duplicate data.
        data = {
            "drinks-TOTAL_FORMS": "2",  # the number of forms rendered
            "drinks-INITIAL_FORMS": "0",  # the number of forms with initial data
            "drinks-MIN_NUM_FORMS": "0",  # min number of forms
            "drinks-MAX_NUM_FORMS": "0",  # max number of forms
            "drinks-0-name": "Gin and Tonic",
            "drinks-1-name": "Gin and Tonic",
        }
        formset = FavoriteDrinksFormSet(data, prefix="drinks")
        self.assertFalse(formset.is_valid())
        # Any errors raised by formset.clean() are available via the
        # formset.non_form_errors() method.
        for error in formset.non_form_errors():
            self.assertEqual(str(error), "You may only specify a drink once.")
        # The valid case still works.
        data["drinks-1-name"] = "Bloody Mary"
        formset = FavoriteDrinksFormSet(data, prefix="drinks")
        self.assertTrue(formset.is_valid())
        self.assertEqual(formset.non_form_errors(), [])

    def test_limiting_max_forms(self):
        """Limiting the maximum number of forms with max_num."""
        # When not passed, max_num will take a high default value, leaving the
        # number of forms only controlled by the value of the extra parameter.
        LimitedFavoriteDrinkFormSet = formset_factory(FavoriteDrinkForm, extra=3)
        formset = LimitedFavoriteDrinkFormSet()
        self.assertHTMLEqual(
            "\n".join(str(form) for form in formset.forms),
            """<div><label for="id_form-0-name">Name:</label>
            <input type="text" name="form-0-name" id="id_form-0-name"></div>
<div><label for="id_form-1-name">Name:</label>
<input type="text" name="form-1-name" id="id_form-1-name"></div>
<div><label for="id_form-2-name">Name:</label>
<input type="text" name="form-2-name" id="id_form-2-name"></div>""",
        )
        # If max_num is 0 then no form is rendered at all.
        LimitedFavoriteDrinkFormSet = formset_factory(
            FavoriteDrinkForm, extra=3, max_num=0
        )
        formset = LimitedFavoriteDrinkFormSet()
        self.assertEqual(formset.forms, [])

    def test_limited_max_forms_two(self):
        LimitedFavoriteDrinkFormSet = formset_factory(
            FavoriteDrinkForm, extra=5, max_num=2
        )
        formset = LimitedFavoriteDrinkFormSet()
        self.assertHTMLEqual(
            "\n".join(str(form) for form in formset.forms),
            """<div><label for="id_form-0-name">Name:</label>
<input type="text" name="form-0-name" id="id_form-0-name"></div>
<div><label for="id_form-1-name">Name:</label>
<input type="text" name="form-1-name" id="id_form-1-name"></div>""",
        )

    def test_limiting_extra_lest_than_max_num(self):
        """max_num has no effect when extra is less than max_num."""
        LimitedFavoriteDrinkFormSet = formset_factory(
            FavoriteDrinkForm, extra=1, max_num=2
        )
        formset = LimitedFavoriteDrinkFormSet()
        self.assertHTMLEqual(
            "\n".join(str(form) for form in formset.forms),
            """<div><label for="id_form-0-name">Name:</label>
<input type="text" name="form-0-name" id="id_form-0-name"></div>""",
        )

    def test_max_num_with_initial_data(self):
        # When not passed, max_num will take a high default value, leaving the
        # number of forms only controlled by the value of the initial and extra
        # parameters.
        LimitedFavoriteDrinkFormSet = formset_factory(FavoriteDrinkForm, extra=1)
        formset = LimitedFavoriteDrinkFormSet(initial=[{"name": "Fernet and Coke"}])
        self.assertHTMLEqual(
            "\n".join(str(form) for form in formset.forms),
            """
            <div><label for="id_form-0-name">Name:</label>
            <input type="text" name="form-0-name" value="Fernet and Coke"
                id="id_form-0-name"></div>
            <div><label for="id_form-1-name">Name:</label>
            <input type="text" name="form-1-name" id="id_form-1-name"></div>
            """,
        )

    def test_max_num_zero(self):
        """
        If max_num is 0 then no form is rendered at all, regardless of extra,
        unless initial data is present.
        """
        LimitedFavoriteDrinkFormSet = formset_factory(
            FavoriteDrinkForm, extra=1, max_num=0
        )
        formset = LimitedFavoriteDrinkFormSet()
        self.assertEqual(formset.forms, [])

    def test_max_num_zero_with_initial(self):
        # initial trumps max_num
        initial = [
            {"name": "Fernet and Coke"},
            {"name": "Bloody Mary"},
        ]
        LimitedFavoriteDrinkFormSet = formset_factory(
            FavoriteDrinkForm, extra=1, max_num=0
        )
        formset = LimitedFavoriteDrinkFormSet(initial=initial)
        self.assertHTMLEqual(
            "\n".join(str(form) for form in formset.forms),
            """
            <div><label for="id_form-0-name">Name:</label>
            <input id="id_form-0-name" name="form-0-name" type="text"
                value="Fernet and Coke"></div>
            <div><label for="id_form-1-name">Name:</label>
            <input id="id_form-1-name" name="form-1-name" type="text"
                value="Bloody Mary"></div>
            """,
        )

    def test_more_initial_than_max_num(self):
        """
        More initial forms than max_num results in all initial forms being
        displayed (but no extra forms).
        """
        initial = [
            {"name": "Gin Tonic"},
            {"name": "Bloody Mary"},
            {"name": "Jack and Coke"},
        ]
        LimitedFavoriteDrinkFormSet = formset_factory(
            FavoriteDrinkForm, extra=1, max_num=2
        )
        formset = LimitedFavoriteDrinkFormSet(initial=initial)
        self.assertHTMLEqual(
            "\n".join(str(form) for form in formset.forms),
            """
            <div><label for="id_form-0-name">Name:</label>
            <input id="id_form-0-name" name="form-0-name" type="text" value="Gin Tonic">
            </div>
            <div><label for="id_form-1-name">Name:</label>
            <input id="id_form-1-name" name="form-1-name" type="text"
                value="Bloody Mary"></div>
            <div><label for="id_form-2-name">Name:</label>
            <input id="id_form-2-name" name="form-2-name" type="text"
                value="Jack and Coke"></div>
            """,
        )

    def test_default_absolute_max(self):
        # absolute_max defaults to 2 * DEFAULT_MAX_NUM if max_num is None.
        data = {
            "form-TOTAL_FORMS": 2001,
            "form-INITIAL_FORMS": "0",
            "form-MAX_NUM_FORMS": "0",
        }
        formset = FavoriteDrinksFormSet(data=data)
        self.assertIs(formset.is_valid(), False)
        self.assertEqual(
            formset.non_form_errors(),
            ["Please submit at most 1000 forms."],
        )
        self.assertEqual(formset.absolute_max, 2000)

    def test_absolute_max(self):
        data = {
            "form-TOTAL_FORMS": "2001",
            "form-INITIAL_FORMS": "0",
            "form-MAX_NUM_FORMS": "0",
        }
        AbsoluteMaxFavoriteDrinksFormSet = formset_factory(
            FavoriteDrinkForm,
            absolute_max=3000,
        )
        formset = AbsoluteMaxFavoriteDrinksFormSet(data=data)
        self.assertIs(formset.is_valid(), True)
        self.assertEqual(len(formset.forms), 2001)
        # absolute_max provides a hard limit.
        data["form-TOTAL_FORMS"] = "3001"
        formset = AbsoluteMaxFavoriteDrinksFormSet(data=data)
        self.assertIs(formset.is_valid(), False)
        self.assertEqual(len(formset.forms), 3000)
        self.assertEqual(
            formset.non_form_errors(),
            ["Please submit at most 1000 forms."],
        )

    def test_absolute_max_with_max_num(self):
        data = {
            "form-TOTAL_FORMS": "1001",
            "form-INITIAL_FORMS": "0",
            "form-MAX_NUM_FORMS": "0",
        }
        LimitedFavoriteDrinksFormSet = formset_factory(
            FavoriteDrinkForm,
            max_num=30,
            absolute_max=1000,
        )
        formset = LimitedFavoriteDrinksFormSet(data=data)
        self.assertIs(formset.is_valid(), False)
        self.assertEqual(len(formset.forms), 1000)
        self.assertEqual(
            formset.non_form_errors(),
            ["Please submit at most 30 forms."],
        )

    def test_absolute_max_invalid(self):
        msg = "'absolute_max' must be greater or equal to 'max_num'."
        for max_num in [None, 31]:
            with self.subTest(max_num=max_num):
                with self.assertRaisesMessage(ValueError, msg):
                    formset_factory(FavoriteDrinkForm, max_num=max_num, absolute_max=30)

    def test_more_initial_form_result_in_one(self):
        """
        One form from initial and extra=3 with max_num=2 results in the one
        initial form and one extra.
        """
        LimitedFavoriteDrinkFormSet = formset_factory(
            FavoriteDrinkForm, extra=3, max_num=2
        )
        formset = LimitedFavoriteDrinkFormSet(initial=[{"name": "Gin Tonic"}])
        self.assertHTMLEqual(
            "\n".join(str(form) for form in formset.forms),
            """
            <div><label for="id_form-0-name">Name:</label>
            <input type="text" name="form-0-name" value="Gin Tonic" id="id_form-0-name">
            </div>
            <div><label for="id_form-1-name">Name:</label>
            <input type="text" name="form-1-name" id="id_form-1-name"></div>""",
        )

    def test_management_form_field_names(self):
        """The management form class has field names matching the constants."""
        self.assertCountEqual(
            ManagementForm.base_fields,
            [
                TOTAL_FORM_COUNT,
                INITIAL_FORM_COUNT,
                MIN_NUM_FORM_COUNT,
                MAX_NUM_FORM_COUNT,
            ],
        )

    def test_management_form_prefix(self):
        """The management form has the correct prefix."""
        formset = FavoriteDrinksFormSet()
        self.assertEqual(formset.management_form.prefix, "form")
        data = {
            "form-TOTAL_FORMS": "2",
            "form-INITIAL_FORMS": "0",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "0",
        }
        formset = FavoriteDrinksFormSet(data=data)
        self.assertEqual(formset.management_form.prefix, "form")
        formset = FavoriteDrinksFormSet(initial={})
        self.assertEqual(formset.management_form.prefix, "form")

    def test_non_form_errors(self):
        data = {
            "drinks-TOTAL_FORMS": "2",  # the number of forms rendered
            "drinks-INITIAL_FORMS": "0",  # the number of forms with initial data
            "drinks-MIN_NUM_FORMS": "0",  # min number of forms
            "drinks-MAX_NUM_FORMS": "0",  # max number of forms
            "drinks-0-name": "Gin and Tonic",
            "drinks-1-name": "Gin and Tonic",
        }
        formset = FavoriteDrinksFormSet(data, prefix="drinks")
        self.assertFalse(formset.is_valid())
        self.assertEqual(
            formset.non_form_errors(), ["You may only specify a drink once."]
        )
        self.assertEqual(
            str(formset.non_form_errors()),
            '<ul class="errorlist nonform"><li>'
            "You may only specify a drink once.</li></ul>",
        )

    def test_formset_iteration(self):
        """Formset instances are iterable."""
        ChoiceFormset = formset_factory(Choice, extra=3)
        formset = ChoiceFormset()
        # An iterated formset yields formset.forms.
        forms = list(formset)
        self.assertEqual(forms, formset.forms)
        self.assertEqual(len(formset), len(forms))
        # A formset may be indexed to retrieve its forms.
        self.assertEqual(formset[0], forms[0])
        with self.assertRaises(IndexError):
            formset[3]

        # Formsets can override the default iteration order
        class BaseReverseFormSet(BaseFormSet):
            def __iter__(self):
                return reversed(self.forms)

            def __getitem__(self, idx):
                return super().__getitem__(len(self) - idx - 1)

        ReverseChoiceFormset = formset_factory(Choice, BaseReverseFormSet, extra=3)
        reverse_formset = ReverseChoiceFormset()
        # __iter__() modifies the rendering order.
        # Compare forms from "reverse" formset with forms from original formset
        self.assertEqual(str(reverse_formset[0]), str(forms[-1]))
        self.assertEqual(str(reverse_formset[1]), str(forms[-2]))
        self.assertEqual(len(reverse_formset), len(forms))

    def test_formset_nonzero(self):
        """A formsets without any forms evaluates as True."""
        ChoiceFormset = formset_factory(Choice, extra=0)
        formset = ChoiceFormset()
        self.assertEqual(len(formset.forms), 0)
        self.assertTrue(formset)

    def test_formset_splitdatetimefield(self):
        """
        Formset works with SplitDateTimeField(initial=datetime.datetime.now).
        """

        class SplitDateTimeForm(Form):
            when = SplitDateTimeField(initial=datetime.datetime.now)

        SplitDateTimeFormSet = formset_factory(SplitDateTimeForm)
        data = {
            "form-TOTAL_FORMS": "1",
            "form-INITIAL_FORMS": "0",
            "form-0-when_0": "1904-06-16",
            "form-0-when_1": "15:51:33",
        }
        formset = SplitDateTimeFormSet(data)
        self.assertTrue(formset.is_valid())

    def test_formset_error_class(self):
        """Formset's forms use the formset's error_class."""

        class CustomErrorList(ErrorList):
            pass

        formset = FavoriteDrinksFormSet(error_class=CustomErrorList)
        self.assertEqual(formset.forms[0].error_class, CustomErrorList)

    def test_formset_calls_forms_is_valid(self):
        """Formsets call is_valid() on each form."""

        class AnotherChoice(Choice):
            def is_valid(self):
                self.is_valid_called = True
                return super().is_valid()

        AnotherChoiceFormSet = formset_factory(AnotherChoice)
        data = {
            "choices-TOTAL_FORMS": "1",  # number of forms rendered
            "choices-INITIAL_FORMS": "0",  # number of forms with initial data
            "choices-MIN_NUM_FORMS": "0",  # min number of forms
            "choices-MAX_NUM_FORMS": "0",  # max number of forms
            "choices-0-choice": "Calexico",
            "choices-0-votes": "100",
        }
        formset = AnotherChoiceFormSet(data, auto_id=False, prefix="choices")
        self.assertTrue(formset.is_valid())
        self.assertTrue(all(form.is_valid_called for form in formset.forms))

    def test_hard_limit_on_instantiated_forms(self):
        """A formset has a hard limit on the number of forms instantiated."""
        # reduce the default limit of 1000 temporarily for testing
        _old_DEFAULT_MAX_NUM = formsets.DEFAULT_MAX_NUM
        try:
            formsets.DEFAULT_MAX_NUM = 2
            ChoiceFormSet = formset_factory(Choice, max_num=1)
            # someone fiddles with the mgmt form data...
            formset = ChoiceFormSet(
                {
                    "choices-TOTAL_FORMS": "4",
                    "choices-INITIAL_FORMS": "0",
                    "choices-MIN_NUM_FORMS": "0",  # min number of forms
                    "choices-MAX_NUM_FORMS": "4",
                    "choices-0-choice": "Zero",
                    "choices-0-votes": "0",
                    "choices-1-choice": "One",
                    "choices-1-votes": "1",
                    "choices-2-choice": "Two",
                    "choices-2-votes": "2",
                    "choices-3-choice": "Three",
                    "choices-3-votes": "3",
                },
                prefix="choices",
            )
            # But we still only instantiate 3 forms
            self.assertEqual(len(formset.forms), 3)
            # and the formset isn't valid
            self.assertFalse(formset.is_valid())
        finally:
            formsets.DEFAULT_MAX_NUM = _old_DEFAULT_MAX_NUM

    def test_increase_hard_limit(self):
        """Can increase the built-in forms limit via a higher max_num."""
        # reduce the default limit of 1000 temporarily for testing
        _old_DEFAULT_MAX_NUM = formsets.DEFAULT_MAX_NUM
        try:
            formsets.DEFAULT_MAX_NUM = 3
            # for this form, we want a limit of 4
            ChoiceFormSet = formset_factory(Choice, max_num=4)
            formset = ChoiceFormSet(
                {
                    "choices-TOTAL_FORMS": "4",
                    "choices-INITIAL_FORMS": "0",
                    "choices-MIN_NUM_FORMS": "0",  # min number of forms
                    "choices-MAX_NUM_FORMS": "4",
                    "choices-0-choice": "Zero",
                    "choices-0-votes": "0",
                    "choices-1-choice": "One",
                    "choices-1-votes": "1",
                    "choices-2-choice": "Two",
                    "choices-2-votes": "2",
                    "choices-3-choice": "Three",
                    "choices-3-votes": "3",
                },
                prefix="choices",
            )
            # Four forms are instantiated and no exception is raised
            self.assertEqual(len(formset.forms), 4)
        finally:
            formsets.DEFAULT_MAX_NUM = _old_DEFAULT_MAX_NUM

    def test_non_form_errors_run_full_clean(self):
        """
        If non_form_errors() is called without calling is_valid() first,
        it should ensure that full_clean() is called.
        """

        class BaseCustomFormSet(BaseFormSet):
            def clean(self):
                raise ValidationError("This is a non-form error")

        ChoiceFormSet = formset_factory(Choice, formset=BaseCustomFormSet)
        data = {
            "choices-TOTAL_FORMS": "1",
            "choices-INITIAL_FORMS": "0",
        }
        formset = ChoiceFormSet(data, auto_id=False, prefix="choices")
        self.assertIsInstance(formset.non_form_errors(), ErrorList)
        self.assertEqual(list(formset.non_form_errors()), ["This is a non-form error"])

    def test_validate_max_ignores_forms_marked_for_deletion(self):
        class CheckForm(Form):
            field = IntegerField()

        data = {
            "check-TOTAL_FORMS": "2",
            "check-INITIAL_FORMS": "0",
            "check-MAX_NUM_FORMS": "1",
            "check-0-field": "200",
            "check-0-DELETE": "",
            "check-1-field": "50",
            "check-1-DELETE": "on",
        }
        CheckFormSet = formset_factory(
            CheckForm, max_num=1, validate_max=True, can_delete=True
        )
        formset = CheckFormSet(data, prefix="check")
        self.assertTrue(formset.is_valid())

    def test_formset_total_error_count(self):
        """A valid formset should have 0 total errors."""
        data = [  # formset_data, expected error count
            ([("Calexico", "100")], 0),
            ([("Calexico", "")], 1),
            ([("", "invalid")], 2),
            ([("Calexico", "100"), ("Calexico", "")], 1),
            ([("Calexico", ""), ("Calexico", "")], 2),
        ]
        for formset_data, expected_error_count in data:
            formset = self.make_choiceformset(formset_data)
            self.assertEqual(formset.total_error_count(), expected_error_count)

    def test_formset_total_error_count_with_non_form_errors(self):
        data = {
            "choices-TOTAL_FORMS": "2",  # the number of forms rendered
            "choices-INITIAL_FORMS": "0",  # the number of forms with initial data
            "choices-MAX_NUM_FORMS": "2",  # max number of forms - should be ignored
            "choices-0-choice": "Zero",
            "choices-0-votes": "0",
            "choices-1-choice": "One",
            "choices-1-votes": "1",
        }
        ChoiceFormSet = formset_factory(Choice, extra=1, max_num=1, validate_max=True)
        formset = ChoiceFormSet(data, auto_id=False, prefix="choices")
        self.assertEqual(formset.total_error_count(), 1)
        data["choices-1-votes"] = ""
        formset = ChoiceFormSet(data, auto_id=False, prefix="choices")
        self.assertEqual(formset.total_error_count(), 2)

    def test_html_safe(self):
        formset = self.make_choiceformset()
        self.assertTrue(hasattr(formset, "__html__"))
        self.assertEqual(str(formset), formset.__html__())

    def test_can_delete_extra_formset_forms(self):
        ChoiceFormFormset = formset_factory(form=Choice, can_delete=True, extra=2)
        formset = ChoiceFormFormset()
        self.assertEqual(len(formset), 2)
        self.assertIn("DELETE", formset.forms[0].fields)
        self.assertIn("DELETE", formset.forms[1].fields)

    def test_disable_delete_extra_formset_forms(self):
        ChoiceFormFormset = formset_factory(
            form=Choice,
            can_delete=True,
            can_delete_extra=False,
            extra=2,
        )
        formset = ChoiceFormFormset()
        self.assertEqual(len(formset), 2)
        self.assertNotIn("DELETE", formset.forms[0].fields)
        self.assertNotIn("DELETE", formset.forms[1].fields)

        formset = ChoiceFormFormset(initial=[{"choice": "Zero", "votes": "1"}])
        self.assertEqual(len(formset), 3)
        self.assertIn("DELETE", formset.forms[0].fields)
        self.assertNotIn("DELETE", formset.forms[1].fields)
        self.assertNotIn("DELETE", formset.forms[2].fields)

        formset = ChoiceFormFormset(
            data={
                "form-0-choice": "Zero",
                "form-0-votes": "0",
                "form-0-DELETE": "on",
                "form-1-choice": "One",
                "form-1-votes": "1",
                "form-2-choice": "",
                "form-2-votes": "",
                "form-TOTAL_FORMS": "3",
                "form-INITIAL_FORMS": "1",
            },
            initial=[{"choice": "Zero", "votes": "1"}],
        )
        self.assertEqual(
            formset.cleaned_data,
            [
                {"choice": "Zero", "votes": 0, "DELETE": True},
                {"choice": "One", "votes": 1},
                {},
            ],
        )
        self.assertIs(formset._should_delete_form(formset.forms[0]), True)
        self.assertIs(formset._should_delete_form(formset.forms[1]), False)
        self.assertIs(formset._should_delete_form(formset.forms[2]), False)

    def test_template_name_uses_renderer_value(self):
        class CustomRenderer(TemplatesSetting):
            formset_template_name = "a/custom/formset/template.html"

        ChoiceFormSet = formset_factory(Choice, renderer=CustomRenderer)

        self.assertEqual(
            ChoiceFormSet().template_name, "a/custom/formset/template.html"
        )

    def test_template_name_can_be_overridden(self):
        class CustomFormSet(BaseFormSet):
            template_name = "a/custom/formset/template.html"

        ChoiceFormSet = formset_factory(Choice, formset=CustomFormSet)

        self.assertEqual(
            ChoiceFormSet().template_name, "a/custom/formset/template.html"
        )

    def test_custom_renderer(self):
        """
        A custom renderer passed to a formset_factory() is passed to all forms
        and ErrorList.
        """
        from django.forms.renderers import Jinja2

        renderer = Jinja2()
        data = {
            "choices-TOTAL_FORMS": "2",
            "choices-INITIAL_FORMS": "0",
            "choices-MIN_NUM_FORMS": "0",
            "choices-0-choice": "Zero",
            "choices-0-votes": "",
            "choices-1-choice": "One",
            "choices-1-votes": "",
        }
        ChoiceFormSet = formset_factory(Choice, renderer=renderer)
        formset = ChoiceFormSet(data, auto_id=False, prefix="choices")
        self.assertEqual(formset.renderer, renderer)
        self.assertEqual(formset.forms[0].renderer, renderer)
        self.assertEqual(formset.management_form.renderer, renderer)
        self.assertEqual(formset.non_form_errors().renderer, renderer)
        self.assertEqual(formset.empty_form.renderer, renderer)

    def test_repr(self):
        valid_formset = self.make_choiceformset([("test", 1)])
        valid_formset.full_clean()
        invalid_formset = self.make_choiceformset([("test", "")])
        invalid_formset.full_clean()
        partially_invalid_formset = self.make_choiceformset(
            [("test", "1"), ("test", "")],
        )
        partially_invalid_formset.full_clean()
        invalid_formset_non_form_errors_only = self.make_choiceformset(
            [("test", "")],
            formset_class=ChoiceFormsetWithNonFormError,
        )
        invalid_formset_non_form_errors_only.full_clean()

        cases = [
            (
                self.make_choiceformset(),
                "<ChoiceFormSet: bound=False valid=Unknown total_forms=1>",
            ),
            (
                self.make_choiceformset(
                    formset_class=formset_factory(Choice, extra=10),
                ),
                "<ChoiceFormSet: bound=False valid=Unknown total_forms=10>",
            ),
            (
                self.make_choiceformset([]),
                "<ChoiceFormSet: bound=True valid=Unknown total_forms=0>",
            ),
            (
                self.make_choiceformset([("test", 1)]),
                "<ChoiceFormSet: bound=True valid=Unknown total_forms=1>",
            ),
            (valid_formset, "<ChoiceFormSet: bound=True valid=True total_forms=1>"),
            (invalid_formset, "<ChoiceFormSet: bound=True valid=False total_forms=1>"),
            (
                partially_invalid_formset,
                "<ChoiceFormSet: bound=True valid=False total_forms=2>",
            ),
            (
                invalid_formset_non_form_errors_only,
                "<ChoiceFormsetWithNonFormError: bound=True valid=False total_forms=1>",
            ),
        ]
        for formset, expected_repr in cases:
            with self.subTest(expected_repr=expected_repr):
                self.assertEqual(repr(formset), expected_repr)

    def test_repr_do_not_trigger_validation(self):
        formset = self.make_choiceformset([("test", 1)])
        with mock.patch.object(formset, "full_clean") as mocked_full_clean:
            repr(formset)
            mocked_full_clean.assert_not_called()
            formset.is_valid()
            mocked_full_clean.assert_called()


@jinja2_tests
class Jinja2FormsFormsetTestCase(FormsFormsetTestCase):
    pass


class FormsetAsTagTests(SimpleTestCase):
    def setUp(self):
        data = {
            "choices-TOTAL_FORMS": "1",
            "choices-INITIAL_FORMS": "0",
            "choices-MIN_NUM_FORMS": "0",
            "choices-MAX_NUM_FORMS": "0",
            "choices-0-choice": "Calexico",
            "choices-0-votes": "100",
        }
        self.formset = ChoiceFormSet(data, auto_id=False, prefix="choices")
        self.management_form_html = (
            '<input type="hidden" name="choices-TOTAL_FORMS" value="1">'
            '<input type="hidden" name="choices-INITIAL_FORMS" value="0">'
            '<input type="hidden" name="choices-MIN_NUM_FORMS" value="0">'
            '<input type="hidden" name="choices-MAX_NUM_FORMS" value="0">'
        )

    def test_as_table(self):
        self.assertHTMLEqual(
            self.formset.as_table(),
            self.management_form_html
            + (
                "<tr><th>Choice:</th><td>"
                '<input type="text" name="choices-0-choice" value="Calexico"></td></tr>'
                "<tr><th>Votes:</th><td>"
                '<input type="number" name="choices-0-votes" value="100"></td></tr>'
            ),
        )

    def test_as_p(self):
        self.assertHTMLEqual(
            self.formset.as_p(),
            self.management_form_html
            + (
                "<p>Choice: "
                '<input type="text" name="choices-0-choice" value="Calexico"></p>'
                '<p>Votes: <input type="number" name="choices-0-votes" value="100"></p>'
            ),
        )

    def test_as_ul(self):
        self.assertHTMLEqual(
            self.formset.as_ul(),
            self.management_form_html
            + (
                "<li>Choice: "
                '<input type="text" name="choices-0-choice" value="Calexico"></li>'
                "<li>Votes: "
                '<input type="number" name="choices-0-votes" value="100"></li>'
            ),
        )

    def test_as_div(self):
        self.assertHTMLEqual(
            self.formset.as_div(),
            self.management_form_html
            + (
                "<div>Choice: "
                '<input type="text" name="choices-0-choice" value="Calexico"></div>'
                '<div>Votes: <input type="number" name="choices-0-votes" value="100">'
                "</div>"
            ),
        )


@jinja2_tests
class Jinja2FormsetAsTagTests(FormsetAsTagTests):
    pass


class ArticleForm(Form):
    title = CharField()
    pub_date = DateField()


ArticleFormSet = formset_factory(ArticleForm)


class TestIsBoundBehavior(SimpleTestCase):
    def test_no_data_error(self):
        formset = ArticleFormSet({})
        self.assertIs(formset.is_valid(), False)
        self.assertEqual(
            formset.non_form_errors(),
            [
                "ManagementForm data is missing or has been tampered with. "
                "Missing fields: form-TOTAL_FORMS, form-INITIAL_FORMS. "
                "You may need to file a bug report if the issue persists.",
            ],
        )
        self.assertEqual(formset.errors, [])
        # Can still render the formset.
        self.assertHTMLEqual(
            str(formset),
            '<ul class="errorlist nonfield">'
            "<li>(Hidden field TOTAL_FORMS) This field is required.</li>"
            "<li>(Hidden field INITIAL_FORMS) This field is required.</li>"
            "</ul>"
            "<div>"
            '<input type="hidden" name="form-TOTAL_FORMS" id="id_form-TOTAL_FORMS">'
            '<input type="hidden" name="form-INITIAL_FORMS" id="id_form-INITIAL_FORMS">'
            '<input type="hidden" name="form-MIN_NUM_FORMS" id="id_form-MIN_NUM_FORMS">'
            '<input type="hidden" name="form-MAX_NUM_FORMS" id="id_form-MAX_NUM_FORMS">'
            "</div>\n",
        )

    def test_management_form_invalid_data(self):
        data = {
            "form-TOTAL_FORMS": "two",
            "form-INITIAL_FORMS": "one",
        }
        formset = ArticleFormSet(data)
        self.assertIs(formset.is_valid(), False)
        self.assertEqual(
            formset.non_form_errors(),
            [
                "ManagementForm data is missing or has been tampered with. "
                "Missing fields: form-TOTAL_FORMS, form-INITIAL_FORMS. "
                "You may need to file a bug report if the issue persists.",
            ],
        )
        self.assertEqual(formset.errors, [])
        # Can still render the formset.
        self.assertHTMLEqual(
            str(formset),
            '<ul class="errorlist nonfield">'
            "<li>(Hidden field TOTAL_FORMS) Enter a whole number.</li>"
            "<li>(Hidden field INITIAL_FORMS) Enter a whole number.</li>"
            "</ul>"
            "<div>"
            '<input type="hidden" name="form-TOTAL_FORMS" value="two" '
            'id="id_form-TOTAL_FORMS">'
            '<input type="hidden" name="form-INITIAL_FORMS" value="one" '
            'id="id_form-INITIAL_FORMS">'
            '<input type="hidden" name="form-MIN_NUM_FORMS" id="id_form-MIN_NUM_FORMS">'
            '<input type="hidden" name="form-MAX_NUM_FORMS" id="id_form-MAX_NUM_FORMS">'
            "</div>\n",
        )

    def test_customize_management_form_error(self):
        formset = ArticleFormSet(
            {}, error_messages={"missing_management_form": "customized"}
        )
        self.assertIs(formset.is_valid(), False)
        self.assertEqual(formset.non_form_errors(), ["customized"])
        self.assertEqual(formset.errors, [])

    def test_with_management_data_attrs_work_fine(self):
        data = {
            "form-TOTAL_FORMS": "1",
            "form-INITIAL_FORMS": "0",
        }
        formset = ArticleFormSet(data)
        self.assertEqual(0, formset.initial_form_count())
        self.assertEqual(1, formset.total_form_count())
        self.assertTrue(formset.is_bound)
        self.assertTrue(formset.forms[0].is_bound)
        self.assertTrue(formset.is_valid())
        self.assertTrue(formset.forms[0].is_valid())
        self.assertEqual([{}], formset.cleaned_data)

    def test_form_errors_are_caught_by_formset(self):
        data = {
            "form-TOTAL_FORMS": "2",
            "form-INITIAL_FORMS": "0",
            "form-0-title": "Test",
            "form-0-pub_date": "1904-06-16",
            "form-1-title": "Test",
            "form-1-pub_date": "",  # <-- this date is missing but required
        }
        formset = ArticleFormSet(data)
        self.assertFalse(formset.is_valid())
        self.assertEqual(
            [{}, {"pub_date": ["This field is required."]}], formset.errors
        )

    def test_empty_forms_are_unbound(self):
        data = {
            "form-TOTAL_FORMS": "1",
            "form-INITIAL_FORMS": "0",
            "form-0-title": "Test",
            "form-0-pub_date": "1904-06-16",
        }
        unbound_formset = ArticleFormSet()
        bound_formset = ArticleFormSet(data)
        empty_forms = [unbound_formset.empty_form, bound_formset.empty_form]
        # Empty forms should be unbound
        self.assertFalse(empty_forms[0].is_bound)
        self.assertFalse(empty_forms[1].is_bound)
        # The empty forms should be equal.
        self.assertHTMLEqual(empty_forms[0].as_p(), empty_forms[1].as_p())


@jinja2_tests
class TestIsBoundBehavior(TestIsBoundBehavior):
    pass


class TestEmptyFormSet(SimpleTestCase):
    def test_empty_formset_is_valid(self):
        """An empty formset still calls clean()"""

        class EmptyFsetWontValidate(BaseFormSet):
            def clean(self):
                raise ValidationError("Clean method called")

        EmptyFsetWontValidateFormset = formset_factory(
            FavoriteDrinkForm, extra=0, formset=EmptyFsetWontValidate
        )
        formset = EmptyFsetWontValidateFormset(
            data={"form-INITIAL_FORMS": "0", "form-TOTAL_FORMS": "0"},
            prefix="form",
        )
        formset2 = EmptyFsetWontValidateFormset(
            data={
                "form-INITIAL_FORMS": "0",
                "form-TOTAL_FORMS": "1",
                "form-0-name": "bah",
            },
            prefix="form",
        )
        self.assertFalse(formset.is_valid())
        self.assertFalse(formset2.is_valid())

    def test_empty_formset_media(self):
        """Media is available on empty formset."""

        class MediaForm(Form):
            class Media:
                js = ("some-file.js",)

        self.assertIn("some-file.js", str(formset_factory(MediaForm, extra=0)().media))

    def test_empty_formset_is_multipart(self):
        """is_multipart() works with an empty formset."""

        class FileForm(Form):
            file = FileField()

        self.assertTrue(formset_factory(FileForm, extra=0)().is_multipart())


class AllValidTests(SimpleTestCase):
    def test_valid(self):
        data = {
            "choices-TOTAL_FORMS": "2",
            "choices-INITIAL_FORMS": "0",
            "choices-MIN_NUM_FORMS": "0",
            "choices-0-choice": "Zero",
            "choices-0-votes": "0",
            "choices-1-choice": "One",
            "choices-1-votes": "1",
        }
        ChoiceFormSet = formset_factory(Choice)
        formset1 = ChoiceFormSet(data, auto_id=False, prefix="choices")
        formset2 = ChoiceFormSet(data, auto_id=False, prefix="choices")
        self.assertIs(all_valid((formset1, formset2)), True)
        expected_errors = [{}, {}]
        self.assertEqual(formset1._errors, expected_errors)
        self.assertEqual(formset2._errors, expected_errors)

    def test_invalid(self):
        """all_valid() validates all forms, even when some are invalid."""
        data = {
            "choices-TOTAL_FORMS": "2",
            "choices-INITIAL_FORMS": "0",
            "choices-MIN_NUM_FORMS": "0",
            "choices-0-choice": "Zero",
            "choices-0-votes": "",
            "choices-1-choice": "One",
            "choices-1-votes": "",
        }
        ChoiceFormSet = formset_factory(Choice)
        formset1 = ChoiceFormSet(data, auto_id=False, prefix="choices")
        formset2 = ChoiceFormSet(data, auto_id=False, prefix="choices")
        self.assertIs(all_valid((formset1, formset2)), False)
        expected_errors = [
            {"votes": ["This field is required."]},
            {"votes": ["This field is required."]},
        ]
        self.assertEqual(formset1._errors, expected_errors)
        self.assertEqual(formset2._errors, expected_errors)
