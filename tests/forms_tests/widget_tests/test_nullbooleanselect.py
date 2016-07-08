from django.forms import NullBooleanSelect
from django.test import override_settings
from django.utils import translation

from .base import WidgetTest


class NullBooleanSelectTest(WidgetTest):
    widget = NullBooleanSelect()

    def test_render_true(self):
        self.check_html(self.widget, 'is_cool', True, html=(
            """<select name="is_cool">
            <option value="1">Unknown</option>
            <option value="2" selected="selected">Yes</option>
            <option value="3">No</option>
            </select>"""
        ))

    def test_render_false(self):
        self.check_html(self.widget, 'is_cool', False, html=(
            """<select name="is_cool">
            <option value="1">Unknown</option>
            <option value="2">Yes</option>
            <option value="3" selected="selected">No</option>
            </select>"""
        ))

    def test_render_none(self):
        self.check_html(self.widget, 'is_cool', None, html=(
            """<select name="is_cool">
            <option value="1" selected="selected">Unknown</option>
            <option value="2">Yes</option>
            <option value="3">No</option>
            </select>"""
        ))

    def test_render_value(self):
        self.check_html(self.widget, 'is_cool', '2', html=(
            """<select name="is_cool">
            <option value="1">Unknown</option>
            <option value="2" selected="selected">Yes</option>
            <option value="3">No</option>
            </select>"""
        ))

    @override_settings(USE_L10N=True)
    def test_l10n(self):
        """
        Ensure that the NullBooleanSelect widget's options are lazily
        localized (#17190).
        """
        widget = NullBooleanSelect()

        with translation.override('de-at'):
            self.check_html(widget, 'id_bool', True, html=(
                """
                <select name="id_bool">
                    <option value="1">Unbekannt</option>
                    <option value="2" selected="selected">Ja</option>
                    <option value="3">Nein</option>
                </select>
                """
            ))
