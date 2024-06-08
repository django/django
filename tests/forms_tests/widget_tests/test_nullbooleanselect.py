from django.forms import Form, NullBooleanField, NullBooleanSelect
from django.utils import translation

from .base import WidgetTest


class NullBooleanSelectTest(WidgetTest):
    widget = NullBooleanSelect()

    def test_render_true(self):
        self.check_html(
            self.widget,
            "is_cool",
            True,
            html=(
                """<select name="is_cool">
            <option value="unknown">Unknown</option>
            <option value="true" selected>Yes</option>
            <option value="false">No</option>
            </select>"""
            ),
        )

    def test_render_false(self):
        self.check_html(
            self.widget,
            "is_cool",
            False,
            html=(
                """<select name="is_cool">
            <option value="unknown">Unknown</option>
            <option value="true">Yes</option>
            <option value="false" selected>No</option>
            </select>"""
            ),
        )

    def test_render_none(self):
        self.check_html(
            self.widget,
            "is_cool",
            None,
            html=(
                """<select name="is_cool">
            <option value="unknown" selected>Unknown</option>
            <option value="true">Yes</option>
            <option value="false">No</option>
            </select>"""
            ),
        )

    def test_render_value_unknown(self):
        self.check_html(
            self.widget,
            "is_cool",
            "unknown",
            html=(
                """<select name="is_cool">
            <option value="unknown" selected>Unknown</option>
            <option value="true">Yes</option>
            <option value="false">No</option>
            </select>"""
            ),
        )

    def test_render_value_true(self):
        self.check_html(
            self.widget,
            "is_cool",
            "true",
            html=(
                """<select name="is_cool">
            <option value="unknown">Unknown</option>
            <option value="true" selected>Yes</option>
            <option value="false">No</option>
            </select>"""
            ),
        )

    def test_render_value_false(self):
        self.check_html(
            self.widget,
            "is_cool",
            "false",
            html=(
                """<select name="is_cool">
            <option value="unknown">Unknown</option>
            <option value="true">Yes</option>
            <option value="false" selected>No</option>
            </select>"""
            ),
        )

    def test_render_value_1(self):
        self.check_html(
            self.widget,
            "is_cool",
            "1",
            html=(
                """<select name="is_cool">
            <option value="unknown" selected>Unknown</option>
            <option value="true">Yes</option>
            <option value="false">No</option>
            </select>"""
            ),
        )

    def test_render_value_2(self):
        self.check_html(
            self.widget,
            "is_cool",
            "2",
            html=(
                """<select name="is_cool">
            <option value="unknown">Unknown</option>
            <option value="true" selected>Yes</option>
            <option value="false">No</option>
            </select>"""
            ),
        )

    def test_render_value_3(self):
        self.check_html(
            self.widget,
            "is_cool",
            "3",
            html=(
                """<select name="is_cool">
            <option value="unknown">Unknown</option>
            <option value="true">Yes</option>
            <option value="false" selected>No</option>
            </select>"""
            ),
        )

    def test_l10n(self):
        """
        The NullBooleanSelect widget's options are lazily localized (#17190).
        """
        widget = NullBooleanSelect()

        with translation.override("de-at"):
            self.check_html(
                widget,
                "id_bool",
                True,
                html=(
                    """
                <select name="id_bool">
                    <option value="unknown">Unbekannt</option>
                    <option value="true" selected>Ja</option>
                    <option value="false">Nein</option>
                </select>
                """
                ),
            )

    def test_fieldset(self):
        class TestForm(Form):
            template_name = "forms_tests/use_fieldset.html"
            field = NullBooleanField(widget=self.widget)

        form = TestForm()
        self.assertIs(self.widget.use_fieldset, False)
        self.assertHTMLEqual(
            '<div><label for="id_field">Field:</label>'
            '<select name="field" id="id_field">'
            '<option value="unknown" selected>Unknown</option>'
            '<option value="true">Yes</option>'
            '<option value="false">No</option></select></div>',
            form.render(),
        )
