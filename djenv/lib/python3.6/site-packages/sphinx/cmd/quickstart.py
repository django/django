# -*- coding: utf-8 -*-
"""
    sphinx.cmd.quickstart
    ~~~~~~~~~~~~~~~~~~~~~

    Quickly setup documentation source to work with Sphinx.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""
from __future__ import absolute_import
from __future__ import print_function

import argparse
import locale
import os
import re
import sys
import time
from collections import OrderedDict
from io import open
from os import path

# try to import readline, unix specific enhancement
try:
    import readline
    if readline.__doc__ and 'libedit' in readline.__doc__:
        readline.parse_and_bind("bind ^I rl_complete")
        USE_LIBEDIT = True
    else:
        readline.parse_and_bind("tab: complete")
        USE_LIBEDIT = False
except ImportError:
    USE_LIBEDIT = False

from docutils.utils import column_width
from six import PY2, PY3, text_type, binary_type
from six.moves import input
from six.moves.urllib.parse import quote as urlquote

import sphinx.locale
from sphinx import __display_version__, package_dir
from sphinx.locale import __
from sphinx.util import texescape
from sphinx.util.console import (  # type: ignore
    colorize, bold, red, turquoise, nocolor, color_terminal
)
from sphinx.util.osutil import ensuredir, make_filename
from sphinx.util.template import SphinxRenderer

if False:
    # For type annotation
    from typing import Any, Callable, Dict, List, Pattern, Union  # NOQA

TERM_ENCODING = getattr(sys.stdin, 'encoding', None)

EXTENSIONS = OrderedDict([
    ('autodoc', __('automatically insert docstrings from modules')),
    ('doctest', __('automatically test code snippets in doctest blocks')),
    ('intersphinx', __('link between Sphinx documentation of different projects')),
    ('todo', __('write "todo" entries that can be shown or hidden on build')),
    ('coverage', __('checks for documentation coverage')),
    ('imgmath', __('include math, rendered as PNG or SVG images')),
    ('mathjax', __('include math, rendered in the browser by MathJax')),
    ('ifconfig', __('conditional inclusion of content based on config values')),
    ('viewcode',
     __('include links to the source code of documented Python objects')),
    ('githubpages',
     __('create .nojekyll file to publish the document on GitHub pages')),
])

DEFAULTS = {
    'path': '.',
    'sep': False,
    'dot': '_',
    'language': None,
    'suffix': '.rst',
    'master': 'index',
    'makefile': True,
    'batchfile': True,
}

PROMPT_PREFIX = '> '

if sys.platform == 'win32':
    # On Windows, show questions as bold because of color scheme of PowerShell (refs: #5294).
    COLOR_QUESTION = 'bold'
else:
    COLOR_QUESTION = 'purple'


# function to get input from terminal -- overridden by the test suite
def term_input(prompt):
    # type: (unicode) -> unicode
    if sys.platform == 'win32':
        # Important: On windows, readline is not enabled by default.  In these
        #            environment, escape sequences have been broken.  To avoid the
        #            problem, quickstart uses ``print()`` to show prompt.
        print(prompt, end='')
        return input('')
    else:
        return input(prompt)


class ValidationError(Exception):
    """Raised for validation errors."""


def is_path(x):
    # type: (unicode) -> unicode
    x = path.expanduser(x)
    if path.exists(x) and not path.isdir(x):
        raise ValidationError(__("Please enter a valid path name."))
    return x


def allow_empty(x):
    # type: (unicode) -> unicode
    return x


def nonempty(x):
    # type: (unicode) -> unicode
    if not x:
        raise ValidationError(__("Please enter some text."))
    return x


def choice(*l):
    # type: (unicode) -> Callable[[unicode], unicode]
    def val(x):
        # type: (unicode) -> unicode
        if x not in l:
            raise ValidationError(__('Please enter one of %s.') % ', '.join(l))
        return x
    return val


def boolean(x):
    # type: (unicode) -> bool
    if x.upper() not in ('Y', 'YES', 'N', 'NO'):
        raise ValidationError(__("Please enter either 'y' or 'n'."))
    return x.upper() in ('Y', 'YES')


def suffix(x):
    # type: (unicode) -> unicode
    if not (x[0:1] == '.' and len(x) > 1):
        raise ValidationError(__("Please enter a file suffix, "
                                 "e.g. '.rst' or '.txt'."))
    return x


def ok(x):
    # type: (unicode) -> unicode
    return x


def term_decode(text):
    # type: (Union[bytes,unicode]) -> unicode
    if isinstance(text, text_type):
        return text

    # Use the known encoding, if possible
    if TERM_ENCODING:
        return text.decode(TERM_ENCODING)

    # If ascii is safe, use it with no warning
    if text.decode('ascii', 'replace').encode('ascii', 'replace') == text:
        return text.decode('ascii')

    print(turquoise(__('* Note: non-ASCII characters entered '
                       'and terminal encoding unknown -- assuming '
                       'UTF-8 or Latin-1.')))
    try:
        return text.decode('utf-8')
    except UnicodeDecodeError:
        return text.decode('latin1')


def do_prompt(text, default=None, validator=nonempty):
    # type: (unicode, unicode, Callable[[unicode], Any]) -> Union[unicode, bool]
    while True:
        if default is not None:
            prompt = PROMPT_PREFIX + '%s [%s]: ' % (text, default)  # type: unicode
        else:
            prompt = PROMPT_PREFIX + text + ': '
        if PY2:
            # for Python 2.x, try to get a Unicode string out of it
            if prompt.encode('ascii', 'replace').decode('ascii', 'replace') \
                    != prompt:
                if TERM_ENCODING:
                    prompt = prompt.encode(TERM_ENCODING)
                else:
                    print(turquoise(__('* Note: non-ASCII default value provided '
                                       'and terminal encoding unknown -- assuming '
                                       'UTF-8 or Latin-1.')))
                    try:
                        prompt = prompt.encode('utf-8')
                    except UnicodeEncodeError:
                        prompt = prompt.encode('latin1')
        if USE_LIBEDIT:
            # Note: libedit has a problem for combination of ``input()`` and escape
            # sequence (see #5335).  To avoid the problem, all prompts are not colored
            # on libedit.
            pass
        else:
            prompt = colorize(COLOR_QUESTION, prompt, input_mode=True)
        x = term_input(prompt).strip()
        if default and not x:
            x = default
        x = term_decode(x)
        try:
            x = validator(x)
        except ValidationError as err:
            print(red('* ' + str(err)))
            continue
        break
    return x


def convert_python_source(source, rex=re.compile(r"[uU]('.*?')")):
    # type: (unicode, Pattern) -> unicode
    # remove Unicode literal prefixes
    if PY3:
        return rex.sub('\\1', source)
    else:
        return source


class QuickstartRenderer(SphinxRenderer):
    def __init__(self, templatedir):
        # type: (unicode) -> None
        self.templatedir = templatedir or ''
        super(QuickstartRenderer, self).__init__()

    def render(self, template_name, context):
        # type: (unicode, Dict) -> unicode
        user_template = path.join(self.templatedir, path.basename(template_name))
        if self.templatedir and path.exists(user_template):
            return self.render_from_file(user_template, context)
        else:
            return super(QuickstartRenderer, self).render(template_name, context)


def ask_user(d):
    # type: (Dict) -> None
    """Ask the user for quickstart values missing from *d*.

    Values are:

    * path:      root path
    * sep:       separate source and build dirs (bool)
    * dot:       replacement for dot in _templates etc.
    * project:   project name
    * author:    author names
    * version:   version of project
    * release:   release of project
    * language:  document language
    * suffix:    source file suffix
    * master:    master document name
    * extensions:  extensions to use (list)
    * makefile:  make Makefile
    * batchfile: make command file
    """

    print(bold(__('Welcome to the Sphinx %s quickstart utility.')) % __display_version__)
    print(__('''
Please enter values for the following settings (just press Enter to
accept a default value, if one is given in brackets).'''))

    if 'path' in d:
        print(bold(__('''
Selected root path: %s''') % d['path']))
    else:
        print(__('''
Enter the root path for documentation.'''))
        d['path'] = do_prompt(__('Root path for the documentation'), '.', is_path)

    while path.isfile(path.join(d['path'], 'conf.py')) or \
            path.isfile(path.join(d['path'], 'source', 'conf.py')):
        print()
        print(bold(__('Error: an existing conf.py has been found in the '
                      'selected root path.')))
        print(__('sphinx-quickstart will not overwrite existing Sphinx projects.'))
        print()
        d['path'] = do_prompt(__('Please enter a new root path (or just Enter '
                                 'to exit)'), '', is_path)
        if not d['path']:
            sys.exit(1)

    if 'sep' not in d:
        print(__('''
You have two options for placing the build directory for Sphinx output.
Either, you use a directory "_build" within the root path, or you separate
"source" and "build" directories within the root path.'''))
        d['sep'] = do_prompt(__('Separate source and build directories (y/n)'),
                             'n', boolean)

    if 'dot' not in d:
        print(__('''
Inside the root directory, two more directories will be created; "_templates"
for custom HTML templates and "_static" for custom stylesheets and other static
files. You can enter another prefix (such as ".") to replace the underscore.'''))
        d['dot'] = do_prompt(__('Name prefix for templates and static dir'), '_', ok)

    if 'project' not in d:
        print(__('''
The project name will occur in several places in the built documentation.'''))
        d['project'] = do_prompt(__('Project name'))
    if 'author' not in d:
        d['author'] = do_prompt(__('Author name(s)'))

    if 'version' not in d:
        print(__('''
Sphinx has the notion of a "version" and a "release" for the
software. Each version can have multiple releases. For example, for
Python the version is something like 2.5 or 3.0, while the release is
something like 2.5.1 or 3.0a1.  If you don't need this dual structure,
just set both to the same value.'''))
        d['version'] = do_prompt(__('Project version'), '', allow_empty)
    if 'release' not in d:
        d['release'] = do_prompt(__('Project release'), d['version'], allow_empty)

    if 'language' not in d:
        print(__('''
If the documents are to be written in a language other than English,
you can select a language here by its language code. Sphinx will then
translate text that it generates into that language.

For a list of supported codes, see
http://sphinx-doc.org/config.html#confval-language.'''))
        d['language'] = do_prompt(__('Project language'), 'en')
        if d['language'] == 'en':
            d['language'] = None

    if 'suffix' not in d:
        print(__('''
The file name suffix for source files. Commonly, this is either ".txt"
or ".rst".  Only files with this suffix are considered documents.'''))
        d['suffix'] = do_prompt(__('Source file suffix'), '.rst', suffix)

    if 'master' not in d:
        print(__('''
One document is special in that it is considered the top node of the
"contents tree", that is, it is the root of the hierarchical structure
of the documents. Normally, this is "index", but if your "index"
document is a custom template, you can also set this to another filename.'''))
        d['master'] = do_prompt(__('Name of your master document (without suffix)'),
                                'index')

    while path.isfile(path.join(d['path'], d['master'] + d['suffix'])) or \
            path.isfile(path.join(d['path'], 'source', d['master'] + d['suffix'])):
        print()
        print(bold(__('Error: the master file %s has already been found in the '
                      'selected root path.') % (d['master'] + d['suffix'])))
        print(__('sphinx-quickstart will not overwrite the existing file.'))
        print()
        d['master'] = do_prompt(__('Please enter a new file name, or rename the '
                                   'existing file and press Enter'), d['master'])

    if 'extensions' not in d:
        print(__('Indicate which of the following Sphinx extensions should be '
                 'enabled:'))
        d['extensions'] = []
        for name, description in EXTENSIONS.items():
            if do_prompt('%s: %s (y/n)' % (name, description), 'n', boolean):
                d['extensions'].append('sphinx.ext.%s' % name)

        # Handle conflicting options
        if set(['sphinx.ext.imgmath', 'sphinx.ext.mathjax']).issubset(
                d['extensions']):
            print(__('Note: imgmath and mathjax cannot be enabled at the same '
                     'time. imgmath has been deselected.'))
            d['extensions'].remove('sphinx.ext.imgmath')

    if 'makefile' not in d:
        print(__('''
A Makefile and a Windows command file can be generated for you so that you
only have to run e.g. `make html' instead of invoking sphinx-build
directly.'''))
        d['makefile'] = do_prompt(__('Create Makefile? (y/n)'), 'y', boolean)

    if 'batchfile' not in d:
        d['batchfile'] = do_prompt(__('Create Windows command file? (y/n)'),
                                   'y', boolean)
    print()


def generate(d, overwrite=True, silent=False, templatedir=None):
    # type: (Dict, bool, bool, unicode) -> None
    """Generate project based on values in *d*."""
    template = QuickstartRenderer(templatedir=templatedir)

    texescape.init()

    if 'mastertoctree' not in d:
        d['mastertoctree'] = ''
    if 'mastertocmaxdepth' not in d:
        d['mastertocmaxdepth'] = 2

    d['PY3'] = PY3
    d['project_fn'] = make_filename(d['project'])
    d['project_url'] = urlquote(d['project'].encode('idna'))
    d['project_manpage'] = d['project_fn'].lower()
    d['now'] = time.asctime()
    d['project_underline'] = column_width(d['project']) * '='
    d.setdefault('extensions', [])
    d['copyright'] = time.strftime('%Y') + ', ' + d['author']
    d['author_texescaped'] = text_type(d['author']).\
        translate(texescape.tex_escape_map)
    d['project_doc'] = d['project'] + ' Documentation'
    d['project_doc_texescaped'] = text_type(d['project'] + ' Documentation').\
        translate(texescape.tex_escape_map)

    # escape backslashes and single quotes in strings that are put into
    # a Python string literal
    for key in ('project', 'project_doc', 'project_doc_texescaped',
                'author', 'author_texescaped', 'copyright',
                'version', 'release', 'master'):
        d[key + '_str'] = d[key].replace('\\', '\\\\').replace("'", "\\'")

    if not path.isdir(d['path']):
        ensuredir(d['path'])

    srcdir = d['sep'] and path.join(d['path'], 'source') or d['path']

    ensuredir(srcdir)
    if d['sep']:
        builddir = path.join(d['path'], 'build')
        d['exclude_patterns'] = ''
    else:
        builddir = path.join(srcdir, d['dot'] + 'build')
        exclude_patterns = map(repr, [
            d['dot'] + 'build',
            'Thumbs.db', '.DS_Store',
        ])
        d['exclude_patterns'] = ', '.join(exclude_patterns)
    ensuredir(builddir)
    ensuredir(path.join(srcdir, d['dot'] + 'templates'))
    ensuredir(path.join(srcdir, d['dot'] + 'static'))

    def write_file(fpath, content, newline=None):
        # type: (unicode, unicode, unicode) -> None
        if overwrite or not path.isfile(fpath):
            if 'quiet' not in d:
                print(__('Creating file %s.') % fpath)
            with open(fpath, 'wt', encoding='utf-8', newline=newline) as f:
                f.write(content)
        else:
            if 'quiet' not in d:
                print(__('File %s already exists, skipping.') % fpath)

    conf_path = os.path.join(templatedir, 'conf.py_t') if templatedir else None
    if not conf_path or not path.isfile(conf_path):
        conf_path = os.path.join(package_dir, 'templates', 'quickstart', 'conf.py_t')
    with open(conf_path) as f:
        conf_text = convert_python_source(f.read())

    write_file(path.join(srcdir, 'conf.py'), template.render_string(conf_text, d))

    masterfile = path.join(srcdir, d['master'] + d['suffix'])
    write_file(masterfile, template.render('quickstart/master_doc.rst_t', d))

    if d.get('make_mode') is True:
        makefile_template = 'quickstart/Makefile.new_t'
        batchfile_template = 'quickstart/make.bat.new_t'
    else:
        makefile_template = 'quickstart/Makefile_t'
        batchfile_template = 'quickstart/make.bat_t'

    if d['makefile'] is True:
        d['rsrcdir'] = d['sep'] and 'source' or '.'
        d['rbuilddir'] = d['sep'] and 'build' or d['dot'] + 'build'
        # use binary mode, to avoid writing \r\n on Windows
        write_file(path.join(d['path'], 'Makefile'),
                   template.render(makefile_template, d), u'\n')

    if d['batchfile'] is True:
        d['rsrcdir'] = d['sep'] and 'source' or '.'
        d['rbuilddir'] = d['sep'] and 'build' or d['dot'] + 'build'
        write_file(path.join(d['path'], 'make.bat'),
                   template.render(batchfile_template, d), u'\r\n')

    if silent:
        return
    print()
    print(bold(__('Finished: An initial directory structure has been created.')))
    print(__('''
You should now populate your master file %s and create other documentation
source files. ''') % masterfile + ((d['makefile'] or d['batchfile']) and __('''\
Use the Makefile to build the docs, like so:
   make builder
''') or __('''\
Use the sphinx-build command to build the docs, like so:
   sphinx-build -b builder %s %s
''') % (srcdir, builddir)) + __('''\
where "builder" is one of the supported builders, e.g. html, latex or linkcheck.
'''))


def valid_dir(d):
    # type: (Dict) -> bool
    dir = d['path']
    if not path.exists(dir):
        return True
    if not path.isdir(dir):
        return False

    if set(['Makefile', 'make.bat']) & set(os.listdir(dir)):
        return False

    if d['sep']:
        dir = os.path.join('source', dir)
        if not path.exists(dir):
            return True
        if not path.isdir(dir):
            return False

    reserved_names = [
        'conf.py',
        d['dot'] + 'static',
        d['dot'] + 'templates',
        d['master'] + d['suffix'],
    ]
    if set(reserved_names) & set(os.listdir(dir)):
        return False

    return True


def get_parser():
    # type: () -> argparse.ArgumentParser
    parser = argparse.ArgumentParser(
        usage='%(prog)s [OPTIONS] <PROJECT_DIR>',
        epilog=__("For more information, visit <http://sphinx-doc.org/>."),
        description=__("""
