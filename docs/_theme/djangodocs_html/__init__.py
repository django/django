# Setup code for the djangodocs_html Sphinx theme. (Not to be confused with
# the djangodocs Sphinx extension in _ext/djangodocs.py.) This theme must also
# be listed in conf.py extensions so that Sphinx calls the setup() function.

import os


def patch_suppress_sidebar_toctree(
    app, pagename, templatename, context, doctree
) -> None:
    # Django shows a full toctree in the primary sidebar on _all_ pages.
    # pydata-sphinx-theme base templates decide whether to hide the "Collapse
    # Sidebar" button based on logic in context.suppress_sidebar_toctree,
    # which is not accurate with Django's nav. Override it to never suppress
    # the collapse button. (See pydata_sphinx_theme/toctree.py.)
    if app.builder.name == "epub":
        return

    if "suppress_sidebar_toctree" not in context:
        raise RuntimeError(
            "djangodocs_html was connected before pydata-sphinx-theme or is "
            "incompatible with this version of the theme."
        )

    def suppress_sidebar_toctree(startdepth=1, **kwargs):
        return False

    context["suppress_sidebar_toctree"] = suppress_sidebar_toctree


def setup(app):
    if app.config.html_theme == "djangodocs_html":
        # This must be connected at a late (high number) priority so it runs
        # after pydata-sphinx-theme's context generation.
        app.connect("html-page-context", patch_suppress_sidebar_toctree, priority=900)

        if os.environ.get("READTHEDOCS_VERSION_TYPE") == "external":
            # Adjust layout for Read the Docs PR preview builds.
            app.add_css_file("pr-preview.css")

    return {
        "version": "0.1",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
