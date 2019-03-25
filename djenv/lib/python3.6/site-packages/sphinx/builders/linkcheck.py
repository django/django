# -*- coding: utf-8 -*-
"""
    sphinx.builders.linkcheck
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    The CheckExternalLinksBuilder class.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import codecs
import re
import socket
import threading
from os import path

from docutils import nodes
from requests.exceptions import HTTPError
from six.moves import queue, html_parser
from six.moves.urllib.parse import unquote

# 2015-06-25 barry@python.org.  This exception was deprecated in Python 3.3 and
# removed in Python 3.5, however for backward compatibility reasons, we're not
# going to just remove it.  If it doesn't exist, define an exception that will
# never be caught but leaves the code in check_anchor() intact.
try:
    from six.moves.html_parser import HTMLParseError  # type: ignore
except ImportError:
    class HTMLParseError(Exception):  # type: ignore
        pass

from sphinx.builders import Builder
from sphinx.locale import __
from sphinx.util import encode_uri, requests, logging
from sphinx.util.console import (  # type: ignore
    purple, red, darkgreen, darkgray, darkred, turquoise
)
from sphinx.util.requests import is_ssl_error

if False:
    # For type annotation
    from typing import Any, Dict, List, Set, Tuple, Union  # NOQA
    from sphinx.application import Sphinx  # NOQA
    from sphinx.util.requests.requests import Response  # NOQA


logger = logging.getLogger(__name__)


class AnchorCheckParser(html_parser.HTMLParser):
    """Specialized HTML parser that looks for a specific anchor."""

    def __init__(self, search_anchor):
        # type: (unicode) -> None
        html_parser.HTMLParser.__init__(self)

        self.search_anchor = search_anchor
        self.found = False

    def handle_starttag(self, tag, attrs):
        # type: (Any, Any) -> None
        for key, value in attrs:
            if key in ('id', 'name') and value == self.search_anchor:
                self.found = True
                break


def check_anchor(response, anchor):
    # type: (Response, unicode) -> bool
    """Reads HTML data from a response object `response` searching for `anchor`.
    Returns True if anchor was found, False otherwise.
    """
    parser = AnchorCheckParser(anchor)
    try:
        # Read file in chunks. If we find a matching anchor, we break
        # the loop early in hopes not to have to download the whole thing.
        for chunk in response.iter_content(chunk_size=4096, decode_unicode=True):
            parser.feed(chunk)
            if parser.found:
                break
        parser.close()
    except HTMLParseError:
        # HTMLParser is usually pretty good with sloppy HTML, but it tends to
        # choke on EOF. But we're done then anyway.
        pass
    return parser.found


class CheckExternalLinksBuilder(Builder):
    """
    Checks for broken external links.
    """
    name = 'linkcheck'
    epilog = __('Look for any errors in the above output or in '
                '%(outdir)s/output.txt')

    def init(self):
        # type: () -> None
        self.to_ignore = [re.compile(x) for x in self.app.config.linkcheck_ignore]
        self.anchors_ignore = [re.compile(x)
                               for x in self.app.config.linkcheck_anchors_ignore]
        self.good = set()       # type: Set[unicode]
        self.broken = {}        # type: Dict[unicode, unicode]
        self.redirected = {}    # type: Dict[unicode, Tuple[unicode, int]]
        # set a timeout for non-responding servers
        socket.setdefaulttimeout(5.0)
        # create output file
        open(path.join(self.outdir, 'output.txt'), 'w').close()

        # create queues and worker threads
        self.wqueue = queue.Queue()  # type: queue.Queue
        self.rqueue = queue.Queue()  # type: queue.Queue
        self.workers = []  # type: List[threading.Thread]
        for i in range(self.app.config.linkcheck_workers):
            thread = threading.Thread(target=self.check_thread)
            thread.setDaemon(True)
            thread.start()
            self.workers.append(thread)

    def check_thread(self):
        # type: () -> None
        kwargs = {
            'allow_redirects': True,
            'headers': {
                'Accept': 'text/html,application/xhtml+xml;q=0.9,*/*;q=0.8'
            },
        }
        if self.app.config.linkcheck_timeout:
            kwargs['timeout'] = self.app.config.linkcheck_timeout

        def check_uri():
            # type: () -> Tuple[unicode, unicode, int]
            # split off anchor
            if '#' in uri:
                req_url, anchor = uri.split('#', 1)
                for rex in self.anchors_ignore:
                    if rex.match(anchor):
                        anchor = None
                        break
            else:
                req_url = uri
                anchor = None

            # handle non-ASCII URIs
            try:
                req_url.encode('ascii')
            except UnicodeError:
                req_url = encode_uri(req_url)

            try:
                if anchor and self.app.config.linkcheck_anchors:
                    # Read the whole document and see if #anchor exists
                    response = requests.get(req_url, stream=True, config=self.app.config,
                                            **kwargs)
                    found = check_anchor(response, unquote(anchor))

                    if not found:
                        raise Exception(__("Anchor '%s' not found") % anchor)
                else:
                    try:
                        # try a HEAD request first, which should be easier on
                        # the server and the network
                        response = requests.head(req_url, config=self.app.config, **kwargs)
                        response.raise_for_status()
                    except HTTPError:
                        # retry with GET request if that fails, some servers
                        # don't like HEAD requests.
                        response = requests.get(req_url, stream=True, config=self.app.config,
                                                **kwargs)
                        response.raise_for_status()
            except HTTPError as err:
                if err.response.status_code == 401:
                    # We'll take "Unauthorized" as working.
                    return 'working', ' - unauthorized', 0
                else:
                    return 'broken', str(err), 0
            except Exception as err:
                if is_ssl_error(err):
                    return 'ignored', str(err), 0
                else:
                    return 'broken', str(err), 0
            if response.url.rstrip('/') == req_url.rstrip('/'):
                return 'working', '', 0
            else:
                new_url = response.url
                if anchor:
                    new_url += '#' + anchor
                # history contains any redirects, get last
                if response.history:
                    code = response.history[-1].status_code
                    return 'redirected', new_url, code
                else:
                    return 'redirected', new_url, 0

        def check():
            # type: () -> Tuple[unicode, unicode, int]
            # check for various conditions without bothering the network
            if len(uri) == 0 or uri.startswith(('#', 'mailto:', 'ftp:')):
                return 'unchecked', '', 0
            elif not uri.startswith(('http:', 'https:')):
                return 'local', '', 0
            elif uri in self.good:
                return 'working', 'old', 0
            elif uri in self.broken:
                return 'broken', self.broken[uri], 0
            elif uri in self.redirected:
                return 'redirected', self.redirected[uri][0], self.redirected[uri][1]
            for rex in self.to_ignore:
                if rex.match(uri):
                    return 'ignored', '', 0

            # need to actually check the URI
            for _ in range(self.app.config.linkcheck_retries):
                status, info, code = check_uri()
                if status != "broken":
                    break

            if status == "working":
                self.good.add(uri)
            elif status == "broken":
                self.broken[uri] = info
            elif status == "redirected":
                self.redirected[uri] = (info, code)

            return (status, info, code)

        while True:
            uri, docname, lineno = self.wqueue.get()
            if uri is None:
                break
            status, info, code = check()
            self.rqueue.put((uri, docname, lineno, status, info, code))

    def process_result(self, result):
        # type: (Tuple[unicode, unicode, int, unicode, unicode, int]) -> None
        uri, docname, lineno, status, info, code = result
        if status == 'unchecked':
            return
        if status == 'working' and info == 'old':
            return
        if lineno:
            logger.info('(line %4d) ', lineno, nonl=1)
        if status == 'ignored':
            if info:
                logger.info(darkgray('-ignored- ') + uri + ': ' + info)
            else:
                logger.info(darkgray('-ignored- ') + uri)
        elif status == 'local':
            logger.info(darkgray('-local-   ') + uri)
            self.write_entry('local', docname, lineno, uri)
        elif status == 'working':
            logger.info(darkgreen('ok        ') + uri + info)
        elif status == 'broken':
            self.write_entry('broken', docname, lineno, uri + ': ' + info)
            if self.app.quiet or self.app.warningiserror:
                logger.warning(__('broken link: %s (%s)'), uri, info,
                               location=(self.env.doc2path(docname), lineno))
            else:
                logger.info(red('broken    ') + uri + red(' - ' + info))
        elif status == 'redirected':
            text, color = {
                301: ('permanently', darkred),
                302: ('with Found', purple),
                303: ('with See Other', purple),
                307: ('temporarily', turquoise),
                0:   ('with unknown code', purple),
            }[code]
            self.write_entry('redirected ' + text, docname, lineno,
                             uri + ' to ' + info)
            logger.info(color('redirect  ') + uri + color(' - ' + text + ' to ' + info))

    def get_target_uri(self, docname, typ=None):
        # type: (unicode, unicode) -> unicode
        return ''

    def get_outdated_docs(self):
        # type: () -> Set[unicode]
        return self.env.found_docs

    def prepare_writing(self, docnames):
        # type: (nodes.Node) -> None
        return

    def write_doc(self, docname, doctree):
        # type: (unicode, nodes.Node) -> None
        logger.info('')
        n = 0
        for node in doctree.traverse(nodes.reference):
            if 'refuri' not in node:
                continue
            uri = node['refuri']
            lineno = None
            while lineno is None:
                node = node.parent
                if node is None:
                    break
                lineno = node.line
            self.wqueue.put((uri, docname, lineno), False)
            n += 1
        done = 0
        while done < n:
            self.process_result(self.rqueue.get())
            done += 1

        if self.broken:
            self.app.statuscode = 1

    def write_entry(self, what, docname, line, uri):
        # type: (unicode, unicode, int, unicode) -> None
        with codecs.open(path.join(self.outdir, 'output.txt'), 'a', 'utf-8') as output:  # type: ignore  # NOQA
            output.write("%s:%s: [%s] %s\n" % (self.env.doc2path(docname, None),
                                               line, what, uri))

    def finish(self):
        # type: () -> None
        for worker in self.workers:
            self.wqueue.put((None, None, None), False)


def setup(app):
    # type: (Sphinx) -> Dict[unicode, Any]
    app.add_builder(CheckExternalLinksBuilder)

    app.add_config_value('linkcheck_ignore', [], None)
    app.add_config_value('linkcheck_retries', 1, None)
    app.add_config_value('linkcheck_timeout', None, None, [int])
    app.add_config_value('linkcheck_workers', 5, None)
    app.add_config_value('linkcheck_anchors', True, None)
    # Anchors starting with ! are ignored since they are
    # commonly used for dynamic pages
    app.add_config_value('linkcheck_anchors_ignore', ["^!"], None)

    return {
        'version': 'builtin',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
