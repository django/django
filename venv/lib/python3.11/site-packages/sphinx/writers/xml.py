"""Docutils-native XML and pseudo-XML writers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from docutils.writers.docutils_xml import Writer as BaseXMLWriter

if TYPE_CHECKING:
    from sphinx.builders import Builder


class XMLWriter(BaseXMLWriter):
    output: str

    def __init__(self, builder: Builder) -> None:
        super().__init__()
        self.builder = builder

        # A lambda function to generate translator lazily
        self.translator_class = lambda document: self.builder.create_translator(document)

    def translate(self, *args: Any, **kwargs: Any) -> None:
        self.document.settings.newlines = \
            self.document.settings.indents = \
            self.builder.env.config.xml_pretty
        self.document.settings.xml_declaration = True
        self.document.settings.doctype_declaration = True
        return super().translate()


class PseudoXMLWriter(BaseXMLWriter):

    supported = ('pprint', 'pformat', 'pseudoxml')
    """Formats this writer supports."""

    config_section = 'pseudoxml writer'
    config_section_dependencies = ('writers',)

    output: str
    """Final translated form of `document`."""

    def __init__(self, builder: Builder) -> None:
        super().__init__()
        self.builder = builder

    def translate(self) -> None:
        self.output = self.document.pformat()

    def supports(self, format: str) -> bool:
        """This writer supports all format-specific elements."""
        return True
