"""
Copyright 2009 55 Minutes (http://www.55minutes.com)

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import imp, sys, types

__all__ = ('find_or_load_module',)

def _brute_force_find_module(module_name, module_path, module_type):
    for m in [m for n, m in sys.modules.iteritems() if type(m) == types.ModuleType]:
        m_path = []
        try:
            if module_type in (imp.PY_COMPILED, imp.PY_SOURCE):
                m_path = [m.__file__]
            elif module_type==imp.PKG_DIRECTORY:
                m_path = m.__path__
        except AttributeError:
            pass
        for p in m_path:
            if p.startswith(module_path):
                return m
    return None

def _load_module(module_name, fo, fp, desc):
    suffix, mode, mtype = desc
    if module_name in sys.modules and \
       sys.modules[module_name].__file__.startswith(fp):
        module = sys.modules[module_name]
    else:
        module = _brute_force_find_module(module_name, fp, mtype)
    if not module:
        try:
            module = imp.load_module(module_name, fo, fp, desc)
        except:
            raise ImportError
    return module

def _load_package(pkg_name, fp, desc):
    suffix, mode, mtype = desc
    if pkg_name in sys.modules:
        if fp in sys.modules[pkg_name].__path__:
            pkg = sys.modules[pkg_name]
    else:
        pkg = _brute_force_find_module(pkg_name, fp, mtype)
    if not pkg:
        pkg = imp.load_module(pkg_name, None, fp, desc)
    return pkg

def find_or_load_module(module_name, path=None):
    """
    Attempts to lookup ``module_name`` in ``sys.modules``, else uses the
    facilities in the ``imp`` module to load the module.

    If module_name specified is not of type ``imp.PY_SOURCE`` or
    ``imp.PKG_DIRECTORY``, raise ``ImportError`` since we don't know
    what to do with those.
    """
    fo, fp, desc = imp.find_module(module_name.split('.')[-1], path)
    suffix, mode, mtype = desc
    if mtype in (imp.PY_SOURCE, imp.PY_COMPILED):
        module = _load_module(module_name, fo, fp, desc)
    elif mtype==imp.PKG_DIRECTORY:
        module = _load_package(module_name, fp, desc)
    else:
        raise ImportError("Don't know how to handle this module type.")
    return module

