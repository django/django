# $Id: __init__.py 7720 2013-09-05 12:54:56Z milde $
# Authors: Chris Liechti <cliechti@gmx.net>;
#          David Goodger <goodger@python.org>
# Copyright: This module has been placed in the public domain.

"""
S5/HTML Slideshow Writer.
"""

__docformat__ = 'reStructuredText'


import sys
import os
import re
import docutils
from docutils import frontend, nodes, utils
from docutils.writers import html4css1
from docutils.parsers.rst import directives
from docutils._compat import b

themes_dir_path = utils.relative_path(
    os.path.join(os.getcwd(), 'dummy'),
    os.path.join(os.path.dirname(__file__), 'themes'))

def find_theme(name):
    # Where else to look for a theme?
    # Check working dir?  Destination dir?  Config dir?  Plugins dir?
    path = os.path.join(themes_dir_path, name)
    if not os.path.isdir(path):
        raise docutils.ApplicationError(
            'Theme directory not found: %r (path: %r)' % (name, path))
    return path


class Writer(html4css1.Writer):

    settings_spec = html4css1.Writer.settings_spec + (
        'S5 Slideshow Specific Options',
        'For the S5/HTML writer, the --no-toc-backlinks option '
        '(defined in General Docutils Options above) is the default, '
        'and should not be changed.',
        (('Specify an installed S5 theme by name.  Overrides --theme-url.  '
          'The default theme name is "default".  The theme files will be '
          'copied into a "ui/<theme>" directory, in the same directory as the '
          'destination file (output HTML).  Note that existing theme files '
          'will not be overwritten (unless --overwrite-theme-files is used).',
          ['--theme'],
          {'default': 'default', 'metavar': '<name>',
           'overrides': 'theme_url'}),
         ('Specify an S5 theme URL.  The destination file (output HTML) will '
          'link to this theme; nothing will be copied.  Overrides --theme.',
          ['--theme-url'],
          {'metavar': '<URL>', 'overrides': 'theme'}),
         ('Allow existing theme files in the ``ui/<theme>`` directory to be '
          'overwritten.  The default is not to overwrite theme files.',
          ['--overwrite-theme-files'],
          {'action': 'store_true', 'validator': frontend.validate_boolean}),
         ('Keep existing theme files in the ``ui/<theme>`` directory; do not '
          'overwrite any.  This is the default.',
          ['--keep-theme-files'],
          {'dest': 'overwrite_theme_files', 'action': 'store_false'}),
         ('Set the initial view mode to "slideshow" [default] or "outline".',
          ['--view-mode'],
          {'choices': ['slideshow', 'outline'], 'default': 'slideshow',
           'metavar': '<mode>'}),
         ('Normally hide the presentation controls in slideshow mode. '
          'This is the default.',
          ['--hidden-controls'],
          {'action': 'store_true', 'default': True,
           'validator': frontend.validate_boolean}),
         ('Always show the presentation controls in slideshow mode.  '
          'The default is to hide the controls.',
          ['--visible-controls'],
          {'dest': 'hidden_controls', 'action': 'store_false'}),
         ('Enable the current slide indicator ("1 / 15").  '
          'The default is to disable it.',
          ['--current-slide'],
          {'action': 'store_true', 'validator': frontend.validate_boolean}),
         ('Disable the current slide indicator.  This is the default.',
          ['--no-current-slide'],
          {'dest': 'current_slide', 'action': 'store_false'}),))

    settings_default_overrides = {'toc_backlinks': 0}

    config_section = 's5_html writer'
    config_section_dependencies = ('writers', 'html4css1 writer')

    def __init__(self):
        html4css1.Writer.__init__(self)
        self.translator_class = S5HTMLTranslator


