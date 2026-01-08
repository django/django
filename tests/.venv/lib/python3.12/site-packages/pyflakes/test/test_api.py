"""
Tests for L{pyflakes.scripts.pyflakes}.
"""

import contextlib
import io
import os
import sys
import shutil
import subprocess
import tempfile

from pyflakes.checker import PYPY
from pyflakes.messages import UnusedImport
from pyflakes.reporter import Reporter
from pyflakes.api import (
    main,
    check,
    checkPath,
    checkRecursive,
    iterSourceCode,
)
from pyflakes.test.harness import TestCase, skipIf


def withStderrTo(stderr, f, *args, **kwargs):
    """
    Call C{f} with C{sys.stderr} redirected to C{stderr}.
    """
    (outer, sys.stderr) = (sys.stderr, stderr)
    try:
        return f(*args, **kwargs)
    finally:
        sys.stderr = outer


class Node:
    """
    Mock an AST node.
    """
    def __init__(self, lineno, col_offset=0):
        self.lineno = lineno
        self.col_offset = col_offset


class SysStreamCapturing:
    """Context manager capturing sys.stdin, sys.stdout and sys.stderr.

    The file handles are replaced with a StringIO object.
    """

    def __init__(self, stdin):
        self._stdin = io.StringIO(stdin or '', newline=os.linesep)

    def __enter__(self):
        self._orig_stdin = sys.stdin
        self._orig_stdout = sys.stdout
        self._orig_stderr = sys.stderr

        sys.stdin = self._stdin
        sys.stdout = self._stdout_stringio = io.StringIO(newline=os.linesep)
        sys.stderr = self._stderr_stringio = io.StringIO(newline=os.linesep)

        return self

    def __exit__(self, *args):
        self.output = self._stdout_stringio.getvalue()
        self.error = self._stderr_stringio.getvalue()

        sys.stdin = self._orig_stdin
        sys.stdout = self._orig_stdout
        sys.stderr = self._orig_stderr


class LoggingReporter:
    """
    Implementation of Reporter that just appends any error to a list.
    """

    def __init__(self, log):
        """
        Construct a C{LoggingReporter}.

        @param log: A list to append log messages to.
        """
        self.log = log

    def flake(self, message):
        self.log.append(('flake', str(message)))

    def unexpectedError(self, filename, message):
        self.log.append(('unexpectedError', filename, message))

    def syntaxError(self, filename, msg, lineno, offset, line):
        self.log.append(('syntaxError', filename, msg, lineno, offset, line))


