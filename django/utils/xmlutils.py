"""
Utilities for XML generation/parsing.
"""

from xml.sax.saxutils import XMLGenerator

from django.utils.regex_helper import _lazy_re_compile

_xml_control_chars_re = _lazy_re_compile(r"[\x00-\x08\x0B-\x0C\x0E-\x1F]")


class UnserializableContentError(ValueError):
    pass


class SimplerXMLGenerator(XMLGenerator):
    def addQuickElement(self, name, contents=None, attrs=None):
        "Convenience method for adding an element with no children"
        if attrs is None:
            attrs = {}
        self.startElement(name, attrs)
        if contents is not None:
            self.characters(contents)
        self.endElement(name)

    def characters(self, content):
        if content and _xml_control_chars_re.search(content):
            # Fail loudly when content has control chars (unsupported in XML
            # 1.0) See https://www.w3.org/International/questions/qa-controls
            raise UnserializableContentError(
                "Control characters are not supported in XML 1.0"
            )
        super().characters(content)

    def startElement(self, name, attrs):
        # Sort attrs for a deterministic output.
        sorted_attrs = dict(sorted(attrs.items())) if attrs else attrs
        super().startElement(name, sorted_attrs)
