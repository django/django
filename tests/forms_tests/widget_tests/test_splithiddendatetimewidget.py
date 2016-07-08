from datetime import datetime

from django.forms import SplitHiddenDateTimeWidget
from django.test import override_settings
from django.utils import translation

from .base import WidgetTest


class SplitHiddenDateTimeWidgetTest(WidgetTest):
    widget = SplitHiddenDateTimeWidget()

    def test_render_empty(self):
        self.check_html(self.widget, 'date', '', html=(
            '<input type="hidden" name="date_0" /><input type="hidden" name="date_1" />'
        ))

    def test_render_value(self):
        d = datetime(2007, 9, 17, 12, 51, 34, 482548)
        self.check_html(self.widget, 'date', d, html=(
            '<input type="hidden" name="date_0" value="2007-09-17" />'
            '<input type="hidden" name="date_1" value="12:51:34" />'
        ))
        self.check_html(self.widget, 'date', datetime(2007, 9, 17, 12, 51, 34), html=(
            '<input type="hidden" name="date_0" value="2007-09-17" />'
            '<input type="hidden" name="date_1" value="12:51:34" />'
        ))
        self.check_html(self.widget, 'date', datetime(2007, 9, 17, 12, 51), html=(
            '<input type="hidden" name="date_0" value="2007-09-17" />'
            '<input type="hidden" name="date_1" value="12:51:00" />'
        ))

    @override_settings(USE_L10N=True)
    @translation.override('de-at')
    def test_l10n(self):
        d = datetime(2007, 9, 17, 12, 51)
        self.check_html(self.widget, 'date', d, html=(
            """
            <input type="hidden" name="date_0" value="17.09.2007" />
            <input type="hidden" name="date_1" value="12:51:00" />
            """
        ))
