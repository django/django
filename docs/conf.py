# Django documentation build configuration file, created by
# sphinx-quickstart on Thu Mar 27 09:06:53 2008.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# The contents of this file are pickled, so don't put values in the namespace
# that aren't picklable (module imports are okay, they're removed automatically).
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import functools
import sys
from os.path import abspath, dirname, join

# Workaround for sphinx-build recursion limit overflow:
# pickle.dump(doctree, f, pickle.HIGHEST_PROTOCOL)
#  RuntimeError: maximum recursion depth exceeded while pickling an object
#
# Python's default allowed recursion depth is 1000 but this isn't enough for
# building docs/ref/settings.txt sometimes.
# https://groups.google.com/g/sphinx-dev/c/MtRf64eGtv4/discussion
sys.setrecursionlimit(2000)

# Make sure we get the version of this copy of Django
sys.path.insert(1, dirname(dirname(abspath(__file__))))

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.append(abspath(join(dirname(__file__), "_ext")))

# Use the module to GitHub url resolver, but import it after the _ext directoy
# it lives in has been added to sys.path.
import github_links  # NOQA

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
needs_sphinx = "4.5.0"

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = [
    "djangodocs",
    "sphinx.ext.extlinks",
    "sphinx.ext.intersphinx",
    "sphinx.ext.autosectionlabel",
    "sphinx.ext.linkcode",
]

# AutosectionLabel settings.
# Uses a <page>:<label> schema which doesn't work for duplicate sub-section
# labels, so set max depth.
autosectionlabel_prefix_document = True
autosectionlabel_maxdepth = 2

# Linkcheck settings.
linkcheck_ignore = [
    # Special-use addresses and domain names. (RFC 6761/6890)
    r"^https?://(?:127\.0\.0\.1|\[::1\])(?::\d+)?/",
    r"^https?://(?:[^/.]+\.)*example\.(?:com|net|org)(?::\d+)?/",
    r"^https?://(?:[^/.]+\.)*(?:example|invalid|localhost|test)(?::\d+)?/",
    # Pages that are inaccessible because they require authentication.
    r"^https://github\.com/[^/]+/[^/]+/fork",
    r"^https://code\.djangoproject\.com/github/login",
    r"^https://code\.djangoproject\.com/newticket",
    r"^https://(?:code|www)\.djangoproject\.com/admin/",
    r"^https://www\.djangoproject\.com/community/add/blogs/",
    r"^https://www\.google\.com/webmasters/tools/ping",
    r"^https://search\.google\.com/search-console/welcome",
    # Fragments used to dynamically switch content or populate fields.
    r"^https://web\.libera\.chat/#",
    r"^https://github\.com/[^#]+#L\d+-L\d+$",
    r"^https://help\.apple\.com/itc/podcasts_connect/#/itc",
    # Anchors on certain pages with missing a[name] attributes.
    r"^https://tools\.ietf\.org/html/rfc1123\.html#section-",
]

# Spelling check needs an additional module that is not installed by default.
# Add it only if spelling check is requested so docs can be generated without it.
if "spelling" in sys.argv:
    extensions.append("sphinxcontrib.spelling")

# Spelling language.
spelling_lang = "en_US"

# Location of word list.
spelling_word_list_filename = "spelling_wordlist"

spelling_warning = True

# Add any paths that contain templates here, relative to this directory.
# templates_path = []

# The suffix of source filenames.
source_suffix = {".txt": "restructuredtext"}

# The encoding of source files.
# source_encoding = 'utf-8-sig'

# The root toctree document.
root_doc = "contents"

# Disable auto-created table of contents entries for all domain objects (e.g.
# functions, classes, attributes, etc.) in Sphinx 5.2+.
toc_object_entries = False

# General substitutions.
project = "Django"
copyright = "Django Software Foundation and contributors"


# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = "5.2"
# The full version, including alpha/beta/rc tags.
try:
    from django import VERSION, get_version
except ImportError:
    release = version
else:

    def django_release():
        pep440ver = get_version()
        if VERSION[3:5] == ("alpha", 0) and "dev" not in pep440ver:
            return pep440ver + ".dev"
        return pep440ver

    release = django_release()

# The "development version" of Django
django_next_version = "5.2"

extlinks = {
    "bpo": ("https://bugs.python.org/issue?@action=redirect&bpo=%s", "bpo-%s"),
    "commit": ("https://github.com/django/django/commit/%s", "%s"),
    "cve": ("https://nvd.nist.gov/vuln/detail/CVE-%s", "CVE-%s"),
    "pypi": ("https://pypi.org/project/%s/", "%s"),
    # A file or directory. GitHub redirects from blob to tree if needed.
    "source": ("https://github.com/django/django/blob/main/%s", "%s"),
    "ticket": ("https://code.djangoproject.com/ticket/%s", "#%s"),
}

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
# language = None

# Location for .po/.mo translation files used when language is set
locale_dirs = ["locale/"]

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
# today = ''
# Else, today_fmt is used as the format for a strftime call.
today_fmt = "%B %d, %Y"

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ["_build", "_theme", "requirements.txt"]

# The reST default role (used for this markup: `text`) to use for all documents.
default_role = "default-role-error"

# If true, '()' will be appended to :func: etc. cross-reference text.
add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
add_module_names = False

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = "trac"

# Links to Python's docs should reference the most recent version of the 3.x
# branch, which is located at this URL.
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "sphinx": ("https://www.sphinx-doc.org/en/master", None),
    "psycopg": ("https://www.psycopg.org/psycopg3/docs", None),
}

