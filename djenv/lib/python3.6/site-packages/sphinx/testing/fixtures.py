# -*- coding: utf-8 -*-
"""
    sphinx.testing.fixtures
    ~~~~~~~~~~~~~~~~~~~~~~~

    Sphinx test fixtures for pytest

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""
from __future__ import print_function

import os
import subprocess
import sys
from collections import namedtuple
from tempfile import gettempdir

import pytest
from six import StringIO, string_types

from . import util

if False:
    # For type annotation
    from typing import Any, Dict, Union  # NOQA


@pytest.fixture(scope='session')
def rootdir():
    # type: () -> None
    return None


@pytest.fixture
def app_params(request, test_params, shared_result, sphinx_test_tempdir, rootdir):
    # type: (Any, Any, Any, Any, Any) -> None
    """
    parameters that is specified by 'pytest.mark.sphinx' for
    sphinx.application.Sphinx initialization
    """

    # ##### process pytest.mark.sphinx

    if hasattr(request.node, 'iter_markers'):  # pytest-3.6.0 or newer
        markers = request.node.iter_markers("sphinx")
    else:
        markers = request.node.get_marker("sphinx")
    pargs = {}
    kwargs = {}  # type: Dict[str, str]

    if markers is not None:
        # to avoid stacking positional args
        for info in reversed(list(markers)):
            for i, a in enumerate(info.args):
                pargs[i] = a
            kwargs.update(info.kwargs)

    args = [pargs[i] for i in sorted(pargs.keys())]

    # ##### process pytest.mark.test_params

    if test_params['shared_result']:
        if 'srcdir' in kwargs:
            raise pytest.Exception('You can not spcify shared_result and '
                                   'srcdir in same time.')
        kwargs['srcdir'] = test_params['shared_result']
        restore = shared_result.restore(test_params['shared_result'])
        kwargs.update(restore)

    # ##### prepare Application params

    testroot = kwargs.pop('testroot', 'root')
    kwargs['srcdir'] = srcdir = sphinx_test_tempdir / kwargs.get('srcdir', testroot)

    # special support for sphinx/tests
    if rootdir and not srcdir.exists():
        testroot_path = rootdir / ('test-' + testroot)
        testroot_path.copytree(srcdir)

    return namedtuple('app_params', 'args,kwargs')(args, kwargs)  # type: ignore


@pytest.fixture
def test_params(request):
    """
    test parameters that is specified by 'pytest.mark.test_params'

    :param Union[str] shared_result:
       If the value is provided, app._status and app._warning objects will be
       shared in the parametrized test functions and/or test functions that
       have same 'shared_result' value.
       **NOTE**: You can not specify shared_result and srcdir in same time.
    """
    if hasattr(request.node, 'get_closest_marker'):  # pytest-3.6.0 or newer
        env = request.node.get_closest_marker('test_params')
    else:
        env = request.node.get_marker('test_params')
    kwargs = env.kwargs if env else {}
    result = {
        'shared_result': None,
    }
    result.update(kwargs)

    if (result['shared_result'] and
            not isinstance(result['shared_result'], string_types)):
        raise pytest.Exception('You can only provide a string type of value '
                               'for "shared_result" ')
    return result


@pytest.fixture(scope='function')
def app(test_params, app_params, make_app, shared_result):
    """
    provides sphinx.application.Sphinx object
    """
    args, kwargs = app_params
    app_ = make_app(*args, **kwargs)
    yield app_

    print('# testroot:', kwargs.get('testroot', 'root'))
    print('# builder:', app_.builder.name)
    print('# srcdir:', app_.srcdir)
    print('# outdir:', app_.outdir)
    print('# status:', '\n' + app_._status.getvalue())
    print('# warning:', '\n' + app_._warning.getvalue())

    if test_params['shared_result']:
        shared_result.store(test_params['shared_result'], app_)


@pytest.fixture(scope='function')
def status(app):
    """
    compat for testing with previous @with_app decorator
    """
    return app._status


@pytest.fixture(scope='function')
def warning(app):
    """
    compat for testing with previous @with_app decorator
    """
    return app._warning


@pytest.fixture()
def make_app(test_params, monkeypatch):
    """
    provides make_app function to initialize SphinxTestApp instance.
    if you want to initialize 'app' in your test function. please use this
    instead of using SphinxTestApp class directory.
    """
    monkeypatch.setattr('sphinx.application.abspath', lambda x: x)

    apps = []
    syspath = sys.path[:]

    def make(*args, **kwargs):
        status, warning = StringIO(), StringIO()
        kwargs.setdefault('status', status)
        kwargs.setdefault('warning', warning)
        app_ = util.SphinxTestApp(*args, **kwargs)  # type: Union[util.SphinxTestApp, util.SphinxTestAppWrapperForSkipBuilding]  # NOQA
        apps.append(app_)
        if test_params['shared_result']:
            app_ = util.SphinxTestAppWrapperForSkipBuilding(app_)  # type: ignore
        return app_
    yield make

    sys.path[:] = syspath
    for app_ in reversed(apps):  # clean up applications from the new ones
        app_.cleanup()


class SharedResult(object):
    cache = {}  # type: Dict[str, Dict[str, str]]

    def store(self, key, app_):
        if key in self.cache:
            return
        data = {
            'status': app_._status.getvalue(),
            'warning': app_._warning.getvalue(),
        }
        self.cache[key] = data

    def restore(self, key):
        if key not in self.cache:
            return {}
        data = self.cache[key]
        return {
            'status': StringIO(data['status']),
            'warning': StringIO(data['warning']),
        }


@pytest.fixture
def shared_result():
    return SharedResult()


@pytest.fixture(scope='module', autouse=True)
def _shared_result_cache():
    SharedResult.cache.clear()


@pytest.fixture
def if_graphviz_found(app):
    """
    The test will be skipped when using 'if_graphviz_found' fixture and graphviz
    dot command is not found.
    """
    graphviz_dot = getattr(app.config, 'graphviz_dot', '')
    try:
        if graphviz_dot:
            dot = subprocess.Popen([graphviz_dot, '-V'],
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)  # show version
            dot.communicate()
            return
    except OSError:  # No such file or directory
        pass

    pytest.skip('graphviz "dot" is not available')


@pytest.fixture(scope='session')
def sphinx_test_tempdir():
    """
    temporary directory that wrapped with `path` class.
    """
    return util.path(os.environ.get('SPHINX_TEST_TEMPDIR', gettempdir())).abspath()


@pytest.fixture
def tempdir(tmpdir):
    """
    temporary directory that wrapped with `path` class.
    this fixture is for compat with old test implementation.
    """
    return util.path(tmpdir)