class S5HTMLTranslator(html4css1.HTMLTranslator):

    s5_stylesheet_template = """\
<!-- configuration parameters -->
<meta name="defaultView" content="%(view_mode)s" />
<meta name="controlVis" content="%(control_visibility)s" />
<!-- style sheet links -->
<script src="%(path)s/slides.js" type="text/javascript"></script>
<link rel="stylesheet" href="%(path)s/slides.css"
      type="text/css" media="projection" id="slideProj" />
<link rel="stylesheet" href="%(path)s/outline.css"
      type="text/css" media="screen" id="outlineStyle" />
<link rel="stylesheet" href="%(path)s/print.css"
      type="text/css" media="print" id="slidePrint" />
<link rel="stylesheet" href="%(path)s/opera.css"
      type="text/css" media="projection" id="operaFix" />\n"""
    # The script element must go in front of the link elements to
    # avoid a flash of unstyled content (FOUC), reproducible with
    # Firefox.

    disable_current_slide = """
<style type="text/css">
#currentSlide {display: none;}
</style>\n"""

    layout_template = """\
<div class="layout">
<div id="controls"></div>
<div id="currentSlide"></div>
<div id="header">
%(header)s
</div>
<div id="footer">
%(title)s%(footer)s
</div>
</div>\n"""
# <div class="topleft"></div>
# <div class="topright"></div>
# <div class="bottomleft"></div>
# <div class="bottomright"></div>

    default_theme = 'default'
    """Name of the default theme."""

    base_theme_file = '__base__'
    """Name of the file containing the name of the base theme."""

    direct_theme_files = (
        'slides.css', 'outline.css', 'print.css', 'opera.css', 'slides.js')
    """Names of theme files directly linked to in the output HTML"""

    indirect_theme_files = (
        's5-core.css', 'framing.css', 'pretty.css', 'blank.gif', 'iepngfix.htc')
    """Names of files used indirectly; imported or used by files in
    `direct_theme_files`."""

    required_theme_files = indirect_theme_files + direct_theme_files
    """Names of mandatory theme files."""

    def __init__(self, *args):
        html4css1.HTMLTranslator.__init__(self, *args)
        #insert S5-specific stylesheet and script stuff:
        self.theme_file_path = None
        self.setup_theme()
        view_mode = self.document.settings.view_mode
        control_visibility = ('visible', 'hidden')[self.document.settings
                                                   .hidden_controls]
        self.stylesheet.append(self.s5_stylesheet_template
                               % {'path': self.theme_file_path,
                                  'view_mode': view_mode,
                                  'control_visibility': control_visibility})
        if not self.document.settings.current_slide:
            self.stylesheet.append(self.disable_current_slide)
        self.add_meta('<meta name="version" content="S5 1.1" />\n')
        self.s5_footer = []
        self.s5_header = []
        self.section_count = 0
        self.theme_files_copied = None

    def setup_theme(self):
        if self.document.settings.theme:
            self.copy_theme()
        elif self.document.settings.theme_url:
            self.theme_file_path = self.document.settings.theme_url
        else:
            raise docutils.ApplicationError(
                'No theme specified for S5/HTML writer.')

    def copy_theme(self):
        """
        Locate & copy theme files.

        A theme may be explicitly based on another theme via a '__base__'
        file.  The default base theme is 'default'.  Files are accumulated
        from the specified theme, any base themes, and 'default'.
        """
        settings = self.document.settings
        path = find_theme(settings.theme)
        theme_paths = [path]
        self.theme_files_copied = {}
        required_files_copied = {}
        # This is a link (URL) in HTML, so we use "/", not os.sep:
        self.theme_file_path = '%s/%s' % ('ui', settings.theme)
        if settings._destination:
            dest = os.path.join(
                os.path.dirname(settings._destination), 'ui', settings.theme)
            if not os.path.isdir(dest):
                os.makedirs(dest)
        else:
            # no destination, so we can't copy the theme
            return
        default = False
        while path:
            for f in os.listdir(path):  # copy all files from each theme
                if f == self.base_theme_file:
                    continue            # ... except the "__base__" file
                if ( self.copy_file(f, path, dest)
                     and f in self.required_theme_files):
                    required_files_copied[f] = 1
            if default:
                break                   # "default" theme has no base theme
            # Find the "__base__" file in theme directory:
            base_theme_file = os.path.join(path, self.base_theme_file)
            # If it exists, read it and record the theme path:
            if os.path.isfile(base_theme_file):
                lines = open(base_theme_file).readlines()
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        path = find_theme(line)
                        if path in theme_paths: # check for duplicates (cycles)
                            path = None         # if found, use default base
                        else:
                            theme_paths.append(path)
                        break
                else:                   # no theme name found
                    path = None         # use default base
            else:                       # no base theme file found
                path = None             # use default base
            if not path:
                path = find_theme(self.default_theme)
                theme_paths.append(path)
                default = True
        if len(required_files_copied) != len(self.required_theme_files):
            # Some required files weren't found & couldn't be copied.
            required = list(self.required_theme_files)
            for f in list(required_files_copied.keys()):
                required.remove(f)
            raise docutils.ApplicationError(
                'Theme files not found: %s'
                % ', '.join(['%r' % f for f in required]))

    files_to_skip_pattern = re.compile(r'~$|\.bak$|#$|\.cvsignore$')

    def copy_file(self, name, source_dir, dest_dir):
        """
        Copy file `name` from `source_dir` to `dest_dir`.
        Return 1 if the file exists in either `source_dir` or `dest_dir`.
        """
        source = os.path.join(source_dir, name)
        dest = os.path.join(dest_dir, name)
        if dest in self.theme_files_copied:
            return 1
        else:
            self.theme_files_copied[dest] = 1
        if os.path.isfile(source):
            if self.files_to_skip_pattern.search(source):
                return None
            settings = self.document.settings
            if os.path.exists(dest) and not settings.overwrite_theme_files:
                settings.record_dependencies.add(dest)
            else:
                src_file = open(source, 'rb')
                src_data = src_file.read()
                src_file.close()
                dest_file = open(dest, 'wb')
                dest_dir = dest_dir.replace(os.sep, '/')
                dest_file.write(src_data.replace(
                    b('ui/default'),
                    dest_dir[dest_dir.rfind('ui/'):].encode(
                    sys.getfilesystemencoding())))
                dest_file.close()
                settings.record_dependencies.add(source)
            return 1
        if os.path.isfile(dest):
            return 1

    def depart_document(self, node):
        self.head_prefix.extend([self.doctype,
                                 self.head_prefix_template %
                                 {'lang': self.settings.language_code}])
        self.html_prolog.append(self.doctype)
        self.meta.insert(0, self.content_type % self.settings.output_encoding)
        self.head.insert(0, self.content_type % self.settings.output_encoding)
        if self.math_header:
            if self.math_output == 'mathjax':
                self.head.extend(self.math_header)
            else:
                self.stylesheet.extend(self.math_header)
        # skip content-type meta tag with interpolated charset value:
        self.html_head.extend(self.head[1:])
        self.fragment.extend(self.body)
        # special S5 code up to the next comment line
        header = ''.join(self.s5_header)
        footer = ''.join(self.s5_footer)
        title = ''.join(self.html_title).replace('<h1 class="title">', '<h1>')
        layout = self.layout_template % {'header': header,
                                         'title': title,
                                         'footer': footer}
        self.body_prefix.extend(layout)
        self.body_prefix.append('<div class="presentation">\n')
        self.body_prefix.append(
            self.starttag({'classes': ['slide'], 'ids': ['slide0']}, 'div'))
        if not self.section_count:
            self.body.append('</div>\n')
        #
        self.body_suffix.insert(0, '</div>\n')
        self.html_body.extend(self.body_prefix[1:] + self.body_pre_docinfo
                              + self.docinfo + self.body
                              + self.body_suffix[:-1])

    def depart_footer(self, node):
        start = self.context.pop()
        self.s5_footer.append('<h2>')
        self.s5_footer.extend(self.body[start:])
        self.s5_footer.append('</h2>')
        del self.body[start:]

    def depart_header(self, node):
        start = self.context.pop()
        header = ['<div id="header">\n']
        header.extend(self.body[start:])
        header.append('\n</div>\n')
        del self.body[start:]
        self.s5_header.extend(header)

    def visit_section(self, node):
        if not self.section_count:
            self.body.append('\n</div>\n')
        self.section_count += 1
        self.section_level += 1
        if self.section_level > 1:
            # dummy for matching div's
            self.body.append(self.starttag(node, 'div', CLASS='section'))
        else:
            self.body.append(self.starttag(node, 'div', CLASS='slide'))

    def visit_subtitle(self, node):
        if isinstance(node.parent, nodes.section):
            level = self.section_level + self.initial_header_level - 1
            if level == 1:
                level = 2
            tag = 'h%s' % level
            self.body.append(self.starttag(node, tag, ''))
            self.context.append('</%s>\n' % tag)
        else:
            html4css1.HTMLTranslator.visit_subtitle(self, node)

    def visit_title(self, node):
        html4css1.HTMLTranslator.visit_title(self, node)
