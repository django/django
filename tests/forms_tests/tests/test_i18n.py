from django.forms import (
    CharField,
    ChoiceField,
    Form,
    IntegerField,
    RadioSelect,
    Select,
    TextInput,
)
from django.test import SimpleTestCase
from django.utils import translation
from django.utils.translation import gettext_lazy

from . import jinja2_tests


class FormsI18nTests(SimpleTestCase):
    def test_lazy_labels(self):
        class SomeForm(Form):
            username = CharField(max_length=10, label=gettext_lazy("username"))

        f = SomeForm()
        self.assertHTMLEqual(
            f.as_p(),
            '<p><label for="id_username">username:</label>'
            '<input id="id_username" type="text" name="username" maxlength="10" '
            "required></p>",
        )

        # Translations are done at rendering time, so multi-lingual apps can
        # define forms.
        with translation.override("de"):
            self.assertHTMLEqual(
                f.as_p(),
                '<p><label for="id_username">Benutzername:</label>'
                '<input id="id_username" type="text" name="username" maxlength="10" '
                "required></p>",
            )
        with translation.override("pl"):
            self.assertHTMLEqual(
                f.as_p(),
                '<p><label for="id_username">nazwa u\u017cytkownika:</label>'
                '<input id="id_username" type="text" name="username" maxlength="10" '
                "required></p>",
            )

    def test_non_ascii_label(self):
        class SomeForm(Form):
            field_1 = CharField(max_length=10, label=gettext_lazy("field_1"))
            field_2 = CharField(
                max_length=10,
                label=gettext_lazy("field_2"),
                widget=TextInput(attrs={"id": "field_2_id"}),
            )

        f = SomeForm()
        self.assertHTMLEqual(
            f["field_1"].label_tag(), '<label for="id_field_1">field_1:</label>'
        )
        self.assertHTMLEqual(
            f["field_1"].legend_tag(),
            '<legend for="id_field_1">field_1:</legend>',
        )
        self.assertHTMLEqual(
            f["field_2"].label_tag(), '<label for="field_2_id">field_2:</label>'
        )
        self.assertHTMLEqual(
            f["field_2"].legend_tag(),
            '<legend for="field_2_id">field_2:</legend>',
        )

    def test_non_ascii_choices(self):
        class SomeForm(Form):
            somechoice = ChoiceField(
                choices=(("\xc5", "En tied\xe4"), ("\xf8", "Mies"), ("\xdf", "Nainen")),
                widget=RadioSelect(),
                label="\xc5\xf8\xdf",
            )

        f = SomeForm()
        self.assertHTMLEqual(
            f.as_p(),
            "<p><label>\xc5\xf8\xdf:</label>"
            '<div id="id_somechoice">\n'
            '<div><label for="id_somechoice_0">'
            '<input type="radio" id="id_somechoice_0" value="\xc5" name="somechoice" '
            "required> En tied\xe4</label></div>\n"
            '<div><label for="id_somechoice_1">'
            '<input type="radio" id="id_somechoice_1" value="\xf8" name="somechoice" '
            'required> Mies</label></div>\n<div><label for="id_somechoice_2">'
            '<input type="radio" id="id_somechoice_2" value="\xdf" name="somechoice" '
            "required> Nainen</label></div>\n</div></p>",
        )

        # Translated error messages
        with translation.override("ru"):
            f = SomeForm({})
            self.assertHTMLEqual(
                f.as_p(),
                '<ul class="errorlist" id="id_somechoice_error"><li>'
                "\u041e\u0431\u044f\u0437\u0430\u0442\u0435\u043b\u044c"
                "\u043d\u043e\u0435 \u043f\u043e\u043b\u0435.</li></ul>\n"
                "<p><label>\xc5\xf8\xdf:</label>"
                ' <div id="id_somechoice">\n<div><label for="id_somechoice_0">'
                '<input type="radio" id="id_somechoice_0" value="\xc5" '
                'name="somechoice" aria-invalid="true" required>'
                "En tied\xe4</label></div>\n"
                '<div><label for="id_somechoice_1">'
                '<input type="radio" id="id_somechoice_1" value="\xf8" '
                'name="somechoice" aria-invalid="true" required>'
                "Mies</label></div>\n<div>"
                '<label for="id_somechoice_2">'
                '<input type="radio" id="id_somechoice_2" value="\xdf" '
                'name="somechoice" aria-invalid="true" required>'
                "Nainen</label></div>\n</div></p>",
            )

    def test_select_translated_text(self):
        # Deep copying translated text shouldn't raise an error.
        class CopyForm(Form):
            degree = IntegerField(widget=Select(choices=((1, gettext_lazy("test")),)))

        CopyForm()


@jinja2_tests
class Jinja2FormsI18nTests(FormsI18nTests):
    pass
