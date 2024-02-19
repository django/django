"""docutils writers handling Sphinx' custom nodes."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from docutils.writers.html4css1 import Writer

from sphinx.util import logging
from sphinx.writers.html5 import HTML5Translator

if TYPE_CHECKING:
    from sphinx.builders.html import StandaloneHTMLBuilder


logger = logging.getLogger(__name__)
HTMLTranslator = HTML5Translator

# A good overview of the purpose behind these classes can be found here:
# http://www.arnebrodowski.de/blog/write-your-own-restructuredtext-writer.html


class HTMLWriter(Writer):

    # override embed-stylesheet default value to False.
    settings_default_overrides = {"embed_stylesheet": False}

    def __init__(self, builder: StandaloneHTMLBuilder) -> None:
        super().__init__()
        self.builder = builder

    def translate(self) -> None:
        # sadly, this is mostly copied from parent class
        visitor = self.builder.create_translator(self.document, self.builder)
        self.visitor = cast(HTML5Translator, visitor)
        self.document.walkabout(visitor)
        self.output = self.visitor.astext()
        for attr in ('head_prefix', 'stylesheet', 'head', 'body_prefix',
                     'body_pre_docinfo', 'docinfo', 'body', 'fragment',
                     'body_suffix', 'meta', 'title', 'subtitle', 'header',
                     'footer', 'html_prolog', 'html_head', 'html_title',
                     'html_subtitle', 'html_body'):
            setattr(self, attr, getattr(visitor, attr, None))
        self.clean_meta = ''.join(self.visitor.meta[2:])
