from __future__ import division, absolute_import, print_function

import pytest

from numpy.testing import assert_, suppress_warnings
import numpy.distutils.fcompiler

customizable_flags = [
    ('f77', 'F77FLAGS'),
    ('f90', 'F90FLAGS'),
    ('free', 'FREEFLAGS'),
    ('arch', 'FARCH'),
    ('debug', 'FDEBUG'),
    ('flags', 'FFLAGS'),
    ('linker_so', 'LDFLAGS'),
]


def test_fcompiler_flags(monkeypatch):
    monkeypatch.setenv('NPY_DISTUTILS_APPEND_FLAGS', '0')
    fc = numpy.distutils.fcompiler.new_fcompiler(compiler='none')
    flag_vars = fc.flag_vars.clone(lambda *args, **kwargs: None)

    for opt, envvar in customizable_flags:
        new_flag = '-dummy-{}-flag'.format(opt)
        prev_flags = getattr(flag_vars, opt)

        monkeypatch.setenv(envvar, new_flag)
        new_flags = getattr(flag_vars, opt)

        monkeypatch.delenv(envvar)
        assert_(new_flags == [new_flag])

    monkeypatch.setenv('NPY_DISTUTILS_APPEND_FLAGS', '1')

    for opt, envvar in customizable_flags:
        new_flag = '-dummy-{}-flag'.format(opt)
        prev_flags = getattr(flag_vars, opt)
        monkeypatch.setenv(envvar, new_flag)
        new_flags = getattr(flag_vars, opt)

        monkeypatch.delenv(envvar)
        if prev_flags is None:
            assert_(new_flags == [new_flag])
        else:
            assert_(new_flags == prev_flags + [new_flag])


def test_fcompiler_flags_append_warning(monkeypatch):
    # Test to check that the warning for append behavior changing in future
    # is triggered.  Need to use a real compiler instance so that we have
    # non-empty flags to start with (otherwise the "if var and append" check
    # will always be false).
    try:
        with suppress_warnings() as sup:
            sup.record()
            fc = numpy.distutils.fcompiler.new_fcompiler(compiler='gnu95')
            fc.customize()
    except numpy.distutils.fcompiler.CompilerNotFound:
        pytest.skip("gfortran not found, so can't execute this test")

    # Ensure NPY_DISTUTILS_APPEND_FLAGS not defined
    monkeypatch.delenv('NPY_DISTUTILS_APPEND_FLAGS', raising=False)

    for opt, envvar in customizable_flags:
        new_flag = '-dummy-{}-flag'.format(opt)
        with suppress_warnings() as sup:
            sup.record()
            prev_flags = getattr(fc.flag_vars, opt)

        monkeypatch.setenv(envvar, new_flag)
        with suppress_warnings() as sup:
            sup.record()
            new_flags = getattr(fc.flag_vars, opt)
            if prev_flags:
                # Check that warning was issued
                assert len(sup.log) == 1

        monkeypatch.delenv(envvar)
        assert_(new_flags == [new_flag])

