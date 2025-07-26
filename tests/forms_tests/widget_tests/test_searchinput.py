from django.forms import SearchInput

from .base import WidgetTest


class SearchInputTest(WidgetTest):
    widget = SearchInput()

    def test_render(self):
        self.check_html(
            self.widget, "search", "", html='<input type="search" name="search">'
        )
