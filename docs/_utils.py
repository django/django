import tempfile

from sphinx.application import Sphinx


def find_sphinx_sources(srcdir):
    # Use a minimal Sphinx app to locate source files per conf.py.
    with tempfile.TemporaryDirectory() as tmpdir:
        app = Sphinx(
            srcdir=srcdir,
            confdir=srcdir,
            outdir=tmpdir,
            doctreedir=tmpdir,
            buildername="dummy",
            # Disable extensions: none of them affect source discovery, and
            # loading them would download intersphinx inventories.
            confoverrides={"extensions": []},
            status=None,
        )
        return [
            str(app.project.doc2path(docname, absolute=True))
            for docname in app.project.docnames
        ]
