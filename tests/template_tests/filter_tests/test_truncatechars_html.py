from django.template.defaultfilters import truncatechars_html
from django.test import SimpleTestCase


class FunctionTests(SimpleTestCase):

    def test_truncate_zero(self):
        self.assertEqual(truncatechars_html('<p>one <a href="#">two - three <br>four</a> five</p>', 0), '…')

    def test_truncate(self):
        self.assertEqual(
            truncatechars_html('<p>one <a href="#">two - three <br>four</a> five</p>', 4),
            '<p>one…</p>',
        )

    def test_truncate2(self):
        self.assertEqual(
            truncatechars_html('<p>one <a href="#">two - three <br>four</a> five</p>', 9),
            '<p>one <a href="#">two …</a></p>',
        )

    def test_truncate3(self):
        self.assertEqual(
            truncatechars_html('<p>one <a href="#">two - three <br>four</a> five</p>', 100),
            '<p>one <a href="#">two - three <br>four</a> five</p>',
        )

    def test_truncate_unicode(self):
        self.assertEqual(truncatechars_html('<b>\xc5ngstr\xf6m</b> was here', 3), '<b>\xc5n…</b>')

    def test_truncate_something(self):
        self.assertEqual(truncatechars_html('a<b>b</b>c', 3), 'a<b>b</b>c')

    def test_invalid_arg(self):
        html = '<p>one <a href="#">two - three <br>four</a> five</p>'
        self.assertEqual(truncatechars_html(html, 'a'), html)