# Python's docs don't change every week.
intersphinx_cache_limit = 90  # days

# The 'versionadded' and 'versionchanged' directives are overridden.
suppress_warnings = ["app.add_directive"]

# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = "djangodocs"

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
# html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
html_theme_path = ["_theme"]

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
# html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
# html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
# html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
# html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
# html_static_path = ["_static"]

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
html_last_updated_fmt = "%b %d, %Y"

# Content template for the index page.
# html_index = ''

# Custom sidebar templates, maps document names to template names.
# html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
html_additional_pages = {}

# If false, no module index is generated.
# html_domain_indices = True

# If false, no index is generated.
# html_use_index = True

# If true, the index is split into individual pages for each letter.
# html_split_index = False

# If true, links to the reST sources are added to the pages.
# html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
# html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
# html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
# html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
# html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = "Djangodoc"

modindex_common_prefix = ["django."]

# Appended to every page
rst_epilog = """
.. |django-users| replace:: :ref:`django-users <django-users-mailing-list>`
.. |django-developers| replace:: :ref:`django-developers <django-developers-mailing-list>`
.. |django-announce| replace:: :ref:`django-announce <django-announce-mailing-list>`
.. |django-updates| replace:: :ref:`django-updates <django-updates-mailing-list>`
"""  # NOQA

# -- Options for LaTeX output --------------------------------------------------

# Use XeLaTeX for Unicode support.
latex_engine = "xelatex"
latex_use_xindy = False
# Set font for CJK and fallbacks for unicode characters.
latex_elements = {
    "fontpkg": r"""
        \setmainfont{Symbola}
    """,
    "preamble": r"""
        \usepackage[UTF8]{ctex}
        \xeCJKDeclareCharClass{HalfLeft}{"2018, "201C}
        \xeCJKDeclareCharClass{HalfRight}{
            "00B7, "2019, "201D, "2013, "2014, "2025, "2026, "2E3A
        }
        \usepackage{newunicodechar}
        \newunicodechar{π}{\ensuremath{\pi}}
        \newunicodechar{≤}{\ensuremath{\le}}
        \newunicodechar{≥}{\ensuremath{\ge}}
        \newunicodechar{♥}{\ensuremath{\heartsuit}}
        \newunicodechar{…}{\ensuremath{\ldots}}
    """,
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, document class [howto/manual]).
# latex_documents = []
latex_documents = [
    (
        "contents",
        "django.tex",
        "Django Documentation",
        "Django Software Foundation",
        "manual",
    ),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
# latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
# latex_use_parts = False

# If true, show page references after internal links.
# latex_show_pagerefs = False

# If true, show URL addresses after external links.
# latex_show_urls = False

# Documents to append as an appendix to all manuals.
# latex_appendices = []

# If false, no module index is generated.
# latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    (
        "ref/django-admin",
        "django-admin",
        "Utility script for the Django web framework",
        ["Django Software Foundation"],
        1,
    )
]


# -- Options for Texinfo output ------------------------------------------------

# List of tuples (startdocname, targetname, title, author, dir_entry,
# description, category, toctree_only)
texinfo_documents = [
    (
        root_doc,
        "django",
        "",
        "",
        "Django",
        "Documentation of the Django framework",
        "Web development",
        False,
    )
]


# -- Options for Epub output ---------------------------------------------------

# Bibliographic Dublin Core info.
epub_title = project
epub_author = "Django Software Foundation"
epub_publisher = "Django Software Foundation"
epub_copyright = copyright

# The basename for the epub file. It defaults to the project name.
# epub_basename = 'Django'

# The HTML theme for the epub output. Since the default themes are not optimized
# for small screen space, using the same theme for HTML and epub output is
# usually not wise. This defaults to 'epub', a theme designed to save visual
# space.
epub_theme = "djangodocs-epub"

# The language of the text. It defaults to the language option
# or en if the language is not set.
# epub_language = ''

# The scheme of the identifier. Typical schemes are ISBN or URL.
# epub_scheme = ''

# The unique identifier of the text. This can be an ISBN number
# or the project homepage.
# epub_identifier = ''

# A unique identification for the text.
# epub_uid = ''

# A tuple containing the cover image and cover page html template filenames.
epub_cover = ("", "epub-cover.html")

# A sequence of (type, uri, title) tuples for the guide element of content.opf.
# epub_guide = ()

# HTML files that should be inserted before the pages created by sphinx.
# The format is a list of tuples containing the path and title.
# epub_pre_files = []

# HTML files that should be inserted after the pages created by sphinx.
# The format is a list of tuples containing the path and title.
# epub_post_files = []

# A list of files that should not be packed into the epub file.
# epub_exclude_files = []

# The depth of the table of contents in toc.ncx.
# epub_tocdepth = 3

# Allow duplicate toc entries.
# epub_tocdup = True

# Choose between 'default' and 'includehidden'.
# epub_tocscope = 'default'

# Fix unsupported image types using the PIL.
# epub_fix_images = False

# Scale large images.
# epub_max_image_width = 0

# How to display URL addresses: 'footnote', 'no', or 'inline'.
# epub_show_urls = 'inline'

# If false, no index is generated.
# epub_use_index = True

linkcode_resolve = functools.partial(
    github_links.github_linkcode_resolve,
    version=version,
    next_version=django_next_version,
)
