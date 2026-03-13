from django.template.defaultfilters import truncated_unordered_list
from django.test import SimpleTestCase


class TruncatedUnorderedListTests(SimpleTestCase):
    def test_no_max_items(self):
        self.assertEqual(
            truncated_unordered_list(["item 1", "item 2"], None),
            "\t<li>item 1</li>\n\t<li>item 2</li>",
        )

    def test_invalid_max_items_value(self):
        self.assertEqual(
            truncated_unordered_list(["item 1", "item 2"], "invalid_int"),
            "\t<li>item 1</li>\n\t<li>item 2</li>",
        )

    def test_max_items_zero(self):
        self.assertEqual(
            truncated_unordered_list(["a", "b", "c"], 0),
            '\t<li class="quiet">\u2026and 3 more.</li>',
        )

    def test_flat_list_truncated(self):
        self.assertEqual(
            truncated_unordered_list(["a", "b", "c", "d", "e"], 3),
            "\t<li>a</li>\n\t<li>b</li>\n\t<li>c</li>\n"
            '\t<li class="quiet">\u2026and 2 more.</li>',
        )

    def test_nested_two_levels_truncated(self):
        self.assertEqual(
            truncated_unordered_list(["a", ["a1", "a2"], "b", "c", "d", "e"], 3),
            "\t<li>a\n\t<ul>\n\t\t<li>a1</li>\n\t\t<li>a2</li>\n\t</ul>\n\t</li>\n"
            "\t<li>b</li>\n\t<li>c</li>\n"
            '\t<li class="quiet">\u2026and 2 more.</li>',
        )

    def test_nested_and_top_level_truncated(self):
        self.assertEqual(
            truncated_unordered_list(
                ["a", ["n1", "n2", "n3", "n4", "n5"], "b", "c", "d", "e"],
                3,
            ),
            "\t<li>a\n\t<ul>\n\t\t<li>n1</li>\n\t\t<li>n2</li>\n\t\t<li>n3</li>\n"
            '\t\t<li class="quiet">\u2026and 2 more.</li>\n\t</ul>\n\t</li>\n'
            "\t<li>b</li>\n\t<li>c</li>\n"
            '\t<li class="quiet">\u2026and 2 more.</li>',
        )

    def test_nested_three_levels_truncated(self):
        self.assertEqual(
            truncated_unordered_list(["a", ["a1", ["a1x"]], "b", "c", "d", "e"], 3),
            "\t<li>a\n\t<ul>\n\t\t<li>a1\n\t\t<ul>\n\t\t\t<li>a1x</li>\n"
            "\t\t</ul>\n\t\t</li>\n\t</ul>\n\t</li>\n"
            "\t<li>b</li>\n\t<li>c</li>\n"
            '\t<li class="quiet">\u2026and 2 more.</li>',
        )

    def test_max_items_equal_to_length(self):
        self.assertEqual(
            truncated_unordered_list(["a", "b", "c"], 3),
            "\t<li>a</li>\n\t<li>b</li>\n\t<li>c</li>",
        )

    def test_max_items_greater_than_length(self):
        self.assertEqual(
            truncated_unordered_list(["a", "b"], 10),
            "\t<li>a</li>\n\t<li>b</li>",
        )

    def test_truncated_single_remaining(self):
        self.assertEqual(
            truncated_unordered_list(["a", "b", "c"], 2),
            "\t<li>a</li>\n\t<li>b</li>\n" '\t<li class="quiet">\u2026and 1 more.</li>',
        )

    def test_autoescape(self):
        self.assertEqual(
            truncated_unordered_list(["<a>item</a>", "safe"], 1),
            "\t<li>&lt;a&gt;item&lt;/a&gt;</li>\n"
            '\t<li class="quiet">\u2026and 1 more.</li>',
        )

    def test_autoescape_off(self):
        self.assertEqual(
            truncated_unordered_list(["<a>item</a>", "safe"], 1, autoescape=False),
            "\t<li><a>item</a></li>\n" '\t<li class="quiet">\u2026and 1 more.</li>',
        )

    def test_empty_list(self):
        self.assertEqual(truncated_unordered_list([], 5), "")