Generate required files for a Sphinx project.

sphinx-quickstart is an interactive tool that asks some questions about your
project and then generates a complete documentation directory and sample
Makefile to be used with sphinx-build.
"""))

    parser.add_argument('-q', '--quiet', action='store_true', dest='quiet',
                        default=None,
                        help=__('quiet mode'))
    parser.add_argument('--version', action='version', dest='show_version',
                        version='%%(prog)s %s' % __display_version__)

    parser.add_argument('path', metavar='PROJECT_DIR', default='.', nargs='?',
                        help=__('output path'))

    group = parser.add_argument_group(__('Structure options'))
    group.add_argument('--sep', action='store_true', default=None,
                       help=__('if specified, separate source and build dirs'))
    group.add_argument('--dot', metavar='DOT',
                       help=__('replacement for dot in _templates etc.'))

    group = parser.add_argument_group(__('Project basic options'))
    group.add_argument('-p', '--project', metavar='PROJECT', dest='project',
                       help=__('project name'))
    group.add_argument('-a', '--author', metavar='AUTHOR', dest='author',
                       help=__('author names'))
    group.add_argument('-v', metavar='VERSION', dest='version', default='',
                       help=__('version of project'))
    group.add_argument('-r', '--release', metavar='RELEASE', dest='release',
                       help=__('release of project'))
    group.add_argument('-l', '--language', metavar='LANGUAGE', dest='language',
                       help=__('document language'))
    group.add_argument('--suffix', metavar='SUFFIX',
                       help=__('source file suffix'))
    group.add_argument('--master', metavar='MASTER',
                       help=__('master document name'))
    group.add_argument('--epub', action='store_true', default=False,
                       help=__('use epub'))

    group = parser.add_argument_group(__('Extension options'))
    for ext in EXTENSIONS:
        group.add_argument('--ext-%s' % ext, action='append_const',
                           const='sphinx.ext.%s' % ext, dest='extensions',
                           help=__('enable %s extension') % ext)
    group.add_argument('--extensions', metavar='EXTENSIONS', dest='extensions',
                       action='append', help=__('enable arbitrary extensions'))

    group = parser.add_argument_group(__('Makefile and Batchfile creation'))
    group.add_argument('--makefile', action='store_true', dest='makefile', default=None,
                       help=__('create makefile'))
    group.add_argument('--no-makefile', action='store_false', dest='makefile',
                       help=__('do not create makefile'))
    group.add_argument('--batchfile', action='store_true', dest='batchfile', default=None,
                       help=__('create batchfile'))
    group.add_argument('--no-batchfile', action='store_false',
                       dest='batchfile',
                       help=__('do not create batchfile'))
    group.add_argument('-m', '--use-make-mode', action='store_true',
                       dest='make_mode', default=True,
                       help=__('use make-mode for Makefile/make.bat'))
    group.add_argument('-M', '--no-use-make-mode', action='store_false',
                       dest='make_mode',
                       help=__('do not use make-mode for Makefile/make.bat'))

    group = parser.add_argument_group(__('Project templating'))
    group.add_argument('-t', '--templatedir', metavar='TEMPLATEDIR',
                       dest='templatedir',
                       help=__('template directory for template files'))
    group.add_argument('-d', metavar='NAME=VALUE', action='append',
                       dest='variables',
                       help=__('define a template variable'))

    return parser


def main(argv=sys.argv[1:]):
    # type: (List[str]) -> int
    sphinx.locale.setlocale(locale.LC_ALL, '')
    sphinx.locale.init_console(os.path.join(package_dir, 'locale'), 'sphinx')

    if not color_terminal():
        nocolor()

    # parse options
    parser = get_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as err:
        return err.code

    d = vars(args)
    # delete None or False value
    d = dict((k, v) for k, v in d.items() if v is not None)

    try:
        if 'quiet' in d:
            if not set(['project', 'author']).issubset(d):
                print(__('''"quiet" is specified, but any of "project" or \
"author" is not specified.'''))
                return 1

        if set(['quiet', 'project', 'author']).issubset(d):
            # quiet mode with all required params satisfied, use default
            d.setdefault('version', '')
            d.setdefault('release', d['version'])
            d2 = DEFAULTS.copy()
            d2.update(d)
            d = d2

            if not valid_dir(d):
                print()
                print(bold(__('Error: specified path is not a directory, or sphinx'
                              ' files already exist.')))
                print(__('sphinx-quickstart only generate into a empty directory.'
                         ' Please specify a new root path.'))
                return 1
        else:
            ask_user(d)
    except (KeyboardInterrupt, EOFError):
        print()
        print('[Interrupted.]')
        return 130  # 128 + SIGINT

    # decode values in d if value is a Python string literal
    for key, value in d.items():
        if isinstance(value, binary_type):
            d[key] = term_decode(value)

    # handle use of CSV-style extension values
    d.setdefault('extensions', [])
    for ext in d['extensions'][:]:
        if ',' in ext:
            d['extensions'].remove(ext)
            d['extensions'].extend(ext.split(','))

    for variable in d.get('variables', []):
        try:
            name, value = variable.split('=')
            d[name] = value
        except ValueError:
            print(__('Invalid template variable: %s') % variable)

    generate(d, overwrite=False, templatedir=args.templatedir)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
