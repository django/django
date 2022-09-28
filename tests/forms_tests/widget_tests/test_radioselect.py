import datetime

from django.forms import ChoiceField, Form, MultiWidget, RadioSelect
from django.test import override_settings

from .base import WidgetTest


class RadioSelectTest(WidgetTest):
    widget = RadioSelect

    def test_render(self):
        choices = (("", "------"),) + self.beatles
        self.check_html(
            self.widget(choices=choices),
            "beatle",
            "J",
            html="""
            <div>
            <div><label><input type="radio" name="beatle" value=""> <span>------</span></label></div>
            <div><label>
            <input checked type="radio" name="beatle" value="J"> <span>John</span></label></div>
            <div><label><input type="radio" name="beatle" value="P"> <span>Paul</span></label></div>
            <div><label>
            <input type="radio" name="beatle" value="G"> <span>George</span></label></div>
            <div><label><input type="radio" name="beatle" value="R"> <span>Ringo</span></label></div>
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
        <div>
        <label for="media_0">
        <input type="radio" name="nestchoice" value="unknown" id="media_0"> <span>Unknown</span>
        </label></div>
        <div>
        <label><span>Audio</span></label>
        <div>
        <label for="media_1_0">
        <input type="radio" name="nestchoice" value="vinyl" id="media_1_0"> <span>Vinyl</span>
        </label></div>
        <div> <label for="media_1_1">
        <input type="radio" name="nestchoice" value="cd" id="media_1_1"> <span>CD</span>
        </label></div>
        </div><div>
        <label><span>Video</span></label>
        <div>
        <label for="media_2_0">
        <input type="radio" name="nestchoice" value="vhs" id="media_2_0"> <span>VHS</span>
        </label></div>
        <div>
        <label for="media_2_1">
        <input type="radio" name="nestchoice" value="dvd" id="media_2_1" checked> <span>DVD</span>
        </label></div>
        </div>
        </div>
        """
        self.check_html(
            self.widget(choices=nested_choices),
            "nestchoice",
            "dvd",
            attrs={"id": "media"},
            html=html,
        )

    def test_constructor_attrs(self):
        """
        Attributes provided at instantiation are passed to the constituent
        inputs.
        """
        widget = RadioSelect(attrs={"id": "foo"}, choices=self.beatles)
        html = """
        <div id="foo">
        <div>
        <label for="foo_0">
        <input checked type="radio" id="foo_0" value="J" name="beatle"> <span>John</span></label>
        </div>
        <div><label for="foo_1">
        <input type="radio" id="foo_1" value="P" name="beatle"> <span>Paul</span></label></div>
        <div><label for="foo_2">
        <input type="radio" id="foo_2" value="G" name="beatle"> <span>George</span></label></div>
        <div><label for="foo_3">
        <input type="radio" id="foo_3" value="R" name="beatle"> <span>Ringo</span></label></div>
        </div>
        """
        self.check_html(widget, "beatle", "J", html=html)

    def test_render_attrs(self):
        """
        Attributes provided at render-time are passed to the constituent
        inputs.
        """
        html = """
        <div id="bar">
        <div>
        <label for="bar_0">
        <input checked type="radio" id="bar_0" value="J" name="beatle"> <span>John</span></label>
        </div>
        <div><label for="bar_1">
        <input type="radio" id="bar_1" value="P" name="beatle"> <span>Paul</span></label></div>
        <div><label for="bar_2">
        <input type="radio" id="bar_2" value="G" name="beatle"> <span>George</span></label></div>
        <div><label for="bar_3">
        <input type="radio" id="bar_3" value="R" name="beatle"> <span>Ringo</span></label></div>
        </div>
        """
        self.check_html(
            self.widget(choices=self.beatles),
            "beatle",
            "J",
            attrs={"id": "bar"},
            html=html,
        )

    def test_class_attrs(self):
        """
        The <div> in the multiple_input.html widget template include the class
        attribute.
        """
        html = """
        <div class="bar">
        <div><label>
        <input checked type="radio" class="bar" value="J" name="beatle"> <span>John</span></label>
        </div>
        <div><label>
        <input type="radio" class="bar" value="P" name="beatle"> <span>Paul</span></label></div>
        <div><label>
        <input type="radio" class="bar" value="G" name="beatle"> <span>George</span></label></div>
        <div><label>
        <input type="radio" class="bar" value="R" name="beatle"> <span>Ringo</span></label></div>
        </div>
        """
        self.check_html(
            self.widget(choices=self.beatles),
            "beatle",
            "J",
            attrs={"class": "bar"},
            html=html,
        )

    @override_settings(USE_THOUSAND_SEPARATOR=True)
    def test_doesnt_localize_input_value(self):
        choices = [
            (1, "One"),
            (1000, "One thousand"),
            (1000000, "One million"),
        ]
        html = """
        <div>
        <div><label><input type="radio" name="number" value="1"> <span>One</span></label></div>
        <div><label>
        <input type="radio" name="number" value="1000"> <span>One thousand</span></label></div>
        <div><label>
        <input type="radio" name="number" value="1000000"> <span>One million</span></label></div>
        </div>
        """
        self.check_html(self.widget(choices=choices), "number", None, html=html)

        choices = [
            (datetime.time(0, 0), "midnight"),
            (datetime.time(12, 0), "noon"),
        ]
        html = """
        <div>
        <div><label>
        <input type="radio" name="time" value="00:00:00"> <span>midnight</span></label></div>
        <div><label>
        <input type="radio" name="time" value="12:00:00"> <span>noon</span></label></div>
        </div>
        """
        self.check_html(self.widget(choices=choices), "time", None, html=html)

    def test_render_as_subwidget(self):
        """A RadioSelect as a subwidget of MultiWidget."""
        choices = (("", "------"),) + self.beatles
        self.check_html(
            MultiWidget([self.widget(choices=choices)]),
            "beatle",
            ["J"],
            html="""
            <div>
            <div><label>
            <input type="radio" name="beatle_0" value=""> <span>------</span></label></div>
            <div><label>
            <input checked type="radio" name="beatle_0" value="J"> <span>John</span></label></div>
            <div><label>
            <input type="radio" name="beatle_0" value="P"> <span>Paul</span></label></div>
            <div><label>
            <input type="radio" name="beatle_0" value="G"> <span>George</span></label></div>
            <div><label>
            <input type="radio" name="beatle_0" value="R"> <span>Ringo</span></label></div>
            </div>
        """,
        )

    def test_fieldset(self):
        class TestForm(Form):
            template_name = "forms_tests/use_fieldset.html"
            field = ChoiceField(
                widget=self.widget, choices=self.beatles, required=False
            )

        form = TestForm()
        self.assertIs(self.widget.use_fieldset, True)
        self.assertHTMLEqual(
            '<div><fieldset><legend>Field:</legend><div id="id_field">'
            '<div><label for="id_field_0">'
            '<input type="radio" name="field" value="J" id="id_field_0"> <span>John</span>'
            '</label></div><div><label for="id_field_1">'
            '<input type="radio" name="field" value="P" id="id_field_1"><span>Paul</span>'
            '</label></div><div><label for="id_field_2"><input type="radio" '
            'name="field" value="G" id="id_field_2"> <span>George</span></label></div>'
            '<div><label for="id_field_3"><input type="radio" name="field" '
            'value="R" id="id_field_3"><span>Ringo</span></label></div></div></fieldset>'
            "</div>",
            form.render(),
        )