class TestIterSourceCode(TestCase):
    """
    Tests for L{iterSourceCode}.
    """

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def makeEmptyFile(self, *parts):
        assert parts
        fpath = os.path.join(self.tempdir, *parts)
        open(fpath, 'a').close()
        return fpath

    def test_emptyDirectory(self):
        """
        There are no Python files in an empty directory.
        """
        self.assertEqual(list(iterSourceCode([self.tempdir])), [])

    def test_singleFile(self):
        """
        If the directory contains one Python file, C{iterSourceCode} will find
        it.
        """
        childpath = self.makeEmptyFile('foo.py')
        self.assertEqual(list(iterSourceCode([self.tempdir])), [childpath])

    def test_onlyPythonSource(self):
        """
        Files that are not Python source files are not included.
        """
        self.makeEmptyFile('foo.pyc')
        self.assertEqual(list(iterSourceCode([self.tempdir])), [])

    def test_recurses(self):
        """
        If the Python files are hidden deep down in child directories, we will
        find them.
        """
        os.mkdir(os.path.join(self.tempdir, 'foo'))
        apath = self.makeEmptyFile('foo', 'a.py')
        self.makeEmptyFile('foo', 'a.py~')
        os.mkdir(os.path.join(self.tempdir, 'bar'))
        bpath = self.makeEmptyFile('bar', 'b.py')
        cpath = self.makeEmptyFile('c.py')
        self.assertEqual(
            sorted(iterSourceCode([self.tempdir])),
            sorted([apath, bpath, cpath]))

    def test_shebang(self):
        """
        Find Python files that don't end with `.py`, but contain a Python
        shebang.
        """
        python = os.path.join(self.tempdir, 'a')
        with open(python, 'w') as fd:
            fd.write('#!/usr/bin/env python\n')

        self.makeEmptyFile('b')

        with open(os.path.join(self.tempdir, 'c'), 'w') as fd:
            fd.write('hello\nworld\n')

        python3 = os.path.join(self.tempdir, 'e')
        with open(python3, 'w') as fd:
            fd.write('#!/usr/bin/env python3\n')

        pythonw = os.path.join(self.tempdir, 'f')
        with open(pythonw, 'w') as fd:
            fd.write('#!/usr/bin/env pythonw\n')

        python3args = os.path.join(self.tempdir, 'g')
        with open(python3args, 'w') as fd:
            fd.write('#!/usr/bin/python3 -u\n')

        python3d = os.path.join(self.tempdir, 'i')
        with open(python3d, 'w') as fd:
            fd.write('#!/usr/local/bin/python3d\n')

        python38m = os.path.join(self.tempdir, 'j')
        with open(python38m, 'w') as fd:
            fd.write('#! /usr/bin/env python3.8m\n')

        # Should NOT be treated as Python source
        notfirst = os.path.join(self.tempdir, 'l')
        with open(notfirst, 'w') as fd:
            fd.write('#!/bin/sh\n#!/usr/bin/python\n')

        self.assertEqual(
            sorted(iterSourceCode([self.tempdir])),
            sorted([
                python, python3, pythonw, python3args, python3d,
                python38m,
            ]))

    def test_multipleDirectories(self):
        """
        L{iterSourceCode} can be given multiple directories.  It will recurse
        into each of them.
        """
        foopath = os.path.join(self.tempdir, 'foo')
        barpath = os.path.join(self.tempdir, 'bar')
        os.mkdir(foopath)
        apath = self.makeEmptyFile('foo', 'a.py')
        os.mkdir(barpath)
        bpath = self.makeEmptyFile('bar', 'b.py')
        self.assertEqual(
            sorted(iterSourceCode([foopath, barpath])),
            sorted([apath, bpath]))

    def test_explicitFiles(self):
        """
        If one of the paths given to L{iterSourceCode} is not a directory but
        a file, it will include that in its output.
        """
        epath = self.makeEmptyFile('e.py')
        self.assertEqual(list(iterSourceCode([epath])),
                         [epath])


class TestReporter(TestCase):
    """
    Tests for L{Reporter}.
    """

    def test_syntaxError(self):
        """
        C{syntaxError} reports that there was a syntax error in the source
        file.  It reports to the error stream and includes the filename, line
        number, error message, actual line of source and a caret pointing to
        where the error is.
        """
        err = io.StringIO()
        reporter = Reporter(None, err)
        reporter.syntaxError('foo.py', 'a problem', 3, 8, 'bad line of source')
        self.assertEqual(
            ("foo.py:3:8: a problem\n"
             "bad line of source\n"
             "       ^\n"),
            err.getvalue())

    def test_syntaxErrorNoOffset(self):
        """
        C{syntaxError} doesn't include a caret pointing to the error if
        C{offset} is passed as C{None}.
        """
        err = io.StringIO()
        reporter = Reporter(None, err)
        reporter.syntaxError('foo.py', 'a problem', 3, None,
                             'bad line of source')
        self.assertEqual(
            ("foo.py:3: a problem\n"
             "bad line of source\n"),
            err.getvalue())

    def test_syntaxErrorNoText(self):
        """
        C{syntaxError} doesn't include text or nonsensical offsets if C{text} is C{None}.

        This typically happens when reporting syntax errors from stdin.
        """
        err = io.StringIO()
        reporter = Reporter(None, err)
        reporter.syntaxError('<stdin>', 'a problem', 0, 0, None)
        self.assertEqual(("<stdin>:1:1: a problem\n"), err.getvalue())

    def test_multiLineSyntaxError(self):
        """
        If there's a multi-line syntax error, then we only report the last
        line.  The offset is adjusted so that it is relative to the start of
        the last line.
        """
        err = io.StringIO()
        lines = [
            'bad line of source',
            'more bad lines of source',
        ]
        reporter = Reporter(None, err)
        reporter.syntaxError('foo.py', 'a problem', 3, len(lines[0]) + 7,
                             '\n'.join(lines))
        self.assertEqual(
            ("foo.py:3:25: a problem\n" +
             lines[-1] + "\n" +
             " " * 24 + "^\n"),
            err.getvalue())

    def test_unexpectedError(self):
        """
        C{unexpectedError} reports an error processing a source file.
        """
        err = io.StringIO()
        reporter = Reporter(None, err)
        reporter.unexpectedError('source.py', 'error message')
        self.assertEqual('source.py: error message\n', err.getvalue())

    def test_flake(self):
        """
        C{flake} reports a code warning from Pyflakes.  It is exactly the
        str() of a L{pyflakes.messages.Message}.
        """
        out = io.StringIO()
        reporter = Reporter(out, None)
        message = UnusedImport('foo.py', Node(42), 'bar')
        reporter.flake(message)
        self.assertEqual(out.getvalue(), f"{message}\n")


