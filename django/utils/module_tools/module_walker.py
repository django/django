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

import os, re, sys
from glob import glob

from data_storage import *
from module_loader import find_or_load_module

try:
    set
except:
    from sets import Set as set

__all__ = ('get_all_modules',)

def _build_pkg_path(pkg_name, pkg, path):
    for rp in [x for x in pkg.__path__ if path.startswith(x)]:
        p = path.replace(rp, '').replace(os.path.sep, '.')
        return pkg_name + p

def _build_module_path(pkg_name, pkg, path):
    return _build_pkg_path(pkg_name, pkg, os.path.splitext(path)[0])

def _prune_whitelist(whitelist, blacklist):
    excluded = Excluded().excluded

    for wp in whitelist[:]:
        for bp in blacklist:
            if re.search(bp, wp):
                whitelist.remove(wp)
                excluded.append(wp)
                break
    return whitelist

def _parse_module_list(m_list):
    packages = Packages().packages
    modules = Modules().modules
    excluded = Excluded().excluded
    errors = Errors().errors

    for m in m_list:
        components = m.split('.')
        m_name = ''
        search_path = []
        processed=False
        for i, c in enumerate(components):
            m_name = '.'.join([x for x in m_name.split('.') if x] + [c])
            try:
                module = find_or_load_module(m_name, search_path or None)
            except ImportError:
                processed=True
                errors.append(m)
                break
            try:
                search_path.extend(module.__path__)
            except AttributeError:
                processed = True
                if i+1==len(components):
                    modules[m_name] = module
                else:
                    errors.append(m)
                    break
        if not processed:
            packages[m_name] = module

def prune_dirs(root, dirs, exclude_dirs):
    _dirs = [os.path.join(root, d) for d in dirs]
    for i, p in enumerate(_dirs):
        for e in exclude_dirs:
            if re.search(e, p):
                del dirs[i]
                break

def _get_all_packages(pkg_name, pkg, blacklist, exclude_dirs):
    packages = Packages().packages
    errors = Errors().errors

    for path in pkg.__path__:
        for root, dirs, files in os.walk(path):
            prune_dirs(root, dirs, exclude_dirs or [])
            m_name = _build_pkg_path(pkg_name, pkg, root)
            try:
                if _prune_whitelist([m_name], blacklist):
                    m = find_or_load_module(m_name, [os.path.split(root)[0]])
                    packages[m_name] = m
                else:
                    for d in dirs[:]:
                        dirs.remove(d)
            except ImportError:
                errors.append(m_name)
                for d in dirs[:]:
                    dirs.remove(d)

def _get_all_modules(pkg_name, pkg, blacklist):
    modules = Modules().modules
    errors = Errors().errors

    for p in pkg.__path__:
        for f in glob('%s/*.py' %p):
            m_name = _build_module_path(pkg_name, pkg, f)
            try:
                if _prune_whitelist([m_name], blacklist):
                    m = find_or_load_module(m_name, [p])
                    modules[m_name] = m
            except ImportError:
               errors.append(m_name)

def get_all_modules(whitelist, blacklist=None, exclude_dirs=None):
    packages = Packages().packages
    modules = Modules().modules
    excluded = Excluded().excluded
    errors = Errors().errors

    whitelist = _prune_whitelist(whitelist, blacklist or [])
    _parse_module_list(whitelist)
    for pkg_name, pkg in packages.copy().iteritems():
        _get_all_packages(pkg_name, pkg, blacklist, exclude_dirs)
    for pkg_name, pkg in packages.copy().iteritems():
        _get_all_modules(pkg_name, pkg, blacklist)
    return packages, modules, list(set(excluded)), list(set(errors))

