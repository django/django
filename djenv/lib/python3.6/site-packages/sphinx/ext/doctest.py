# -*- coding: utf-8 -*-
"""
    sphinx.ext.doctest
    ~~~~~~~~~~~~~~~~~~

    Mimic doctest by automatically executing code snippets and checking
    their results.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""
from __future__ import absolute_import

import codecs
import doctest
import re
import sys
import time
from os import path

from docutils import nodes
from docutils.parsers.rst import directives
from packaging.specifiers import SpecifierSet, InvalidSpecifier
from packaging.version import Version
from six import itervalues, StringIO, binary_type, text_type, PY2

import sphinx
from sphinx.builders import Builder
from sphinx.locale import __
from sphinx.util import force_decode, logging
from sphinx.util.console import bold  # type: ignore
from sphinx.util.docutils import SphinxDirective
from sphinx.util.nodes import set_source_info
from sphinx.util.osutil import fs_encoding, relpath

if False:
    # For type annotation
    from typing import Any, Callable, Dict, IO, Iterable, List, Optional, Sequence, Set, Tuple  # NOQA
    from sphinx.application import Sphinx  # NOQA

logger = logging.getLogger(__name__)

blankline_re = re.compile(r'^\s*<BLANKLINE>', re.MULTILINE)
doctestopt_re = re.compile(r'#\s*doctest:.+$', re.MULTILINE)

if PY2:
    def doctest_encode(text, encoding):
        # type: (str, unicode) -> unicode
        if isinstance(text, text_type):
            text = text.encode(encoding)
            if text.startswith(codecs.BOM_UTF8):
                text = text[len(codecs.BOM_UTF8):]
        return text
else:
    def doctest_encode(text, encoding):
        # type: (unicode, unicode) -> unicode
        return text


def is_allowed_version(spec, version):
    # type: (unicode, unicode) -> bool
    """Check `spec` satisfies `version` or not.

    This obeys PEP-440 specifiers:
    https://www.python.org/dev/peps/pep-0440/#version-specifiers

    Some examples:

        >>> is_allowed_version('3.3', '<=3.5')
        True
        >>> is_allowed_version('3.3', '<=3.2')
        False
        >>> is_allowed_version('3.3', '>3.2, <4.0')
        True
    """
    return Version(version) in SpecifierSet(spec)


# set up the necessary directives

class TestDirective(SphinxDirective):
    """
    Base class for doctest-related directives.
    """

    has_content = True
    required_arguments = 0
    optional_arguments = 1
    final_argument_whitespace = True

    def run(self):
        # type: () -> List[nodes.Node]
        # use ordinary docutils nodes for test code: they get special attributes
        # so that our builder recognizes them, and the other builders are happy.
        code = '\n'.join(self.content)
        test = None
        if self.name == 'doctest':
            if '<BLANKLINE>' in code:
                # convert <BLANKLINE>s to ordinary blank lines for presentation
                test = code
                code = blankline_re.sub('', code)
            if doctestopt_re.search(code):
                if not test:
                    test = code
                code = doctestopt_re.sub('', code)
        nodetype = nodes.literal_block
        if self.name in ('testsetup', 'testcleanup') or 'hide' in self.options:
            nodetype = nodes.comment
        if self.arguments:
            groups = [x.strip() for x in self.arguments[0].split(',')]
        else:
            groups = ['default']
        node = nodetype(code, code, testnodetype=self.name, groups=groups)
        set_source_info(self, node)
        if test is not None:
            # only save if it differs from code
            node['test'] = test
        if self.name == 'doctest':
            node['language'] = 'pycon'
        elif self.name == 'testcode':
            node['language'] = 'python'
        elif self.name == 'testoutput':
            # don't try to highlight output
            node['language'] = 'none'
        node['options'] = {}
        if self.name in ('doctest', 'testoutput') and 'options' in self.options:
            # parse doctest-like output comparison flags
            option_strings = self.options['options'].replace(',', ' ').split()
            for option in option_strings:
                prefix, option_name = option[0], option[1:]
                if prefix not in '+-':
                    self.state.document.reporter.warning(
                        __("missing '+' or '-' in '%s' option.") % option,
                        line=self.lineno)
                    continue
                if option_name not in doctest.OPTIONFLAGS_BY_NAME:
                    self.state.document.reporter.warning(
                        __("'%s' is not a valid option.") % option_name,
                        line=self.lineno)
                    continue
                flag = doctest.OPTIONFLAGS_BY_NAME[option[1:]]
                node['options'][flag] = (option[0] == '+')
        if self.name == 'doctest' and 'pyversion' in self.options:
            try:
                spec = self.options['pyversion']
                python_version = '.'.join([str(v) for v in sys.version_info[:3]])
                if not is_allowed_version(spec, python_version):
                    flag = doctest.OPTIONFLAGS_BY_NAME['SKIP']
                    node['options'][flag] = True  # Skip the test
            except InvalidSpecifier:
                self.state.document.reporter.warning(
                    __("'%s' is not a valid pyversion option") % spec,
                    line=self.lineno)
        if 'skipif' in self.options:
            node['skipif'] = self.options['skipif']
        return [node]


class TestsetupDirective(TestDirective):
    option_spec = {'skipif': directives.unchanged_required}  # type: Dict


class TestcleanupDirective(TestDirective):
    option_spec = {'skipif': directives.unchanged_required}  # type: Dict


class DoctestDirective(TestDirective):
    option_spec = {
        'hide': directives.flag,
        'options': directives.unchanged,
        'pyversion': directives.unchanged_required,
        'skipif': directives.unchanged_required,
    }


class TestcodeDirective(TestDirective):
    option_spec = {
        'hide': directives.flag,
        'pyversion': directives.unchanged_required,
        'skipif': directives.unchanged_required,
    }


class TestoutputDirective(TestDirective):
    option_spec = {
        'hide': directives.flag,
        'options': directives.unchanged,
        'pyversion': directives.unchanged_required,
        'skipif': directives.unchanged_required,
    }


parser = doctest.DocTestParser()


# helper classes

class TestGroup(object):
    def __init__(self, name):
        # type: (unicode) -> None
        self.name = name
        self.setup = []     # type: List[TestCode]
        self.tests = []     # type: List[List[TestCode]]
        self.cleanup = []   # type: List[TestCode]

    def add_code(self, code, prepend=False):
        # type: (TestCode, bool) -> None
        if code.type == 'testsetup':
            if prepend:
                self.setup.insert(0, code)
            else:
                self.setup.append(code)
        elif code.type == 'testcleanup':
            self.cleanup.append(code)
        elif code.type == 'doctest':
            self.tests.append([code])
        elif code.type == 'testcode':
            self.tests.append([code, None])
        elif code.type == 'testoutput':
            if self.tests and len(self.tests[-1]) == 2:
                self.tests[-1][1] = code
        else:
            raise RuntimeError(__('invalid TestCode type'))

    def __repr__(self):  # type: ignore
        # type: () -> unicode
        return 'TestGroup(name=%r, setup=%r, cleanup=%r, tests=%r)' % (
            self.name, self.setup, self.cleanup, self.tests)


class TestCode(object):
    def __init__(self, code, type, filename, lineno, options=None):
        # type: (unicode, unicode, Optional[str], int, Optional[Dict]) -> None
        self.code = code
        self.type = type
        self.filename = filename
        self.lineno = lineno
        self.options = options or {}

    def __repr__(self):  # type: ignore
        # type: () -> unicode
        return 'TestCode(%r, %r, filename=%r, lineno=%r, options=%r)' % (
            self.code, self.type, self.filename, self.lineno, self.options)


class SphinxDocTestRunner(doctest.DocTestRunner):
    def summarize(self, out, verbose=None):  # type: ignore
        # type: (Callable, bool) -> Tuple[int, int]
        string_io = StringIO()
        old_stdout = sys.stdout
        sys.stdout = string_io
        try:
            res = doctest.DocTestRunner.summarize(self, verbose)
        finally:
            sys.stdout = old_stdout
        out(string_io.getvalue())
        return res

    def _DocTestRunner__patched_linecache_getlines(self, filename,
                                                   module_globals=None):
        # type: (unicode, Any) -> Any
        # this is overridden from DocTestRunner adding the try-except below
        m = self._DocTestRunner__LINECACHE_FILENAME_RE.match(filename)  # type: ignore
        if m and m.group('name') == self.test.name:
            try:
                example = self.test.examples[int(m.group('examplenum'))]
            # because we compile multiple doctest blocks with the same name
            # (viz. the group name) this might, for outer stack frames in a
            # traceback, get the wrong test which might not have enough examples
            except IndexError:
                pass
            else:
                return example.source.splitlines(True)
        return self.save_linecache_getlines(filename, module_globals)  # type: ignore


# the new builder -- use sphinx-build.py -b doctest to run

class DocTestBuilder(Builder):
    """
    Runs test snippets in the documentation.
    """
    name = 'doctest'
    epilog = __('Testing of doctests in the sources finished, look at the '
                'results in %(outdir)s/output.txt.')

    def init(self):
        # type: () -> None
        # default options
        self.opt = self.config.doctest_default_flags

        # HACK HACK HACK
        # doctest compiles its snippets with type 'single'. That is nice
        # for doctest examples but unusable for multi-statement code such
        # as setup code -- to be able to use doctest error reporting with
        # that code nevertheless, we monkey-patch the "compile" it uses.
        doctest.compile = self.compile  # type: ignore

        sys.path[0:0] = self.config.doctest_path

        self.type = 'single'

        self.total_failures = 0
        self.total_tries = 0
        self.setup_failures = 0
        self.setup_tries = 0
        self.cleanup_failures = 0
        self.cleanup_tries = 0

        date = time.strftime('%Y-%m-%d %H:%M:%S')

        self.outfile = None  # type: IO
        self.outfile = codecs.open(path.join(self.outdir, 'output.txt'),  # type: ignore
                                   'w', encoding='utf-8')
        self.outfile.write(('Results of doctest builder run on %s\n'
                            '==================================%s\n') %
                           (date, '=' * len(date)))

    def _out(self, text):
        # type: (unicode) -> None
        logger.info(text, nonl=True)
        self.outfile.write(text)

    def _warn_out(self, text):
        # type: (unicode) -> None
        if self.app.quiet or self.app.warningiserror:
            logger.warning(text)
        else:
            logger.info(text, nonl=True)
        if isinstance(text, binary_type):
            text = force_decode(text, None)
        self.outfile.write(text)

    def get_target_uri(self, docname, typ=None):
        # type: (unicode, unicode) -> unicode
        return ''

    def get_outdated_docs(self):
        # type: () -> Set[unicode]
        return self.env.found_docs

    def finish(self):
        # type: () -> None
        # write executive summary
        def s(v):
            # type: (int) -> unicode
            return v != 1 and 's' or ''
        repl = (self.total_tries, s(self.total_tries),
                self.total_failures, s(self.total_failures),
                self.setup_failures, s(self.setup_failures),
                self.cleanup_failures, s(self.cleanup_failures))
        self._out('''
Doctest summary
===============
%5d test%s
%5d failure%s in tests
%5d failure%s in setup code
%5d failure%s in cleanup code
''' % repl)
        self.outfile.close()

        if self.total_failures or self.setup_failures or self.cleanup_failures:
            self.app.statuscode = 1

    def write(self, build_docnames, updated_docnames, method='update'):
        # type: (Iterable[unicode], Sequence[unicode], unicode) -> None
        if build_docnames is None:
            build_docnames = sorted(self.env.all_docs)

        logger.info(bold('running tests...'))
        for docname in build_docnames:
            # no need to resolve the doctree
            doctree = self.env.get_doctree(docname)
            self.test_doc(docname, doctree)

    def get_filename_for_node(self, node, docname):
        # type: (nodes.Node, unicode) -> str
        """Try to get the file which actually contains the doctest, not the
        filename of the document it's included in."""
        try:
            filename = relpath(node.source, self.env.srcdir)\
                .rsplit(':docstring of ', maxsplit=1)[0]
        except Exception:
            filename = self.env.doc2path(docname, base=None)
        if PY2:
            return filename.encode(fs_encoding)
        return filename

    @staticmethod
    def get_line_number(node):
        # type: (nodes.Node) -> Optional[int]
        """Get the real line number or admit we don't know."""
        # TODO:  Work out how to store or calculate real (file-relative)
        #       line numbers for doctest blocks in docstrings.
        if ':docstring of ' in path.basename(node.source or ''):
            # The line number is given relative to the stripped docstring,
            # not the file.  This is correct where it is set, in
            # `docutils.nodes.Node.setup_child`, but Sphinx should report
            # relative to the file, not the docstring.
            return None
        if node.line is not None:
            # TODO: find the root cause of this off by one error.
            return node.line - 1
        return None

    def skipped(self, node):
        # type: (nodes.Element) -> bool
        if 'skipif' not in node:
            return False
        else:
            condition = node['skipif']
            context = {}  # type: Dict[str, Any]
            if self.config.doctest_global_setup:
                exec(self.config.doctest_global_setup, context)
            should_skip = eval(condition, context)
            if self.config.doctest_global_cleanup:
                exec(self.config.doctest_global_cleanup, context)
            return should_skip

    def test_doc(self, docname, doctree):
        # type: (unicode, nodes.Node) -> None
        groups = {}  # type: Dict[unicode, TestGroup]
        add_to_all_groups = []
        self.setup_runner = SphinxDocTestRunner(verbose=False,
                                                optionflags=self.opt)
        self.test_runner = SphinxDocTestRunner(verbose=False,
                                               optionflags=self.opt)
        self.cleanup_runner = SphinxDocTestRunner(verbose=False,
                                                  optionflags=self.opt)

        self.test_runner._fakeout = self.setup_runner._fakeout  # type: ignore
        self.cleanup_runner._fakeout = self.setup_runner._fakeout  # type: ignore

        if self.config.doctest_test_doctest_blocks:
            def condition(node):
                # type: (nodes.Node) -> bool
                return (isinstance(node, (nodes.literal_block, nodes.comment)) and
                        'testnodetype' in node) or \
                    isinstance(node, nodes.doctest_block)
        else:
            def condition(node):
                # type: (nodes.Node) -> bool
                return isinstance(node, (nodes.literal_block, nodes.comment)) \
                    and 'testnodetype' in node
        for node in doctree.traverse(condition):
            if self.skipped(node):
                continue

            source = node['test'] if 'test' in node else node.astext()
            filename = self.get_filename_for_node(node, docname)
            line_number = self.get_line_number(node)
            if not source:
                logger.warning(__('no code/output in %s block at %s:%s'),
                               node.get('testnodetype', 'doctest'),
                               filename, line_number)
            code = TestCode(source, type=node.get('testnodetype', 'doctest'),
                            filename=filename, lineno=line_number,
                            options=node.get('options'))
            node_groups = node.get('groups', ['default'])
            if '*' in node_groups:
                add_to_all_groups.append(code)
                continue
            for groupname in node_groups:
                if groupname not in groups:
                    groups[groupname] = TestGroup(groupname)
                groups[groupname].add_code(code)
        for code in add_to_all_groups:
            for group in itervalues(groups):
                group.add_code(code)
        if self.config.doctest_global_setup:
            code = TestCode(self.config.doctest_global_setup,
                            'testsetup', filename=None, lineno=0)
            for group in itervalues(groups):
                group.add_code(code, prepend=True)
        if self.config.doctest_global_cleanup:
            code = TestCode(self.config.doctest_global_cleanup,
                            'testcleanup', filename=None, lineno=0)
            for group in itervalues(groups):
                group.add_code(code)
        if not groups:
            return

        self._out('\nDocument: %s\n----------%s\n' %
                  (docname, '-' * len(docname)))
        for group in itervalues(groups):
            self.test_group(group)
        # Separately count results from setup code
        res_f, res_t = self.setup_runner.summarize(self._out, verbose=False)
        self.setup_failures += res_f
        self.setup_tries += res_t
        if self.test_runner.tries:
            res_f, res_t = self.test_runner.summarize(self._out, verbose=True)
            self.total_failures += res_f
            self.total_tries += res_t
        if self.cleanup_runner.tries:
            res_f, res_t = self.cleanup_runner.summarize(self._out,
                                                         verbose=True)
            self.cleanup_failures += res_f
            self.cleanup_tries += res_t

    def compile(self, code, name, type, flags, dont_inherit):
        # type: (unicode, unicode, unicode, Any, bool) -> Any
        return compile(code, name, self.type, flags, dont_inherit)

    def test_group(self, group):
        # type: (TestGroup) -> None
        ns = {}  # type: Dict

        def run_setup_cleanup(runner, testcodes, what):
            # type: (Any, List[TestCode], Any) -> bool
            examples = []
            for testcode in testcodes:
                examples.append(doctest.Example(  # type: ignore
                    doctest_encode(testcode.code, self.env.config.source_encoding), '',  # type: ignore  # NOQA
                    lineno=testcode.lineno))
            if not examples:
                return True
            # simulate a doctest with the code
            sim_doctest = doctest.DocTest(examples, {},
                                          '%s (%s code)' % (group.name, what),
                                          testcodes[0].filename, 0, None)
            sim_doctest.globs = ns
            old_f = runner.failures
            self.type = 'exec'  # the snippet may contain multiple statements
            runner.run(sim_doctest, out=self._warn_out, clear_globs=False)
            if runner.failures > old_f:
                return False
            return True

        # run the setup code
        if not run_setup_cleanup(self.setup_runner, group.setup, 'setup'):
            # if setup failed, don't run the group
            return

        # run the tests
        for code in group.tests:
            if len(code) == 1:
                # ordinary doctests (code/output interleaved)
                try:
                    test = parser.get_doctest(  # type: ignore
                        doctest_encode(code[0].code, self.env.config.source_encoding), {},  # type: ignore  # NOQA
                        group.name, code[0].filename, code[0].lineno)
                except Exception:
                    logger.warning(__('ignoring invalid doctest code: %r'), code[0].code,
                                   location=(code[0].filename, code[0].lineno))
                    continue
                if not test.examples:
                    continue
                for example in test.examples:
                    # apply directive's comparison options
                    new_opt = code[0].options.copy()
                    new_opt.update(example.options)
                    example.options = new_opt
                self.type = 'single'  # as for ordinary doctests
            else:
                # testcode and output separate
                output = code[1] and code[1].code or ''
                options = code[1] and code[1].options or {}
                # disable <BLANKLINE> processing as it is not needed
                options[doctest.DONT_ACCEPT_BLANKLINE] = True
                # find out if we're testing an exception
                m = parser._EXCEPTION_RE.match(output)  # type: ignore
                if m:
                    exc_msg = m.group('msg')
                else:
                    exc_msg = None
                example = doctest.Example(  # type: ignore
                    doctest_encode(code[0].code, self.env.config.source_encoding), output,  # type: ignore  # NOQA
                    exc_msg=exc_msg,
                    lineno=code[0].lineno,
                    options=options)
                test = doctest.DocTest([example], {}, group.name,  # type: ignore
                                       code[0].filename, code[0].lineno, None)
                self.type = 'exec'  # multiple statements again
            # DocTest.__init__ copies the globs namespace, which we don't want
            test.globs = ns
            # also don't clear the globs namespace after running the doctest
            self.test_runner.run(test, out=self._warn_out, clear_globs=False)

        # run the cleanup
        run_setup_cleanup(self.cleanup_runner, group.cleanup, 'cleanup')


def setup(app):
    # type: (Sphinx) -> Dict[unicode, Any]
    app.add_directive('testsetup', TestsetupDirective)
    app.add_directive('testcleanup', TestcleanupDirective)
    app.add_directive('doctest', DoctestDirective)
    app.add_directive('testcode', TestcodeDirective)
    app.add_directive('testoutput', TestoutputDirective)
    app.add_builder(DocTestBuilder)
    # this config value adds to sys.path
    app.add_config_value('doctest_path', [], False)
    app.add_config_value('doctest_test_doctest_blocks', 'default', False)
    app.add_config_value('doctest_global_setup', '', False)
    app.add_config_value('doctest_global_cleanup', '', False)
    app.add_config_value(
        'doctest_default_flags',
        doctest.DONT_ACCEPT_TRUE_FOR_1 | doctest.ELLIPSIS | doctest.IGNORE_EXCEPTION_DETAIL,
        False)
    return {'version': sphinx.__display_version__, 'parallel_read_safe': True}
