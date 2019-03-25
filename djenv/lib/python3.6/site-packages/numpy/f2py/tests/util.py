"""
Utility functions for

- building and importing modules on test time, using a temporary location
- detecting if compilers are present

"""
from __future__ import division, absolute_import, print_function

import os
import sys
import subprocess
import tempfile
import shutil
import atexit
import textwrap
import re
import pytest

from numpy.compat import asbytes, asstr
from numpy.testing import temppath
from importlib import import_module

try:
    from hashlib import md5
except ImportError:
    from md5 import new as md5  # noqa: F401

#
# Maintaining a temporary module directory
#

_module_dir = None


def _cleanup():
    global _module_dir
    if _module_dir is not None:
        try:
            sys.path.remove(_module_dir)
        except ValueError:
            pass
        try:
            shutil.rmtree(_module_dir)
        except (IOError, OSError):
            pass
        _module_dir = None


def get_module_dir():
    global _module_dir
    if _module_dir is None:
        _module_dir = tempfile.mkdtemp()
        atexit.register(_cleanup)
        if _module_dir not in sys.path:
            sys.path.insert(0, _module_dir)
    return _module_dir


def get_temp_module_name():
    # Assume single-threaded, and the module dir usable only by this thread
    d = get_module_dir()
    for j in range(5403, 9999999):
        name = "_test_ext_module_%d" % j
        fn = os.path.join(d, name)
        if name not in sys.modules and not os.path.isfile(fn + '.py'):
            return name
    raise RuntimeError("Failed to create a temporary module name")


def _memoize(func):
    memo = {}

    def wrapper(*a, **kw):
        key = repr((a, kw))
        if key not in memo:
            try:
                memo[key] = func(*a, **kw)
            except Exception as e:
                memo[key] = e
                raise
        ret = memo[key]
        if isinstance(ret, Exception):
            raise ret
        return ret
    wrapper.__name__ = func.__name__
    return wrapper

#
# Building modules
#


@_memoize
def build_module(source_files, options=[], skip=[], only=[], module_name=None):
    """
    Compile and import a f2py module, built from the given files.

    """

    code = ("import sys; sys.path = %s; import numpy.f2py as f2py2e; "
            "f2py2e.main()" % repr(sys.path))

    d = get_module_dir()

    # Copy files
    dst_sources = []
    for fn in source_files:
        if not os.path.isfile(fn):
            raise RuntimeError("%s is not a file" % fn)
        dst = os.path.join(d, os.path.basename(fn))
        shutil.copyfile(fn, dst)
        dst_sources.append(dst)

        fn = os.path.join(os.path.dirname(fn), '.f2py_f2cmap')
        if os.path.isfile(fn):
            dst = os.path.join(d, os.path.basename(fn))
            if not os.path.isfile(dst):
                shutil.copyfile(fn, dst)

    # Prepare options
    if module_name is None:
        module_name = get_temp_module_name()
    f2py_opts = ['-c', '-m', module_name] + options + dst_sources
    if skip:
        f2py_opts += ['skip:'] + skip
    if only:
        f2py_opts += ['only:'] + only

    # Build
    cwd = os.getcwd()
    try:
        os.chdir(d)
        cmd = [sys.executable, '-c', code] + f2py_opts
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT)
        out, err = p.communicate()
        if p.returncode != 0:
            raise RuntimeError("Running f2py failed: %s\n%s"
                               % (cmd[4:], asstr(out)))
    finally:
        os.chdir(cwd)

        # Partial cleanup
        for fn in dst_sources:
            os.unlink(fn)

    # Import
    return import_module(module_name)


@_memoize
def build_code(source_code, options=[], skip=[], only=[], suffix=None,
               module_name=None):
    """
    Compile and import Fortran code using f2py.

    """
    if suffix is None:
        suffix = '.f'
    with temppath(suffix=suffix) as path:
        with open(path, 'w') as f:
            f.write(source_code)
        return build_module([path], options=options, skip=skip, only=only,
                            module_name=module_name)

#
# Check if compilers are available at all...
#

_compiler_status = None


