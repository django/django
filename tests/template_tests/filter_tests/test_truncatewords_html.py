from django.template.defaultfilters import truncatewords_html
from django.test import SimpleTestCase


class FunctionTests(SimpleTestCase):

    def test_truncate_zero(self):
        self.assertEqual(truncatewords_html('<p>one <a href="#">two - three <br>four</a> five</p>', 0), '')

    def test_truncate(self):
        self.assertEqual(
            truncatewords_html('<p>one <a href="#">two - three <br>four</a> five</p>', 2),
            '<p>one <a href="#">two …</a></p>',
        )

    def test_truncate2(self):
        self.assertEqual(
            truncatewords_html('<p>one <a href="#">two - three <br>four</a> five</p>', 4),
            '<p>one <a href="#">two - three …</a></p>',
        )

    def test_truncate3(self):
        self.assertEqual(
            truncatewords_html('<p>one <a href="#">two - three <br>four</a> five</p>', 5),
            '<p>one <a href="#">two - three <br>four …</a></p>',
        )

    def test_truncate4(self):
        self.assertEqual(
            truncatewords_html('<p>one <a href="#">two - three <br>four</a> five</p>', 100),
            '<p>one <a href="#">two - three <br>four</a> five</p>',
        )

    def test_truncate_unicode(self):
        self.assertEqual(truncatewords_html('\xc5ngstr\xf6m was here', 1), '\xc5ngstr\xf6m …')

    def test_truncate_complex(self):
        self.assertEqual(
            truncatewords_html('<i>Buenos d&iacute;as! &#x00bf;C&oacute;mo est&aacute;?</i>', 3),
            '<i>Buenos d&iacute;as! &#x00bf;C&oacute;mo …</i>',
        )

    def test_invalid_arg(self):
        self.assertEqual(truncatewords_html('<p>string</p>', 'a'), '<p>string</p>')