class CheckTests(TestCase):
    """
    Tests for L{check} and L{checkPath} which check a file for flakes.
    """

    @contextlib.contextmanager
    def makeTempFile(self, content):
        """
        Make a temporary file containing C{content} and return a path to it.
        """
        fd, name = tempfile.mkstemp()
        try:
            with os.fdopen(fd, 'wb') as f:
                if not hasattr(content, 'decode'):
                    content = content.encode('ascii')
                f.write(content)
            yield name
        finally:
            os.remove(name)

    def assertHasErrors(self, path, errorList):
        """
        Assert that C{path} causes errors.

        @param path: A path to a file to check.
        @param errorList: A list of errors expected to be printed to stderr.
        """
        err = io.StringIO()
        count = withStderrTo(err, checkPath, path)
        self.assertEqual(
            (count, err.getvalue()), (len(errorList), ''.join(errorList)))

    def getErrors(self, path):
        """
        Get any warnings or errors reported by pyflakes for the file at C{path}.

        @param path: The path to a Python file on disk that pyflakes will check.
        @return: C{(count, log)}, where C{count} is the number of warnings or
            errors generated, and log is a list of those warnings, presented
            as structured data.  See L{LoggingReporter} for more details.
        """
        log = []
        reporter = LoggingReporter(log)
        count = checkPath(path, reporter)
        return count, log

    def test_legacyScript(self):
        from pyflakes.scripts import pyflakes as script_pyflakes
        self.assertIs(script_pyflakes.checkPath, checkPath)

    def test_missingTrailingNewline(self):
        """
        Source which doesn't end with a newline shouldn't cause any
        exception to be raised nor an error indicator to be returned by
        L{check}.
        """
        with self.makeTempFile("def foo():\n\tpass\n\t") as fName:
            self.assertHasErrors(fName, [])

    def test_checkPathNonExisting(self):
        """
        L{checkPath} handles non-existing files.
        """
        count, errors = self.getErrors('extremo')
        self.assertEqual(count, 1)
        self.assertEqual(
            errors,
            [('unexpectedError', 'extremo', 'No such file or directory')])

    def test_multilineSyntaxError(self):
        """
        Source which includes a syntax error which results in the raised
        L{SyntaxError.text} containing multiple lines of source are reported
        with only the last line of that source.
        """
        source = """\
def foo():
    '''

def bar():
    pass

def baz():
    '''quux'''
"""

        # Sanity check - SyntaxError.text should be multiple lines, if it
        # isn't, something this test was unprepared for has happened.
        def evaluate(source):
            exec(source)
        try:
            evaluate(source)
        except SyntaxError as e:
            if not PYPY and sys.version_info < (3, 10):
                self.assertTrue(e.text.count('\n') > 1)
        else:
            self.fail()

        with self.makeTempFile(source) as sourcePath:
            if PYPY:
                message = 'end of file (EOF) while scanning triple-quoted string literal'
            elif sys.version_info >= (3, 10):
                message = 'unterminated triple-quoted string literal (detected at line 8)'  # noqa: E501
            else:
                message = 'invalid syntax'

            if PYPY or sys.version_info >= (3, 10):
                column = 12
            else:
                column = 8
            self.assertHasErrors(
                sourcePath,
                ["""\
%s:8:%d: %s
    '''quux'''
%s^
""" % (sourcePath, column, message, ' ' * (column - 1))])

    def test_eofSyntaxError(self):
        """
        The error reported for source files which end prematurely causing a
        syntax error reflects the cause for the syntax error.
        """
        with self.makeTempFile("def foo(") as sourcePath:
            if PYPY:
                msg = 'parenthesis is never closed'
            elif sys.version_info >= (3, 10):
                msg = "'(' was never closed"
            else:
                msg = 'unexpected EOF while parsing'

            if PYPY or sys.version_info >= (3, 10):
                column = 8
            else:
                column = 9

            spaces = ' ' * (column - 1)
            expected = '{}:1:{}: {}\ndef foo(\n{}^\n'.format(
                sourcePath, column, msg, spaces
            )

            self.assertHasErrors(sourcePath, [expected])

    def test_eofSyntaxErrorWithTab(self):
        """
        The error reported for source files which end prematurely causing a
        syntax error reflects the cause for the syntax error.
        """
        with self.makeTempFile("if True:\n\tfoo =") as sourcePath:
            self.assertHasErrors(
                sourcePath,
                [f"""\
{sourcePath}:2:7: invalid syntax
\tfoo =
\t     ^
"""])

    def test_nonDefaultFollowsDefaultSyntaxError(self):
        """
        Source which has a non-default argument following a default argument
        should include the line number of the syntax error.  However these
        exceptions do not include an offset.
        """
        source = """\
def foo(bar=baz, bax):
    pass
"""
        with self.makeTempFile(source) as sourcePath:
            if sys.version_info >= (3, 12):
                msg = 'parameter without a default follows parameter with a default'  # noqa: E501
            else:
                msg = 'non-default argument follows default argument'

            if PYPY:
                column = 18
            elif sys.version_info >= (3, 10):
                column = 18
            else:
                column = 21
            last_line = ' ' * (column - 1) + '^\n'
            self.assertHasErrors(
                sourcePath,
                [f"""\
{sourcePath}:1:{column}: {msg}
def foo(bar=baz, bax):
{last_line}"""]
            )

    def test_nonKeywordAfterKeywordSyntaxError(self):
        """
        Source which has a non-keyword argument after a keyword argument should
        include the line number of the syntax error.  However these exceptions
        do not include an offset.
        """
        source = """\
foo(bar=baz, bax)
"""
        with self.makeTempFile(source) as sourcePath:
            last_line = ' ' * 16 + '^\n'
            self.assertHasErrors(
                sourcePath,
                [f"""\
{sourcePath}:1:17: positional argument follows keyword argument
foo(bar=baz, bax)
{last_line}"""])

    def test_invalidEscape(self):
        """
        The invalid escape syntax raises ValueError in Python 2
        """
        # ValueError: invalid \x escape
        with self.makeTempFile(r"foo = '\xyz'") as sourcePath:
            position_end = 1
            if PYPY:
                column = 7
            elif sys.version_info < (3, 12):
                column = 13
            else:
                column = 7

            last_line = '%s^\n' % (' ' * (column - 1))

            decoding_error = """\
%s:1:%d: (unicode error) 'unicodeescape' codec can't decode bytes \
in position 0-%d: truncated \\xXX escape
foo = '\\xyz'
%s""" % (sourcePath, column, position_end, last_line)

            self.assertHasErrors(
                sourcePath, [decoding_error])

    @skipIf(sys.platform == 'win32', 'unsupported on Windows')
    def test_permissionDenied(self):
        """
        If the source file is not readable, this is reported on standard
        error.
        """
        if os.getuid() == 0:
            self.skipTest('root user can access all files regardless of '
                          'permissions')
        with self.makeTempFile('') as sourcePath:
            os.chmod(sourcePath, 0)
            count, errors = self.getErrors(sourcePath)
            self.assertEqual(count, 1)
            self.assertEqual(
                errors,
                [('unexpectedError', sourcePath, "Permission denied")])

    def test_pyflakesWarning(self):
        """
        If the source file has a pyflakes warning, this is reported as a
        'flake'.
        """
        with self.makeTempFile("import foo") as sourcePath:
            count, errors = self.getErrors(sourcePath)
            self.assertEqual(count, 1)
            self.assertEqual(
                errors, [('flake', str(UnusedImport(sourcePath, Node(1), 'foo')))])

    def test_encodedFileUTF8(self):
        """
        If source file declares the correct encoding, no error is reported.
        """
        SNOWMAN = chr(0x2603)
        source = ("""\
# coding: utf-8
x = "%s"
""" % SNOWMAN).encode('utf-8')
        with self.makeTempFile(source) as sourcePath:
            self.assertHasErrors(sourcePath, [])

    def test_CRLFLineEndings(self):
        """
        Source files with Windows CR LF line endings are parsed successfully.
        """
        with self.makeTempFile("x = 42\r\n") as sourcePath:
            self.assertHasErrors(sourcePath, [])

    def test_misencodedFileUTF8(self):
        """
        If a source file contains bytes which cannot be decoded, this is
        reported on stderr.
        """
        SNOWMAN = chr(0x2603)
        source = ("""\
# coding: ascii
x = "%s"
""" % SNOWMAN).encode('utf-8')
        with self.makeTempFile(source) as sourcePath:
            self.assertHasErrors(
                sourcePath,
                [f"{sourcePath}:1:1: 'ascii' codec can't decode byte 0xe2 in position 21: ordinal not in range(128)\n"])  # noqa: E501

    def test_misencodedFileUTF16(self):
        """
        If a source file contains bytes which cannot be decoded, this is
        reported on stderr.
        """
        SNOWMAN = chr(0x2603)
        source = ("""\
# coding: ascii
x = "%s"
""" % SNOWMAN).encode('utf-16')
        with self.makeTempFile(source) as sourcePath:
            if sys.version_info < (3, 11, 4):
                expected = f"{sourcePath}: problem decoding source\n"
            else:
                expected = f"{sourcePath}:1: source code string cannot contain null bytes\n"  # noqa: E501

            self.assertHasErrors(sourcePath, [expected])

    def test_checkRecursive(self):
        """
        L{checkRecursive} descends into each directory, finding Python files
        and reporting problems.
        """
        tempdir = tempfile.mkdtemp()
        try:
            os.mkdir(os.path.join(tempdir, 'foo'))
            file1 = os.path.join(tempdir, 'foo', 'bar.py')
            with open(file1, 'wb') as fd:
                fd.write(b"import baz\n")
            file2 = os.path.join(tempdir, 'baz.py')
            with open(file2, 'wb') as fd:
                fd.write(b"import contraband")
            log = []
            reporter = LoggingReporter(log)
            warnings = checkRecursive([tempdir], reporter)
            self.assertEqual(warnings, 2)
            self.assertEqual(
                sorted(log),
                sorted([('flake', str(UnusedImport(file1, Node(1), 'baz'))),
                        ('flake',
                         str(UnusedImport(file2, Node(1), 'contraband')))]))
        finally:
            shutil.rmtree(tempdir)

    def test_stdinReportsErrors(self):
        """
        L{check} reports syntax errors from stdin
        """
        source = "max(1 for i in range(10), key=lambda x: x+1)\n"
        err = io.StringIO()
        count = withStderrTo(err, check, source, "<stdin>")
        self.assertEqual(count, 1)
        errlines = err.getvalue().split("\n")[:-1]

        expected_error = [
            "<stdin>:1:5: Generator expression must be parenthesized",
            "max(1 for i in range(10), key=lambda x: x+1)",
            "    ^",
        ]
        self.assertEqual(errlines, expected_error)


