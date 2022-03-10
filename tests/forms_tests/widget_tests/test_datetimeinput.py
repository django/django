from datetime import datetime

from django.forms import DateTimeInput
from django.test import ignore_warnings
from django.utils import translation
from django.utils.deprecation import RemovedInDjango50Warning

from .base import WidgetTest


class DateTimeInputTest(WidgetTest):
    widget = DateTimeInput()

    def test_render_none(self):
        self.check_html(self.widget, "date", None, '<input type="text" name="date">')

    def test_render_value(self):
        """
        The microseconds are trimmed on display, by default.
        """
        d = datetime(2007, 9, 17, 12, 51, 34, 482548)
        self.assertEqual(str(d), "2007-09-17 12:51:34.482548")
        self.check_html(
            self.widget,
            "date",
            d,
            html=('<input type="text" name="date" value="2007-09-17 12:51:34">'),
        )
        self.check_html(
            self.widget,
            "date",
            datetime(2007, 9, 17, 12, 51, 34),
            html=('<input type="text" name="date" value="2007-09-17 12:51:34">'),
        )
        self.check_html(
            self.widget,
            "date",
            datetime(2007, 9, 17, 12, 51),
            html=('<input type="text" name="date" value="2007-09-17 12:51:00">'),
        )

    def test_render_formatted(self):
        """
        Use 'format' to change the way a value is displayed.
        """
        widget = DateTimeInput(
            format="%d/%m/%Y %H:%M",
            attrs={"type": "datetime"},
        )
        d = datetime(2007, 9, 17, 12, 51, 34, 482548)
        self.check_html(
            widget,
            "date",
            d,
            html='<input type="datetime" name="date" value="17/09/2007 12:51">',
        )

    @translation.override("de-at")
    def test_l10n(self):
        d = datetime(2007, 9, 17, 12, 51, 34, 482548)
        self.check_html(
            self.widget,
            "date",
            d,
            html=('<input type="text" name="date" value="17.09.2007 12:51:34">'),
        )

    @translation.override("de-at")
    def test_locale_aware(self):
        d = datetime(2007, 9, 17, 12, 51, 34, 482548)
        # RemovedInDjango50Warning: When the deprecation ends, remove
        # @ignore_warnings and USE_L10N=False. The assertion should remain
        # because format-related settings will take precedence over
        # locale-dictated formats.
        with ignore_warnings(category=RemovedInDjango50Warning):
            with self.settings(USE_L10N=False):
                with self.settings(
                    DATETIME_INPUT_FORMATS=[
                        "%Y-%m-%d %H:%M:%S",
                        "%Y-%m-%d %H:%M:%S.%f",
                        "%Y-%m-%d %H:%M",
                    ]
                ):
                    self.check_html(
                        self.widget,
                        "date",
                        d,
                        html=(
                            '<input type="text" name="date" '
                            'value="2007-09-17 12:51:34">'
                        ),
                    )
        with translation.override("es"):
            self.check_html(
                self.widget,
                "date",
                d,
                html='<input type="text" name="date" value="17/09/2007 12:51:34">',
            )
