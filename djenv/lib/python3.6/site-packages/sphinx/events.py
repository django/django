# -*- coding: utf-8 -*-
"""
    sphinx.events
    ~~~~~~~~~~~~~

    Sphinx core events.

    Gracefully adapted from the TextPress system by Armin.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""
from __future__ import print_function

from collections import OrderedDict, defaultdict

from six import itervalues

from sphinx.errors import ExtensionError
from sphinx.locale import __

if False:
    # For type annotation
    from typing import Any, Callable, Dict, List  # NOQA


# List of all known core events. Maps name to arguments description.
core_events = {
    'builder-inited': '',
    'config-inited': 'config',
    'env-get-outdated': 'env, added, changed, removed',
    'env-get-updated': 'env',
    'env-purge-doc': 'env, docname',
    'env-before-read-docs': 'env, docnames',
    'env-check-consistency': 'env',
    'source-read': 'docname, source text',
    'doctree-read': 'the doctree before being pickled',
    'env-merge-info': 'env, read docnames, other env instance',
    'missing-reference': 'env, node, contnode',
    'doctree-resolved': 'doctree, docname',
    'env-updated': 'env',
    'html-collect-pages': 'builder',
    'html-page-context': 'pagename, context, doctree or None',
    'build-finished': 'exception',
}  # type: Dict[unicode, unicode]


class EventManager(object):
    def __init__(self):
        # type: () -> None
        self.events = core_events.copy()
        self.listeners = defaultdict(OrderedDict)  # type: Dict[unicode, Dict[int, Callable]]
        self.next_listener_id = 0

    def add(self, name):
        # type: (unicode) -> None
        if name in self.events:
            raise ExtensionError(__('Event %r already present') % name)
        self.events[name] = ''

    def connect(self, name, callback):
        # type: (unicode, Callable) -> int
        if name not in self.events:
            raise ExtensionError(__('Unknown event name: %s') % name)

        listener_id = self.next_listener_id
        self.next_listener_id += 1
        self.listeners[name][listener_id] = callback
        return listener_id

    def disconnect(self, listener_id):
        # type: (int) -> None
        for event in itervalues(self.listeners):
            event.pop(listener_id, None)

    def emit(self, name, *args):
        # type: (unicode, Any) -> List
        results = []
        for callback in itervalues(self.listeners[name]):
            results.append(callback(*args))
        return results

    def emit_firstresult(self, name, *args):
        # type: (unicode, Any) -> Any
        for result in self.emit(name, *args):
            if result is not None:
                return result
        return None
