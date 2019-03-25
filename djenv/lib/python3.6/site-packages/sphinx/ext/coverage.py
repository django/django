# -*- coding: utf-8 -*-
"""
    sphinx.ext.coverage
    ~~~~~~~~~~~~~~~~~~~

    Check Python modules and C API for coverage.  Mostly written by Josip
    Dzolonga for the Google Highly Open Participation contest.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import glob
import inspect
import re
from os import path

from six import iteritems
from six.moves import cPickle as pickle

import sphinx
from sphinx.builders import Builder
from sphinx.locale import __
from sphinx.util import logging
from sphinx.util.inspect import safe_getattr

if False:
    # For type annotation
    from typing import Any, Callable, Dict, IO, List, Pattern, Set, Tuple  # NOQA
    from sphinx.application import Sphinx  # NOQA

logger = logging.getLogger(__name__)


# utility
def write_header(f, text, char='-'):
    # type:(IO, unicode, unicode) -> None
    f.write(text + '\n')
    f.write(char * len(text) + '\n')


def compile_regex_list(name, exps):
    # type: (unicode, unicode) -> List[Pattern]
    lst = []
    for exp in exps:
        try:
            lst.append(re.compile(exp))
        except Exception:
            logger.warning(__('invalid regex %r in %s'), exp, name)
    return lst


class CoverageBuilder(Builder):
    """
    Evaluates coverage of code in the documentation.
    """
    name = 'coverage'
    epilog = __('Testing of coverage in the sources finished, look at the '
                'results in %(outdir)s' + path.sep + 'python.txt.')

    def init(self):
        # type: () -> None
        self.c_sourcefiles = []  # type: List[unicode]
        for pattern in self.config.coverage_c_path:
            pattern = path.join(self.srcdir, pattern)
            self.c_sourcefiles.extend(glob.glob(pattern))

        self.c_regexes = []  # type: List[Tuple[unicode, Pattern]]
        for (name, exp) in self.config.coverage_c_regexes.items():
            try:
                self.c_regexes.append((name, re.compile(exp)))
            except Exception:
                logger.warning(__('invalid regex %r in coverage_c_regexes'), exp)

        self.c_ignorexps = {}  # type: Dict[unicode, List[Pattern]]
        for (name, exps) in iteritems(self.config.coverage_ignore_c_items):
            self.c_ignorexps[name] = compile_regex_list('coverage_ignore_c_items',
                                                        exps)
        self.mod_ignorexps = compile_regex_list('coverage_ignore_modules',
                                                self.config.coverage_ignore_modules)
        self.cls_ignorexps = compile_regex_list('coverage_ignore_classes',
                                                self.config.coverage_ignore_classes)
        self.fun_ignorexps = compile_regex_list('coverage_ignore_functions',
                                                self.config.coverage_ignore_functions)

    def get_outdated_docs(self):
        # type: () -> unicode
        return 'coverage overview'

    def write(self, *ignored):
        # type: (Any) -> None
        self.py_undoc = {}  # type: Dict[unicode, Dict[unicode, Any]]
        self.build_py_coverage()
        self.write_py_coverage()

        self.c_undoc = {}  # type: Dict[unicode, Set[Tuple[unicode, unicode]]]
        self.build_c_coverage()
        self.write_c_coverage()

    def build_c_coverage(self):
        # type: () -> None
        # Fetch all the info from the header files
        c_objects = self.env.domaindata['c']['objects']
        for filename in self.c_sourcefiles:
            undoc = set()  # type: Set[Tuple[unicode, unicode]]
            with open(filename, 'r') as f:
                for line in f:
                    for key, regex in self.c_regexes:
                        match = regex.match(line)
                        if match:
                            name = match.groups()[0]
                            if name not in c_objects:
                                for exp in self.c_ignorexps.get(key, []):
                                    if exp.match(name):
                                        break
                                else:
                                    undoc.add((key, name))
                            continue
            if undoc:
                self.c_undoc[filename] = undoc

    def write_c_coverage(self):
        # type: () -> None
        output_file = path.join(self.outdir, 'c.txt')
        with open(output_file, 'w') as op:
            if self.config.coverage_write_headline:
                write_header(op, 'Undocumented C API elements', '=')
            op.write('\n')

            for filename, undoc in iteritems(self.c_undoc):
                write_header(op, filename)
                for typ, name in sorted(undoc):
                    op.write(' * %-50s [%9s]\n' % (name, typ))
                op.write('\n')

    def build_py_coverage(self):
        # type: () -> None
        objects = self.env.domaindata['py']['objects']
        modules = self.env.domaindata['py']['modules']

        skip_undoc = self.config.coverage_skip_undoc_in_source

        for mod_name in modules:
            ignore = False
            for exp in self.mod_ignorexps:
                if exp.match(mod_name):
                    ignore = True
                    break
            if ignore:
                continue

            try:
                mod = __import__(mod_name, fromlist=['foo'])
            except ImportError as err:
                logger.warning(__('module %s could not be imported: %s'), mod_name, err)
                self.py_undoc[mod_name] = {'error': err}
                continue

            funcs = []
            classes = {}  # type: Dict[unicode, List[unicode]]

            for name, obj in inspect.getmembers(mod):
                # diverse module attributes are ignored:
                if name[0] == '_':
                    # begins in an underscore
                    continue
                if not hasattr(obj, '__module__'):
                    # cannot be attributed to a module
                    continue
                if obj.__module__ != mod_name:
                    # is not defined in this module
                    continue

                full_name = '%s.%s' % (mod_name, name)

                if inspect.isfunction(obj):
                    if full_name not in objects:
                        for exp in self.fun_ignorexps:
                            if exp.match(name):
                                break
                        else:
                            if skip_undoc and not obj.__doc__:
                                continue
                            funcs.append(name)
                elif inspect.isclass(obj):
                    for exp in self.cls_ignorexps:
                        if exp.match(name):
                            break
                    else:
                        if full_name not in objects:
                            if skip_undoc and not obj.__doc__:
                                continue
                            # not documented at all
                            classes[name] = []
                            continue

                        attrs = []  # type: List[unicode]

                        for attr_name in dir(obj):
                            if attr_name not in obj.__dict__:
                                continue
                            try:
                                attr = safe_getattr(obj, attr_name)
                            except AttributeError:
                                continue
                            if not (inspect.ismethod(attr) or
                                    inspect.isfunction(attr)):
                                continue
                            if attr_name[0] == '_':
                                # starts with an underscore, ignore it
                                continue
                            if skip_undoc and not attr.__doc__:
                                # skip methods without docstring if wished
                                continue

                            full_attr_name = '%s.%s' % (full_name, attr_name)
                            if full_attr_name not in objects:
                                attrs.append(attr_name)

                        if attrs:
                            # some attributes are undocumented
                            classes[name] = attrs

            self.py_undoc[mod_name] = {'funcs': funcs, 'classes': classes}

    def write_py_coverage(self):
        # type: () -> None
        output_file = path.join(self.outdir, 'python.txt')
        failed = []
        with open(output_file, 'w') as op:
            if self.config.coverage_write_headline:
                write_header(op, 'Undocumented Python objects', '=')
            keys = sorted(self.py_undoc.keys())
            for name in keys:
                undoc = self.py_undoc[name]
                if 'error' in undoc:
                    failed.append((name, undoc['error']))
                else:
                    if not undoc['classes'] and not undoc['funcs']:
                        continue

                    write_header(op, name)
                    if undoc['funcs']:
                        op.write('Functions:\n')
                        op.writelines(' * %s\n' % x for x in undoc['funcs'])
                        op.write('\n')
                    if undoc['classes']:
                        op.write('Classes:\n')
                        for name, methods in sorted(
                                iteritems(undoc['classes'])):
                            if not methods:
                                op.write(' * %s\n' % name)
                            else:
                                op.write(' * %s -- missing methods:\n\n' % name)
                                op.writelines('   - %s\n' % x for x in methods)
                        op.write('\n')

            if failed:
                write_header(op, 'Modules that failed to import')
                op.writelines(' * %s -- %s\n' % x for x in failed)

    def finish(self):
        # type: () -> None
        # dump the coverage data to a pickle file too
        picklepath = path.join(self.outdir, 'undoc.pickle')
        with open(picklepath, 'wb') as dumpfile:
            pickle.dump((self.py_undoc, self.c_undoc), dumpfile)


def setup(app):
    # type: (Sphinx) -> Dict[unicode, Any]
    app.add_builder(CoverageBuilder)
    app.add_config_value('coverage_ignore_modules', [], False)
    app.add_config_value('coverage_ignore_functions', [], False)
    app.add_config_value('coverage_ignore_classes', [], False)
    app.add_config_value('coverage_c_path', [], False)
    app.add_config_value('coverage_c_regexes', {}, False)
    app.add_config_value('coverage_ignore_c_items', {}, False)
    app.add_config_value('coverage_write_headline', True, False)
    app.add_config_value('coverage_skip_undoc_in_source', False, False)
    return {'version': sphinx.__display_version__, 'parallel_read_safe': True}
