from os import path

from docutils import nodes
from docutils.core import publish_doctree

from sphinx.application import Sphinx
from sphinx.io import SphinxStandaloneReader
from sphinx.parsers import RSTParser
from sphinx.util.docutils import sphinx_domains


def parse(app: Sphinx, text: str, docname: str = 'index') -> nodes.document:
    """Parse a string as reStructuredText with Sphinx application."""
    try:
        app.env.temp_data['docname'] = docname
        reader = SphinxStandaloneReader()
        reader.setup(app)
        parser = RSTParser()
        parser.set_application(app)
        with sphinx_domains(app.env):
            return publish_doctree(
                text,
                path.join(app.srcdir, docname + '.rst'),
                reader=reader,
                parser=parser,
                settings_overrides={
                    'env': app.env,
                    'gettext_compact': True,
                    'input_encoding': 'utf-8',
                    'output_encoding': 'unicode',
                    'traceback': True,
                },
            )
    finally:
        app.env.temp_data.pop('docname', None)