class IntegrationTests(TestCase):
    """
    Tests of the pyflakes script that actually spawn the script.
    """
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.tempfilepath = os.path.join(self.tempdir, 'temp')

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def getPyflakesBinary(self):
        """
        Return the path to the pyflakes binary.
        """
        import pyflakes
        package_dir = os.path.dirname(pyflakes.__file__)
        return os.path.join(package_dir, '..', 'bin', 'pyflakes')

    def runPyflakes(self, paths, stdin=None):
        """
        Launch a subprocess running C{pyflakes}.

        @param paths: Command-line arguments to pass to pyflakes.
        @param stdin: Text to use as stdin.
        @return: C{(returncode, stdout, stderr)} of the completed pyflakes
            process.
        """
        env = dict(os.environ)
        env['PYTHONPATH'] = os.pathsep.join(sys.path)
        command = [sys.executable, self.getPyflakesBinary()]
        command.extend(paths)
        if stdin:
            p = subprocess.Popen(command, env=env, stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (stdout, stderr) = p.communicate(stdin.encode('ascii'))
        else:
            p = subprocess.Popen(command, env=env,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (stdout, stderr) = p.communicate()
        rv = p.wait()
        stdout = stdout.decode('utf-8')
        stderr = stderr.decode('utf-8')
        return (stdout, stderr, rv)

    def test_goodFile(self):
        """
        When a Python source file is all good, the return code is zero and no
        messages are printed to either stdout or stderr.
        """
        open(self.tempfilepath, 'a').close()
        d = self.runPyflakes([self.tempfilepath])
        self.assertEqual(d, ('', '', 0))

    def test_fileWithFlakes(self):
        """
        When a Python source file has warnings, the return code is non-zero
        and the warnings are printed to stdout.
        """
        with open(self.tempfilepath, 'wb') as fd:
            fd.write(b"import contraband\n")
        d = self.runPyflakes([self.tempfilepath])
        expected = UnusedImport(self.tempfilepath, Node(1), 'contraband')
        self.assertEqual(d, (f"{expected}{os.linesep}", '', 1))

    def test_errors_io(self):
        """
        When pyflakes finds errors with the files it's given, (if they don't
        exist, say), then the return code is non-zero and the errors are
        printed to stderr.
        """
        d = self.runPyflakes([self.tempfilepath])
        error_msg = '{}: No such file or directory{}'.format(self.tempfilepath,
                                                             os.linesep)
        self.assertEqual(d, ('', error_msg, 1))

    def test_errors_syntax(self):
        """
        When pyflakes finds errors with the files it's given, (if they don't
        exist, say), then the return code is non-zero and the errors are
        printed to stderr.
        """
        with open(self.tempfilepath, 'wb') as fd:
            fd.write(b"import")
        d = self.runPyflakes([self.tempfilepath])

        if sys.version_info >= (3, 13):
            message = "Expected one or more names after 'import'"
        else:
            message = 'invalid syntax'

        error_msg = '{0}:1:7: {1}{2}import{2}      ^{2}'.format(
            self.tempfilepath, message, os.linesep)
        self.assertEqual(d, ('', error_msg, 1))

    def test_readFromStdin(self):
        """
        If no arguments are passed to C{pyflakes} then it reads from stdin.
        """
        d = self.runPyflakes([], stdin='import contraband')
        expected = UnusedImport('<stdin>', Node(1), 'contraband')
        self.assertEqual(d, (f"{expected}{os.linesep}", '', 1))


class TestMain(IntegrationTests):
    """
    Tests of the pyflakes main function.
    """
    def runPyflakes(self, paths, stdin=None):
        try:
            with SysStreamCapturing(stdin) as capture:
                main(args=paths)
        except SystemExit as e:
            self.assertIsInstance(e.code, bool)
            rv = int(e.code)
            return (capture.output, capture.error, rv)
        else:
            raise RuntimeError('SystemExit not raised')
