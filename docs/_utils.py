import tempfile

from sphinx.application import Sphinx


def find_sphinx_sources(srcdir, *, absolute=False):
    # Use a minimal Sphinx app to locate source files per conf.py.
    with tempfile.TemporaryDirectory() as tmpdir:
        app = Sphinx(
            srcdir=srcdir,
            confdir=srcdir,
            outdir=tmpdir,
            doctreedir=tmpdir,
            buildername="dummy",
            # Avoid downloading intersphinx inventories.
            confoverrides={"extensions": []},
            status=None,
        )
        return [
            str(app.project.doc2path(docname, absolute=absolute))
            for docname in app.project.docnames
        ]
