"""Check Python modules and C API for coverage.

Mostly written by Josip Dzolonga for the Google Highly Open Participation
contest.
"""

from __future__ import annotations

import glob
import inspect
import pickle
import re
import sys
from importlib import import_module
from os import path
from typing import IO, TYPE_CHECKING, Any, TextIO

import sphinx
from sphinx.builders import Builder
from sphinx.locale import __
from sphinx.util import logging
from sphinx.util.console import red  # type: ignore[attr-defined]
from sphinx.util.inspect import safe_getattr

if TYPE_CHECKING:
    from collections.abc import Iterator

    from sphinx.application import Sphinx

logger = logging.getLogger(__name__)


# utility
def write_header(f: IO[str], text: str, char: str = '-') -> None:
    f.write(text + '\n')
    f.write(char * len(text) + '\n\n')


def compile_regex_list(name: str, exps: str) -> list[re.Pattern[str]]:
    lst = []
    for exp in exps:
        try:
            lst.append(re.compile(exp))
        except Exception:
            logger.warning(__('invalid regex %r in %s'), exp, name)
    return lst


def _write_table(table: list[list[str]]) -> Iterator[str]:
    sizes = [max(len(x[column]) for x in table) + 1 for column in range(len(table[0]))]

    yield _add_line(sizes, '-')
    yield from _add_row(sizes, table[0], '=')

    for row in table[1:]:
        yield from _add_row(sizes, row, '-')


def _add_line(sizes: list[int], separator: str) -> str:
    return '+' + ''.join((separator * (size + 1)) + '+' for size in sizes)


def _add_row(col_widths: list[int], columns: list[str], separator: str) -> Iterator[str]:
    yield ''.join(f'| {column: <{col_widths[i]}}' for i, column in enumerate(columns)) + '|'
    yield _add_line(col_widths, separator)


