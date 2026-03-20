from django.forms import SearchInput

from .base import WidgetTest


class SearchInputTest(WidgetTest):
    widget = SearchInput()

    def test_render(self):
        self.check_html(
            self.widget, "search", "", html='<input type="search" name="search">'
        )

    def test_render_with_value(self):
        self.check_html(
            self.widget,
            "search",
            "django",
            html='<input type="search" name="search" value="django">',
        )

    def test_render_with_attrs(self):
        self.check_html(
            self.widget,
            "search",
            "",
            attrs={"placeholder": "Search...", "id": "search-box"},
            html=(
                '<input type="search" name="search" '
                'id="search-box" placeholder="Search...">'
            ),
        )

    def test_value_from_datadict(self):
        data = {"search": "query"}
        result = self.widget.value_from_datadict(data, {}, "search")
        self.assertEqual(result, "query")