def _get_compiler_status():
    global _compiler_status
    if _compiler_status is not None:
        return _compiler_status

    _compiler_status = (False, False, False)

    # XXX: this is really ugly. But I don't know how to invoke Distutils
    #      in a safer way...
    code = """
import os
import sys
sys.path = %(syspath)s

def configuration(parent_name='',top_path=None):
    global config
    from numpy.distutils.misc_util import Configuration
    config = Configuration('', parent_name, top_path)
    return config

from numpy.distutils.core import setup
setup(configuration=configuration)

config_cmd = config.get_config_cmd()
have_c = config_cmd.try_compile('void foo() {}')
print('COMPILERS:%%d,%%d,%%d' %% (have_c,
                                  config.have_f77c(),
                                  config.have_f90c()))
sys.exit(99)
"""
    code = code % dict(syspath=repr(sys.path))

    with temppath(suffix='.py') as script:
        with open(script, 'w') as f:
            f.write(code)

        cmd = [sys.executable, script, 'config']
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT)
        out, err = p.communicate()

    m = re.search(br'COMPILERS:(\d+),(\d+),(\d+)', out)
    if m:
        _compiler_status = (bool(int(m.group(1))), bool(int(m.group(2))),
                            bool(int(m.group(3))))
    # Finished
    return _compiler_status


def has_c_compiler():
    return _get_compiler_status()[0]


def has_f77_compiler():
    return _get_compiler_status()[1]


def has_f90_compiler():
    return _get_compiler_status()[2]

#
# Building with distutils
#


@_memoize
def build_module_distutils(source_files, config_code, module_name, **kw):
    """
    Build a module via distutils and import it.

    """
    from numpy.distutils.misc_util import Configuration
    from numpy.distutils.core import setup

    d = get_module_dir()

    # Copy files
    dst_sources = []
    for fn in source_files:
        if not os.path.isfile(fn):
            raise RuntimeError("%s is not a file" % fn)
        dst = os.path.join(d, os.path.basename(fn))
        shutil.copyfile(fn, dst)
        dst_sources.append(dst)

    # Build script
    config_code = textwrap.dedent(config_code).replace("\n", "\n    ")

    code = """\
import os
import sys
sys.path = %(syspath)s

def configuration(parent_name='',top_path=None):
    from numpy.distutils.misc_util import Configuration
    config = Configuration('', parent_name, top_path)
    %(config_code)s
    return config

if __name__ == "__main__":
    from numpy.distutils.core import setup
    setup(configuration=configuration)
""" % dict(config_code=config_code, syspath=repr(sys.path))

    script = os.path.join(d, get_temp_module_name() + '.py')
    dst_sources.append(script)
    f = open(script, 'wb')
    f.write(asbytes(code))
    f.close()

    # Build
    cwd = os.getcwd()
    try:
        os.chdir(d)
        cmd = [sys.executable, script, 'build_ext', '-i']
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT)
        out, err = p.communicate()
        if p.returncode != 0:
            raise RuntimeError("Running distutils build failed: %s\n%s"
                               % (cmd[4:], asstr(out)))
    finally:
        os.chdir(cwd)

        # Partial cleanup
        for fn in dst_sources:
            os.unlink(fn)

    # Import
    __import__(module_name)
    return sys.modules[module_name]

#
# Unittest convenience
#


class F2PyTest(object):
    code = None
    sources = None
    options = []
    skip = []
    only = []
    suffix = '.f'
    module = None
    module_name = None

    def setup(self):
        if sys.platform == 'win32':
            pytest.skip('Fails with MinGW64 Gfortran (Issue #9673)')

        if self.module is not None:
            return

        # Check compiler availability first
        if not has_c_compiler():
            pytest.skip("No C compiler available")

        codes = []
        if self.sources:
            codes.extend(self.sources)
        if self.code is not None:
            codes.append(self.suffix)

        needs_f77 = False
        needs_f90 = False
        for fn in codes:
            if fn.endswith('.f'):
                needs_f77 = True
            elif fn.endswith('.f90'):
                needs_f90 = True
        if needs_f77 and not has_f77_compiler():
            pytest.skip("No Fortran 77 compiler available")
        if needs_f90 and not has_f90_compiler():
            pytest.skip("No Fortran 90 compiler available")

        # Build the module
        if self.code is not None:
            self.module = build_code(self.code, options=self.options,
                                     skip=self.skip, only=self.only,
                                     suffix=self.suffix,
                                     module_name=self.module_name)

        if self.sources is not None:
            self.module = build_module(self.sources, options=self.options,
                                       skip=self.skip, only=self.only,
                                       module_name=self.module_name)
