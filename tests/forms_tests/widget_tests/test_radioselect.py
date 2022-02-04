import datetime

from django.forms import MultiWidget, RadioSelect
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
            <div><label><input type="radio" name="beatle" value=""> ------</label></div>
            <div><label>
            <input checked type="radio" name="beatle" value="J"> John</label></div>
            <div><label><input type="radio" name="beatle" value="P"> Paul</label></div>
            <div><label>
            <input type="radio" name="beatle" value="G"> George</label></div>
            <div><label><input type="radio" name="beatle" value="R"> Ringo</label></div>
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
        <input type="radio" name="nestchoice" value="unknown" id="media_0"> Unknown
        </label></div>
        <div>
        <label>Audio</label>
        <div>
        <label for="media_1_0">
        <input type="radio" name="nestchoice" value="vinyl" id="media_1_0"> Vinyl
        </label></div>
        <div> <label for="media_1_1">
        <input type="radio" name="nestchoice" value="cd" id="media_1_1"> CD
        </label></div>
        </div><div>
        <label>Video</label>
        <div>
        <label for="media_2_0">
        <input type="radio" name="nestchoice" value="vhs" id="media_2_0"> VHS
        </label></div>
        <div>
        <label for="media_2_1">
        <input type="radio" name="nestchoice" value="dvd" id="media_2_1" checked> DVD
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
        <input checked type="radio" id="foo_0" value="J" name="beatle"> John</label>
        </div>
        <div><label for="foo_1">
        <input type="radio" id="foo_1" value="P" name="beatle"> Paul</label></div>
        <div><label for="foo_2">
        <input type="radio" id="foo_2" value="G" name="beatle"> George</label></div>
        <div><label for="foo_3">
        <input type="radio" id="foo_3" value="R" name="beatle"> Ringo</label></div>
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
        <input checked type="radio" id="bar_0" value="J" name="beatle"> John</label>
        </div>
        <div><label for="bar_1">
        <input type="radio" id="bar_1" value="P" name="beatle"> Paul</label></div>
        <div><label for="bar_2">
        <input type="radio" id="bar_2" value="G" name="beatle"> George</label></div>
        <div><label for="bar_3">
        <input type="radio" id="bar_3" value="R" name="beatle"> Ringo</label></div>
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
        <input checked type="radio" class="bar" value="J" name="beatle"> John</label>
        </div>
        <div><label>
        <input type="radio" class="bar" value="P" name="beatle"> Paul</label></div>
        <div><label>
        <input type="radio" class="bar" value="G" name="beatle"> George</label></div>
        <div><label>
        <input type="radio" class="bar" value="R" name="beatle"> Ringo</label></div>
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
        <div><label><input type="radio" name="number" value="1"> One</label></div>
        <div><label>
        <input type="radio" name="number" value="1000"> One thousand</label></div>
        <div><label>
        <input type="radio" name="number" value="1000000"> One million</label></div>
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
        <input type="radio" name="time" value="00:00:00"> midnight</label></div>
        <div><label>
        <input type="radio" name="time" value="12:00:00"> noon</label></div>
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
            <input type="radio" name="beatle_0" value=""> ------</label></div>
            <div><label>
            <input checked type="radio" name="beatle_0" value="J"> John</label></div>
            <div><label>
            <input type="radio" name="beatle_0" value="P"> Paul</label></div>
            <div><label>
            <input type="radio" name="beatle_0" value="G"> George</label></div>
            <div><label>
            <input type="radio" name="beatle_0" value="R"> Ringo</label></div>
            </div>
        """,
        )
