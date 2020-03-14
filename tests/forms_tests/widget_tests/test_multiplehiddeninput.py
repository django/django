from django.forms import MultipleHiddenInput

from .base import WidgetTest


class MultipleHiddenInputTest(WidgetTest):
    widget = MultipleHiddenInput()
    no_unique_names = MultipleHiddenInput(unique_names=False)

    def test_render_single(self):
        self.check_html(
            self.widget, 'email', ['test@example.com'],
            html='<input type="hidden" name="email_0" value="test@example.com">',
        )

    def test_render_multiple(self):
        self.check_html(
            self.widget, 'email', ['test@example.com', 'foo@example.com'],
            html=(
                '<input type="hidden" name="email_0" value="test@example.com">\n'
                '<input type="hidden" name="email_1" value="foo@example.com">'
            ),
        )

    def test_render_attrs(self):
        self.check_html(
            self.widget, 'email', ['test@example.com'], attrs={'class': 'fun'},
            html='<input type="hidden" name="email_0" value="test@example.com" class="fun">',
        )

    def test_render_attrs_multiple(self):
        self.check_html(
            self.widget, 'email', ['test@example.com', 'foo@example.com'], attrs={'class': 'fun'},
            html=(
                '<input type="hidden" name="email_0" value="test@example.com" class="fun">\n'
                '<input type="hidden" name="email_1" value="foo@example.com" class="fun">'
            ),
        )

    def test_render_attrs_constructor(self):
        widget = MultipleHiddenInput(attrs={'class': 'fun'})
        self.check_html(widget, 'email', [], '')
        self.check_html(
            widget, 'email', ['foo@example.com'],
            html='<input type="hidden" class="fun" value="foo@example.com" name="email_0">',
        )
        self.check_html(
            widget, 'email', ['foo@example.com', 'test@example.com'],
            html=(
                '<input type="hidden" class="fun" value="foo@example.com" name="email_0">\n'
                '<input type="hidden" class="fun" value="test@example.com" name="email_1">'
            ),
        )
        self.check_html(
            widget, 'email', ['foo@example.com'], attrs={'class': 'special'},
            html='<input type="hidden" class="special" value="foo@example.com" name="email_0">',
        )

    def test_render_empty(self):
        self.check_html(self.widget, 'email', [], '')

    def test_render_none(self):
        self.check_html(self.widget, 'email', None, '')

    def test_render_increment_id(self):
        """
        Each input should get a separate ID.
        """
        self.check_html(
            self.widget, 'letters', ['a', 'b', 'c'], attrs={'id': 'hideme'},
            html=(
                '<input type="hidden" name="letters_0" value="a" id="hideme_0">\n'
                '<input type="hidden" name="letters_1" value="b" id="hideme_1">\n'
                '<input type="hidden" name="letters_2" value="c" id="hideme_2">'
            ),
        )

    def test_unique_names_single(self):
        self.check_html(
            self.no_unique_names, 'email', ['test@example.com'],
            html='<input type="hidden" name="email" value="test@example.com">',
        )

    def test_unique_names_multiple(self):
        self.check_html(
            self.no_unique_names, 'email', ['test@example.com', 'foo@example.com'],
            html=(
                '<input type="hidden" name="email" value="test@example.com">\n'
                '<input type="hidden" name="email" value="foo@example.com">'
            ),
        )

    def test_unique_names_render_attrs(self):
        self.check_html(
            self.no_unique_names, 'email', ['test@example.com'], attrs={'class': 'fun'},
            html='<input type="hidden" name="email" value="test@example.com" class="fun">',
        )
