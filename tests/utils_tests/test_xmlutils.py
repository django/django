from io import StringIO

from django.test import SimpleTestCase
from django.utils.xmlutils import SimplerXMLGenerator, UnserializableContentError


class SimplerXMLGeneratorTests(SimpleTestCase):
    def _generate(self, callback):
        stream = StringIO()
        gen = SimplerXMLGenerator(stream, "utf-8")
        gen.startDocument()
        callback(gen)
        gen.endDocument()
        return stream.getvalue()

    def test_add_quick_element_with_content(self):
        output = self._generate(lambda g: g.addQuickElement("title", "Hello World"))
        self.assertIn("<title>Hello World</title>", output)

    def test_add_quick_element_no_content(self):
        output = self._generate(lambda g: g.addQuickElement("br"))
        self.assertIn("<br>", output)
        self.assertIn("</br>", output)

    def test_add_quick_element_with_attrs(self):
        output = self._generate(
            lambda g: g.addQuickElement("link", attrs={"rel": "self", "href": "/feed"})
        )
        self.assertIn('href="/feed"', output)
        self.assertIn('rel="self"', output)

    def test_add_quick_element_attrs_sorted(self):
        output = self._generate(
            lambda g: g.addQuickElement(
                "item", attrs={"z_attr": "last", "a_attr": "first"}
            )
        )
        a_pos = output.index("a_attr")
        z_pos = output.index("z_attr")
        self.assertLess(a_pos, z_pos)

    def test_characters_valid_text(self):
        output = self._generate(
            lambda g: (
                g.startElement("p", {}),
                g.characters("Normal text & <entities>"),
                g.endElement("p"),
            )
        )
        self.assertIn("Normal text &amp; &lt;entities&gt;", output)

    def test_characters_control_chars_raise(self):
        gen = SimplerXMLGenerator(StringIO(), "utf-8")
        gen.startDocument()
        gen.startElement("p", {})
        with self.assertRaises(UnserializableContentError):
            gen.characters("bad\x00content")

    def test_characters_tab_and_newline_allowed(self):
        output = self._generate(
            lambda g: (
                g.startElement("p", {}),
                g.characters("line\ttab\nnewline"),
                g.endElement("p"),
            )
        )
        self.assertIn("line\ttab\nnewline", output)

    def test_characters_various_control_chars(self):
        control_chars = [
            "\x01",
            "\x02",
            "\x08",
            "\x0b",
            "\x0c",
            "\x0e",
            "\x1f",
        ]
        gen = SimplerXMLGenerator(StringIO(), "utf-8")
        gen.startDocument()
        gen.startElement("p", {})
        for char in control_chars:
            with self.subTest(char=repr(char)):
                with self.assertRaises(UnserializableContentError):
                    gen.characters(f"text{char}here")

    def test_characters_empty_string(self):
        output = self._generate(
            lambda g: (
                g.startElement("p", {}),
                g.characters(""),
                g.endElement("p"),
            )
        )
        self.assertIn("<p>", output)

    def test_characters_none_does_not_raise(self):
        output = self._generate(
            lambda g: (
                g.startElement("p", {}),
                g.characters(None),
                g.endElement("p"),
            )
        )
        self.assertIn("<p>", output)

    def test_start_element_attrs_sorted(self):
        stream = StringIO()
        gen = SimplerXMLGenerator(stream, "utf-8")
        gen.startDocument()
        gen.startElement("root", {"zebra": "1", "alpha": "2", "middle": "3"})
        gen.endElement("root")
        gen.endDocument()
        output = stream.getvalue()
        alpha_pos = output.index("alpha")
        middle_pos = output.index("middle")
        zebra_pos = output.index("zebra")
        self.assertLess(alpha_pos, middle_pos)
        self.assertLess(middle_pos, zebra_pos)

    def test_start_element_empty_attrs(self):
        output = self._generate(
            lambda g: (g.startElement("empty", {}), g.endElement("empty"))
        )
        self.assertIn("<empty>", output)


class UnserializableContentErrorTests(SimpleTestCase):
    def test_is_value_error_subclass(self):
        self.assertTrue(issubclass(UnserializableContentError, ValueError))

    def test_message(self):
        err = UnserializableContentError("test message")
        self.assertEqual(str(err), "test message")
