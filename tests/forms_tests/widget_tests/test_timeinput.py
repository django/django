from datetime import time

from django.forms import TimeInput
from django.utils import translation

from .base import WidgetTest


class TimeInputTest(WidgetTest):
    widget = TimeInput()

    def test_render_none(self):
        self.check_html(
            self.widget, "time", None, html='<input type="text" name="time">'
        )

    def test_render_value(self):
        """
        The microseconds are trimmed on display, by default.
        """
        t = time(12, 51, 34, 482548)
        self.assertEqual(str(t), "12:51:34.482548")
        self.check_html(
            self.widget,
            "time",
            t,
            html='<input type="text" name="time" value="12:51:34">',
        )
        self.check_html(
            self.widget,
            "time",
            time(12, 51, 34),
            html=('<input type="text" name="time" value="12:51:34">'),
        )
        self.check_html(
            self.widget,
            "time",
            time(12, 51),
            html=('<input type="text" name="time" value="12:51:00">'),
        )

    def test_string(self):
        """Initializing from a string value."""
        self.check_html(
            self.widget,
            "time",
            "13:12:11",
            html=('<input type="text" name="time" value="13:12:11">'),
        )

    def test_format(self):
        """
        Use 'format' to change the way a value is displayed.
        """
        t = time(12, 51, 34, 482548)
        widget = TimeInput(format="%H:%M", attrs={"type": "time"})
        self.check_html(
            widget, "time", t, html='<input type="time" name="time" value="12:51">'
        )

    @translation.override("de-at")
    def test_l10n(self):
        t = time(12, 51, 34, 482548)
        self.check_html(
            self.widget,
            "time",
            t,
            html='<input type="text" name="time" value="12:51:34">',
        )