class CoverageBuilder(Builder):
    """
    Evaluates coverage of code in the documentation.
    """
    name = 'coverage'
    epilog = __('Testing of coverage in the sources finished, look at the '
                'results in %(outdir)s' + path.sep + 'python.txt.')

    def init(self) -> None:
        self.c_sourcefiles: list[str] = []
        for pattern in self.config.coverage_c_path:
            pattern = path.join(self.srcdir, pattern)
            self.c_sourcefiles.extend(glob.glob(pattern))

        self.c_regexes: list[tuple[str, re.Pattern[str]]] = []
        for (name, exp) in self.config.coverage_c_regexes.items():
            try:
                self.c_regexes.append((name, re.compile(exp)))
            except Exception:
                logger.warning(__('invalid regex %r in coverage_c_regexes'), exp)

        self.c_ignorexps: dict[str, list[re.Pattern[str]]] = {}
        for (name, exps) in self.config.coverage_ignore_c_items.items():
            self.c_ignorexps[name] = compile_regex_list('coverage_ignore_c_items',
                                                        exps)
        self.mod_ignorexps = compile_regex_list('coverage_ignore_modules',
                                                self.config.coverage_ignore_modules)
        self.cls_ignorexps = compile_regex_list('coverage_ignore_classes',
                                                self.config.coverage_ignore_classes)
        self.fun_ignorexps = compile_regex_list('coverage_ignore_functions',
                                                self.config.coverage_ignore_functions)
        self.py_ignorexps = compile_regex_list('coverage_ignore_pyobjects',
                                               self.config.coverage_ignore_pyobjects)

    def get_outdated_docs(self) -> str:
        return 'coverage overview'

    def write(self, *ignored: Any) -> None:
        self.py_undoc: dict[str, dict[str, Any]] = {}
        self.py_undocumented: dict[str, set[str]] = {}
        self.py_documented: dict[str, set[str]] = {}
        self.build_py_coverage()
        self.write_py_coverage()

        self.c_undoc: dict[str, set[tuple[str, str]]] = {}
        self.build_c_coverage()
        self.write_c_coverage()

    def build_c_coverage(self) -> None:
        c_objects = {}
        for obj in self.env.domains['c'].get_objects():
            c_objects[obj[2]] = obj[1]
        for filename in self.c_sourcefiles:
            undoc: set[tuple[str, str]] = set()
            with open(filename, encoding="utf-8") as f:
                for line in f:
                    for key, regex in self.c_regexes:
                        match = regex.match(line)
                        if match:
                            name = match.groups()[0]
                            if key not in c_objects:
                                undoc.add((key, name))
                                continue

                            if name not in c_objects[key]:
                                for exp in self.c_ignorexps.get(key, []):
                                    if exp.match(name):
                                        break
                                else:
                                    undoc.add((key, name))
                            continue
            if undoc:
                self.c_undoc[filename] = undoc

    def write_c_coverage(self) -> None:
        output_file = path.join(self.outdir, 'c.txt')
        with open(output_file, 'w', encoding="utf-8") as op:
            if self.config.coverage_write_headline:
                write_header(op, 'Undocumented C API elements', '=')
            op.write('\n')

            for filename, undoc in self.c_undoc.items():
                write_header(op, filename)
                for typ, name in sorted(undoc):
                    op.write(' * %-50s [%9s]\n' % (name, typ))
                    if self.config.coverage_show_missing_items:
                        if self.app.quiet or self.app.warningiserror:
                            logger.warning(__('undocumented c api: %s [%s] in file %s'),
                                           name, typ, filename)
                        else:
                            logger.info(red('undocumented  ') + 'c   ' + 'api       ' +
                                        '%-30s' % (name + " [%9s]" % typ) +
                                        red(' - in file ') + filename)
                op.write('\n')

    def ignore_pyobj(self, full_name: str) -> bool:
        return any(
            exp.search(full_name)
            for exp in self.py_ignorexps
        )

    def build_py_coverage(self) -> None:
        objects = self.env.domaindata['py']['objects']
        modules = self.env.domaindata['py']['modules']

        skip_undoc = self.config.coverage_skip_undoc_in_source

        for mod_name in modules:
            ignore = False
            for exp in self.mod_ignorexps:
                if exp.match(mod_name):
                    ignore = True
                    break
            if ignore or self.ignore_pyobj(mod_name):
                continue

            try:
                mod = import_module(mod_name)
            except ImportError as err:
                logger.warning(__('module %s could not be imported: %s'), mod_name, err)
                self.py_undoc[mod_name] = {'error': err}
                continue

            documented_objects: set[str] = set()
            undocumented_objects: set[str] = set()

            funcs = []
            classes: dict[str, list[str]] = {}

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

                full_name = f'{mod_name}.{name}'
                if self.ignore_pyobj(full_name):
                    continue

                if inspect.isfunction(obj):
                    if full_name not in objects:
                        for exp in self.fun_ignorexps:
                            if exp.match(name):
                                break
                        else:
                            if skip_undoc and not obj.__doc__:
                                continue
                            funcs.append(name)
                            undocumented_objects.add(full_name)
                    else:
                        documented_objects.add(full_name)
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

                        attrs: list[str] = []

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
                            full_attr_name = f'{full_name}.{attr_name}'
                            if self.ignore_pyobj(full_attr_name):
                                continue
                            if full_attr_name not in objects:
                                attrs.append(attr_name)
                                undocumented_objects.add(full_attr_name)
                            else:
                                documented_objects.add(full_attr_name)

                        if attrs:
                            # some attributes are undocumented
                            classes[name] = attrs

            self.py_undoc[mod_name] = {'funcs': funcs, 'classes': classes}
            self.py_undocumented[mod_name] = undocumented_objects
            self.py_documented[mod_name] = documented_objects

    def _write_py_statistics(self, op: TextIO) -> None:
        """ Outputs the table of ``op``."""
        all_modules = set(self.py_documented.keys()).union(
            set(self.py_undocumented.keys()))
        all_objects: set[str] = set()
        all_documented_objects: set[str] = set()
        for module in all_modules:
            all_module_objects = self.py_documented[module].union(self.py_undocumented[module])
            all_objects = all_objects.union(all_module_objects)
            all_documented_objects = all_documented_objects.union(self.py_documented[module])

        # prepare tabular
        table = [['Module', 'Coverage', 'Undocumented']]
        for module in all_modules:
            module_objects = self.py_documented[module].union(self.py_undocumented[module])
            if len(module_objects):
                value = 100.0 * len(self.py_documented[module]) / len(module_objects)
            else:
                value = 100.0

            table.append([module, '%.2f%%' % value, '%d' % len(self.py_undocumented[module])])
        table.append([
            'TOTAL',
            f'{100 * len(all_documented_objects) / len(all_objects):.2f}%',
            f'{len(all_objects) - len(all_documented_objects)}',
        ])

        for line in _write_table(table):
            op.write(f'{line}\n')

    def write_py_coverage(self) -> None:
        output_file = path.join(self.outdir, 'python.txt')
        failed = []
        with open(output_file, 'w', encoding="utf-8") as op:
            if self.config.coverage_write_headline:
                write_header(op, 'Undocumented Python objects', '=')

            if self.config.coverage_statistics_to_stdout:
                self._write_py_statistics(sys.stdout)

            if self.config.coverage_statistics_to_report:
                write_header(op, 'Statistics')
                self._write_py_statistics(op)
                op.write('\n')

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
                        if self.config.coverage_show_missing_items:
                            if self.app.quiet or self.app.warningiserror:
                                for func in undoc['funcs']:
                                    logger.warning(
                                        __('undocumented python function: %s :: %s'),
                                        name, func)
                            else:
                                for func in undoc['funcs']:
                                    logger.info(red('undocumented  ') + 'py  ' + 'function  ' +
                                                '%-30s' % func + red(' - in module ') + name)
                        op.write('\n')
                    if undoc['classes']:
                        op.write('Classes:\n')
                        for class_name, methods in sorted(
                                undoc['classes'].items()):
                            if not methods:
                                op.write(' * %s\n' % class_name)
                                if self.config.coverage_show_missing_items:
                                    if self.app.quiet or self.app.warningiserror:
                                        logger.warning(
                                            __('undocumented python class: %s :: %s'),
                                            name, class_name)
                                    else:
                                        logger.info(red('undocumented  ') + 'py  ' +
                                                    'class     ' + '%-30s' % class_name +
                                                    red(' - in module ') + name)
                            else:
                                op.write(' * %s -- missing methods:\n\n' % class_name)
                                op.writelines('   - %s\n' % x for x in methods)
                                if self.config.coverage_show_missing_items:
                                    if self.app.quiet or self.app.warningiserror:
                                        for meth in methods:
                                            logger.warning(
                                                __('undocumented python method:' +
                                                   ' %s :: %s :: %s'),
                                                name, class_name, meth)
                                    else:
                                        for meth in methods:
                                            logger.info(red('undocumented  ') + 'py  ' +
                                                        'method    ' + '%-30s' %
                                                        (class_name + '.' + meth) +
                                                        red(' - in module ') + name)
                        op.write('\n')

            if failed:
                write_header(op, 'Modules that failed to import')
                op.writelines(' * %s -- %s\n' % x for x in failed)

    def finish(self) -> None:
        # dump the coverage data to a pickle file too
        picklepath = path.join(self.outdir, 'undoc.pickle')
        with open(picklepath, 'wb') as dumpfile:
            pickle.dump((self.py_undoc, self.c_undoc,
                         self.py_undocumented, self.py_documented), dumpfile)


def setup(app: Sphinx) -> dict[str, Any]:
    app.add_builder(CoverageBuilder)
    app.add_config_value('coverage_ignore_modules', [], False)
    app.add_config_value('coverage_ignore_functions', [], False)
    app.add_config_value('coverage_ignore_classes', [], False)
    app.add_config_value('coverage_ignore_pyobjects', [], False)
    app.add_config_value('coverage_c_path', [], False)
    app.add_config_value('coverage_c_regexes', {}, False)
    app.add_config_value('coverage_ignore_c_items', {}, False)
    app.add_config_value('coverage_write_headline', True, False)
    app.add_config_value('coverage_statistics_to_report', True, False, (bool,))
    app.add_config_value('coverage_statistics_to_stdout', True, False, (bool,))
    app.add_config_value('coverage_skip_undoc_in_source', False, False)
    app.add_config_value('coverage_show_missing_items', False, False)
    return {'version': sphinx.__display_version__, 'parallel_read_safe': True}
