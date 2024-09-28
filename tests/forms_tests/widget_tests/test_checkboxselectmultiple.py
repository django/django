import datetime

from django import forms
from django.forms import CheckboxSelectMultiple, ChoiceField, Form
from django.test import override_settings

from .base import WidgetTest


class CheckboxSelectMultipleTest(WidgetTest):
    widget = CheckboxSelectMultiple

    def test_render_value(self):
        self.check_html(
            self.widget(choices=self.beatles),
            "beatles",
            ["J"],
            html="""
            <div>
            <div><label><input checked type="checkbox" name="beatles" value="J"> John
            </label></div>
            <div><label><input type="checkbox" name="beatles" value="P"> Paul
            </label></div>
            <div><label><input type="checkbox" name="beatles" value="G"> George
            </label></div>
            <div><label><input type="checkbox" name="beatles" value="R"> Ringo
            </label></div>
            </div>
        """,
        )

    def test_render_value_multiple(self):
        self.check_html(
            self.widget(choices=self.beatles),
            "beatles",
            ["J", "P"],
            html="""
            <div>
            <div><label><input checked type="checkbox" name="beatles" value="J"> John
            </label></div>
            <div><label><input checked type="checkbox" name="beatles" value="P"> Paul
            </label></div>
            <div><label><input type="checkbox" name="beatles" value="G"> George
            </label></div>
            <div><label><input type="checkbox" name="beatles" value="R"> Ringo
            </label></div>
            </div>
        """,
        )

    def test_render_none(self):
        """
        If the value is None, none of the options are selected, even if the
        choices have an empty option.
        """
        self.check_html(
            self.widget(choices=(("", "Unknown"),) + self.beatles),
            "beatles",
            None,
            html="""
            <div>
            <div><label><input type="checkbox" name="beatles" value=""> Unknown
            </label></div>
            <div><label><input type="checkbox" name="beatles" value="J"> John
            </label></div>
            <div><label><input type="checkbox" name="beatles" value="P"> Paul
            </label></div>
            <div><label><input type="checkbox" name="beatles" value="G"> George
            </label></div>
            <div><label><input type="checkbox" name="beatles" value="R"> Ringo
            </label></div>
            </div>
        """,
        )

    def test_nested_choices(self):
        nested_choices = (
            ("unknown", "Unknown"),
            ("Audio", (("vinyl", "Vinyl"), ("cd", "CD"))),
            ("Video", (("vhs", "VHS"), ("dvd", "DVD"))),
        )
        html = """
        <div id="media">
        <div> <label for="media_0">
        <input type="checkbox" name="nestchoice" value="unknown" id="media_0"> Unknown
        </label></div>
        <div>
        <label>Audio</label>
        <div> <label for="media_1_0">
        <input checked type="checkbox" name="nestchoice" value="vinyl" id="media_1_0">
        Vinyl</label></div>
        <div> <label for="media_1_1">
        <input type="checkbox" name="nestchoice" value="cd" id="media_1_1"> CD
        </label></div>
        </div><div>
        <label>Video</label>
        <div> <label for="media_2_0">
        <input type="checkbox" name="nestchoice" value="vhs" id="media_2_0"> VHS
        </label></div>
        <div> <label for="media_2_1">
        <input type="checkbox" name="nestchoice" value="dvd" id="media_2_1" checked> DVD
        </label></div>
        </div>
        </div>
        """
        self.check_html(
            self.widget(choices=nested_choices),
            "nestchoice",
            ("vinyl", "dvd"),
            attrs={"id": "media"},
            html=html,
        )

    def test_nested_choices_without_id(self):
        nested_choices = (
            ("unknown", "Unknown"),
            ("Audio", (("vinyl", "Vinyl"), ("cd", "CD"))),
            ("Video", (("vhs", "VHS"), ("dvd", "DVD"))),
        )
        html = """
        <div>
        <div> <label>
        <input type="checkbox" name="nestchoice" value="unknown"> Unknown</label></div>
        <div>
        <label>Audio</label>
        <div> <label>
        <input checked type="checkbox" name="nestchoice" value="vinyl"> Vinyl
        </label></div>
        <div> <label>
        <input type="checkbox" name="nestchoice" value="cd"> CD</label></div>
        </div><div>
        <label>Video</label>
        <div> <label>
        <input type="checkbox" name="nestchoice" value="vhs"> VHS</label></div>
        <div> <label>
        <input type="checkbox" name="nestchoice" value="dvd"checked> DVD</label></div>
        </div>
        </div>
        """
        self.check_html(
            self.widget(choices=nested_choices),
            "nestchoice",
            ("vinyl", "dvd"),
            html=html,
        )

    def test_separate_ids(self):
        """
        Each input gets a separate ID.
        """
        choices = [("a", "A"), ("b", "B"), ("c", "C")]
        html = """
        <div id="abc">
        <div>
        <label for="abc_0">
        <input checked type="checkbox" name="letters" value="a" id="abc_0"> A</label>
        </div>
        <div><label for="abc_1">
        <input type="checkbox" name="letters" value="b" id="abc_1"> B</label></div>
        <div>
        <label for="abc_2">
        <input checked type="checkbox" name="letters" value="c" id="abc_2"> C</label>
        </div>
        </div>
        """
        self.check_html(
            self.widget(choices=choices),
            "letters",
            ["a", "c"],
            attrs={"id": "abc"},
            html=html,
        )

    def test_separate_ids_constructor(self):
        """
        Each input gets a separate ID when the ID is passed to the constructor.
        """
        widget = CheckboxSelectMultiple(
            attrs={"id": "abc"}, choices=[("a", "A"), ("b", "B"), ("c", "C")]
        )
        html = """
        <div id="abc">
        <div>
        <label for="abc_0">
        <input checked type="checkbox" name="letters" value="a" id="abc_0"> A</label>
        </div>
        <div><label for="abc_1">
        <input type="checkbox" name="letters" value="b" id="abc_1"> B</label></div>
        <div>
        <label for="abc_2">
        <input checked type="checkbox" name="letters" value="c" id="abc_2"> C</label>
        </div>
        </div>
        """
        self.check_html(widget, "letters", ["a", "c"], html=html)

    @override_settings(USE_THOUSAND_SEPARATOR=True)
    def test_doesnt_localize_input_value(self):
        choices = [
            (1, "One"),
            (1000, "One thousand"),
            (1000000, "One million"),
        ]
        html = """
        <div>
        <div><label><input type="checkbox" name="numbers" value="1"> One</label></div>
        <div><label>
        <input type="checkbox" name="numbers" value="1000"> One thousand</label></div>
        <div><label>
        <input type="checkbox" name="numbers" value="1000000"> One million</label></div>
        </div>
        """
        self.check_html(self.widget(choices=choices), "numbers", None, html=html)

        choices = [
            (datetime.time(0, 0), "midnight"),
            (datetime.time(12, 0), "noon"),
        ]
        html = """
        <div>
        <div><label>
        <input type="checkbox" name="times" value="00:00:00"> midnight</label></div>
        <div><label>
        <input type="checkbox" name="times" value="12:00:00"> noon</label></div>
        </div>
        """
        self.check_html(self.widget(choices=choices), "times", None, html=html)

    def test_use_required_attribute(self):
        widget = self.widget(choices=self.beatles)
        # Always False because browser validation would require all checkboxes
        # to be checked instead of at least one.
        self.assertIs(widget.use_required_attribute(None), False)
        self.assertIs(widget.use_required_attribute([]), False)
        self.assertIs(widget.use_required_attribute(["J", "P"]), False)

    def test_value_omitted_from_data(self):
        widget = self.widget(choices=self.beatles)
        self.assertIs(widget.value_omitted_from_data({}, {}, "field"), False)
        self.assertIs(
            widget.value_omitted_from_data({"field": "value"}, {}, "field"), False
        )

    def test_label(self):
        """
        CheckboxSelectMultiple doesn't contain 'for="field_0"' in the <label>
        because clicking that would toggle the first checkbox.
        """

        class TestForm(forms.Form):
            f = forms.MultipleChoiceField(widget=CheckboxSelectMultiple)

        bound_field = TestForm()["f"]
        self.assertEqual(bound_field.field.widget.id_for_label("id"), "")
        self.assertEqual(bound_field.label_tag(), "<label>F:</label>")
        self.assertEqual(bound_field.legend_tag(), "<legend>F:</legend>")

    def test_fieldset(self):
        class TestForm(Form):
            template_name = "forms_tests/use_fieldset.html"
            field = ChoiceField(widget=self.widget, choices=self.beatles)

        form = TestForm()
        self.assertIs(self.widget.use_fieldset, True)
        self.assertHTMLEqual(
            form.render(),
            '<div><fieldset><legend>Field:</legend><div id="id_field">'
            '<div><label for="id_field_0"><input type="checkbox" '
            'name="field" value="J" id="id_field_0"> John</label></div>'
            '<div><label for="id_field_1"><input type="checkbox" '
            'name="field" value="P" id="id_field_1">Paul</label></div>'
            '<div><label for="id_field_2"><input type="checkbox" '
            'name="field" value="G" id="id_field_2"> George</label></div>'
            '<div><label for="id_field_3"><input type="checkbox" '
            'name="field" value="R" id="id_field_3">'
            "Ringo</label></div></div></fieldset></div>",
        )
