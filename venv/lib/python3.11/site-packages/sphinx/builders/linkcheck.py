"""The CheckExternalLinksBuilder class."""

from __future__ import annotations

import contextlib
import json
import re
import socket
import time
from html.parser import HTMLParser
from os import path
from queue import PriorityQueue, Queue
from threading import Thread
from typing import TYPE_CHECKING, NamedTuple, cast
from urllib.parse import unquote, urlparse, urlsplit, urlunparse

from docutils import nodes
from requests.exceptions import ConnectionError, HTTPError, SSLError, TooManyRedirects

from sphinx.builders.dummy import DummyBuilder
from sphinx.locale import __
from sphinx.transforms.post_transforms import SphinxPostTransform
from sphinx.util import encode_uri, logging, requests
from sphinx.util.console import (  # type: ignore[attr-defined]
    darkgray,
    darkgreen,
    purple,
    red,
    turquoise,
)
from sphinx.util.http_date import rfc1123_to_epoch
from sphinx.util.nodes import get_node_line

if TYPE_CHECKING:
    from collections.abc import Generator, Iterator
    from typing import Any, Callable

    from requests import Response

    from sphinx.application import Sphinx
    from sphinx.config import Config

logger = logging.getLogger(__name__)

uri_re = re.compile('([a-z]+:)?//')  # matches to foo:// and // (a protocol relative URL)

DEFAULT_REQUEST_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml;q=0.9,*/*;q=0.8',
}
CHECK_IMMEDIATELY = 0
QUEUE_POLL_SECS = 1
DEFAULT_DELAY = 60.0


class CheckExternalLinksBuilder(DummyBuilder):
    """
    Checks for broken external links.
    """
    name = 'linkcheck'
    epilog = __('Look for any errors in the above output or in '
                '%(outdir)s/output.txt')

    def init(self) -> None:
        self.broken_hyperlinks = 0
        self.hyperlinks: dict[str, Hyperlink] = {}
        # set a timeout for non-responding servers
        socket.setdefaulttimeout(5.0)

    def finish(self) -> None:
        checker = HyperlinkAvailabilityChecker(self.config)
        logger.info('')

        output_text = path.join(self.outdir, 'output.txt')
        output_json = path.join(self.outdir, 'output.json')
        with open(output_text, 'w', encoding='utf-8') as self.txt_outfile, \
             open(output_json, 'w', encoding='utf-8') as self.json_outfile:
            for result in checker.check(self.hyperlinks):
                self.process_result(result)

        if self.broken_hyperlinks:
            self.app.statuscode = 1

    def process_result(self, result: CheckResult) -> None:
        filename = self.env.doc2path(result.docname, False)

        linkstat = {'filename': filename, 'lineno': result.lineno,
                    'status': result.status, 'code': result.code, 'uri': result.uri,
                    'info': result.message}
        self.write_linkstat(linkstat)

        if result.status == 'unchecked':
            return
        if result.status == 'working' and result.message == 'old':
            return
        if result.lineno:
            logger.info('(%16s: line %4d) ', result.docname, result.lineno, nonl=True)
        if result.status == 'ignored':
            if result.message:
                logger.info(darkgray('-ignored- ') + result.uri + ': ' + result.message)
            else:
                logger.info(darkgray('-ignored- ') + result.uri)
        elif result.status == 'local':
            logger.info(darkgray('-local-   ') + result.uri)
            self.write_entry('local', result.docname, filename, result.lineno, result.uri)
        elif result.status == 'working':
            logger.info(darkgreen('ok        ') + result.uri + result.message)
        elif result.status == 'broken':
            if self.app.quiet or self.app.warningiserror:
                logger.warning(__('broken link: %s (%s)'), result.uri, result.message,
                               location=(result.docname, result.lineno))
            else:
                logger.info(red('broken    ') + result.uri + red(' - ' + result.message))
            self.write_entry('broken', result.docname, filename, result.lineno,
                             result.uri + ': ' + result.message)
            self.broken_hyperlinks += 1
        elif result.status == 'redirected':
            try:
                text, color = {
                    301: ('permanently', purple),
                    302: ('with Found', purple),
                    303: ('with See Other', purple),
                    307: ('temporarily', turquoise),
                    308: ('permanently', purple),
                }[result.code]
            except KeyError:
                text, color = ('with unknown code', purple)
            linkstat['text'] = text
            if self.config.linkcheck_allowed_redirects:
                logger.warning('redirect  ' + result.uri + ' - ' + text + ' to ' +
                               result.message, location=(result.docname, result.lineno))
            else:
                logger.info(color('redirect  ') + result.uri +
                            color(' - ' + text + ' to ' + result.message))
            self.write_entry('redirected ' + text, result.docname, filename,
                             result.lineno, result.uri + ' to ' + result.message)
        else:
            raise ValueError('Unknown status %s.' % result.status)

    def write_linkstat(self, data: dict) -> None:
        self.json_outfile.write(json.dumps(data))
        self.json_outfile.write('\n')

    def write_entry(self, what: str, docname: str, filename: str, line: int,
                    uri: str) -> None:
        self.txt_outfile.write(f'{filename}:{line}: [{what}] {uri}\n')


class HyperlinkCollector(SphinxPostTransform):
    builders = ('linkcheck',)
    default_priority = 800

    def run(self, **kwargs: Any) -> None:
        builder = cast(CheckExternalLinksBuilder, self.app.builder)
        hyperlinks = builder.hyperlinks
        docname = self.env.docname

        # reference nodes
        for refnode in self.document.findall(nodes.reference):
            if 'refuri' in refnode:
                uri = refnode['refuri']
                _add_uri(self.app, uri, refnode, hyperlinks, docname)

        # image nodes
        for imgnode in self.document.findall(nodes.image):
            uri = imgnode['candidates'].get('?')
            if uri and '://' in uri:
                _add_uri(self.app, uri, imgnode, hyperlinks, docname)

        # raw nodes
        for rawnode in self.document.findall(nodes.raw):
            uri = rawnode.get('source')
            if uri and '://' in uri:
                _add_uri(self.app, uri, rawnode, hyperlinks, docname)


def _add_uri(app: Sphinx, uri: str, node: nodes.Element,
             hyperlinks: dict[str, Hyperlink], docname: str) -> None:
    if newuri := app.emit_firstresult('linkcheck-process-uri', uri):
        uri = newuri

    try:
        lineno = get_node_line(node)
    except ValueError:
        lineno = -1

    if uri not in hyperlinks:
        hyperlinks[uri] = Hyperlink(uri, docname, app.env.doc2path(docname), lineno)


class Hyperlink(NamedTuple):
    uri: str
    docname: str
    docpath: str
    lineno: int


class HyperlinkAvailabilityChecker:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.rate_limits: dict[str, RateLimit] = {}
        self.rqueue: Queue[CheckResult] = Queue()
        self.workers: list[Thread] = []
        self.wqueue: PriorityQueue[CheckRequest] = PriorityQueue()
        self.num_workers: int = config.linkcheck_workers

        self.to_ignore: list[re.Pattern[str]] = list(map(re.compile,
                                                         self.config.linkcheck_ignore))

    def check(self, hyperlinks: dict[str, Hyperlink]) -> Generator[CheckResult, None, None]:
        self.invoke_threads()

        total_links = 0
        for hyperlink in hyperlinks.values():
            if self.is_ignored_uri(hyperlink.uri):
                yield CheckResult(hyperlink.uri, hyperlink.docname, hyperlink.lineno,
                                  'ignored', '', 0)
            else:
                self.wqueue.put(CheckRequest(CHECK_IMMEDIATELY, hyperlink), False)
                total_links += 1

        done = 0
        while done < total_links:
            yield self.rqueue.get()
            done += 1

        self.shutdown_threads()

    def invoke_threads(self) -> None:
        for _i in range(self.num_workers):
            thread = HyperlinkAvailabilityCheckWorker(self.config,
                                                      self.rqueue, self.wqueue,
                                                      self.rate_limits)
            thread.start()
            self.workers.append(thread)

    def shutdown_threads(self) -> None:
        self.wqueue.join()
        for _worker in self.workers:
            self.wqueue.put(CheckRequest(CHECK_IMMEDIATELY, None), False)

    def is_ignored_uri(self, uri: str) -> bool:
        return any(pat.match(uri) for pat in self.to_ignore)


class CheckRequest(NamedTuple):
    next_check: float
    hyperlink: Hyperlink | None


class CheckResult(NamedTuple):
    uri: str
    docname: str
    lineno: int
    status: str
    message: str
    code: int


class HyperlinkAvailabilityCheckWorker(Thread):
    """A worker class for checking the availability of hyperlinks."""

    def __init__(self, config: Config,
                 rqueue: Queue[CheckResult],
                 wqueue: Queue[CheckRequest],
                 rate_limits: dict[str, RateLimit]) -> None:
        self.rate_limits = rate_limits
        self.rqueue = rqueue
        self.wqueue = wqueue

        self.anchors_ignore: list[re.Pattern[str]] = list(
            map(re.compile, config.linkcheck_anchors_ignore))
        self.anchors_ignore_for_url: list[re.Pattern[str]] = list(
            map(re.compile, config.linkcheck_anchors_ignore_for_url))
        self.documents_exclude: list[re.Pattern[str]] = list(
            map(re.compile, config.linkcheck_exclude_documents))
        self.auth = [(re.compile(pattern), auth_info) for pattern, auth_info
                     in config.linkcheck_auth]

        self.timeout: int | float | None = config.linkcheck_timeout
        self.request_headers: dict[str, dict[str, str]] = config.linkcheck_request_headers
        self.check_anchors: bool = config.linkcheck_anchors
        self.allowed_redirects: dict[re.Pattern[str], re.Pattern[str]]
        self.allowed_redirects = config.linkcheck_allowed_redirects
        self.retries: int = config.linkcheck_retries
        self.rate_limit_timeout = config.linkcheck_rate_limit_timeout

        self.user_agent = config.user_agent
        self.tls_verify = config.tls_verify
        self.tls_cacerts = config.tls_cacerts

        self._session = requests._Session()

        super().__init__(daemon=True)

    def run(self) -> None:
        while True:
            next_check, hyperlink = self.wqueue.get()
            if hyperlink is None:
                # An empty hyperlink is a signal to shutdown the worker; cleanup resources here
                self._session.close()
                break

            uri, docname, _docpath, lineno = hyperlink
            if uri is None:
                break

            netloc = urlsplit(uri).netloc
            with contextlib.suppress(KeyError):
                # Refresh rate limit.
                # When there are many links in the queue, workers are all stuck waiting
                # for responses, but the builder keeps queuing. Links in the queue may
                # have been queued before rate limits were discovered.
                next_check = self.rate_limits[netloc].next_check
            if next_check > time.time():
                # Sleep before putting message back in the queue to avoid
                # waking up other threads.
                time.sleep(QUEUE_POLL_SECS)
                self.wqueue.put(CheckRequest(next_check, hyperlink), False)
                self.wqueue.task_done()
                continue
            status, info, code = self._check(docname, uri, hyperlink)
            if status == 'rate-limited':
                logger.info(darkgray('-rate limited-   ') + uri + darkgray(' | sleeping...'))
            else:
                self.rqueue.put(CheckResult(uri, docname, lineno, status, info, code))
            self.wqueue.task_done()

    def _check(self, docname: str, uri: str, hyperlink: Hyperlink) -> tuple[str, str, int]:
        # check for various conditions without bothering the network

        for doc_matcher in self.documents_exclude:
            if doc_matcher.match(docname):
                info = (
                    f'{docname} matched {doc_matcher.pattern} from '
                    'linkcheck_exclude_documents'
                )
                return 'ignored', info, 0

        if len(uri) == 0 or uri.startswith(('#', 'mailto:', 'tel:')):
            return 'unchecked', '', 0
        if not uri.startswith(('http:', 'https:')):
            if uri_re.match(uri):
                # Non-supported URI schemes (ex. ftp)
                return 'unchecked', '', 0

            src_dir = path.dirname(hyperlink.docpath)
            if path.exists(path.join(src_dir, uri)):
                return 'working', '', 0
            return 'broken', '', 0

        # need to actually check the URI
        status, info, code = '', '', 0
        for _ in range(self.retries):
            status, info, code = self._check_uri(uri, hyperlink)
            if status != 'broken':
                break

        return status, info, code

    def _retrieval_methods(self,
                           check_anchors: bool,
                           anchor: str) -> Iterator[tuple[Callable, dict]]:
        if not check_anchors or not anchor:
            yield self._session.head, {'allow_redirects': True}
        yield self._session.get, {'stream': True}

    def _check_uri(self, uri: str, hyperlink: Hyperlink) -> tuple[str, str, int]:
        req_url, delimiter, anchor = uri.partition('#')
        if delimiter and anchor:
            for rex in self.anchors_ignore:
                if rex.match(anchor):
                    anchor = ''
                    break
            else:
                for rex in self.anchors_ignore_for_url:
                    if rex.match(req_url):
                        anchor = ''
                        break

        # handle non-ASCII URIs
        try:
            req_url.encode('ascii')
        except UnicodeError:
            req_url = encode_uri(req_url)

        # Get auth info, if any
        for pattern, auth_info in self.auth:  # noqa: B007 (false positive)
            if pattern.match(uri):
                break
        else:
            auth_info = None

        # update request headers for the URL
        headers = _get_request_headers(uri, self.request_headers)

        # Linkcheck HTTP request logic:
        #
        # - Attempt HTTP HEAD before HTTP GET unless page content is required.
        # - Follow server-issued HTTP redirects.
        # - Respect server-issued HTTP 429 back-offs.
        error_message = ''
        status_code = -1
        response_url = retry_after = ''
        for retrieval_method, kwargs in self._retrieval_methods(self.check_anchors, anchor):
            try:
                with retrieval_method(
                    url=req_url, auth=auth_info,
                    headers=headers,
                    timeout=self.timeout,
                    **kwargs,
                    _user_agent=self.user_agent,
                    _tls_info=(self.tls_verify, self.tls_cacerts),
                ) as response:
                    if (self.check_anchors and response.ok and anchor
                            and not contains_anchor(response, anchor)):
                        raise Exception(__(f'Anchor {anchor!r} not found'))

                # Copy data we need from the (closed) response
                status_code = response.status_code
                redirect_status_code = response.history[-1].status_code if response.history else None  # NoQA: E501
                retry_after = response.headers.get('Retry-After')
                response_url = f'{response.url}'
                response.raise_for_status()
                del response
                break

            except SSLError as err:
                # SSL failure; report that the link is broken.
                return 'broken', str(err), 0

            except (ConnectionError, TooManyRedirects) as err:
                # Servers drop the connection on HEAD requests, causing
                # ConnectionError.
                error_message = str(err)
                continue

            except HTTPError as err:
                error_message = str(err)

                # Unauthorised: the reference probably exists
                if status_code == 401:
                    return 'working', 'unauthorized', 0

                # Rate limiting; back-off if allowed, or report failure otherwise
                if status_code == 429:
                    if next_check := self.limit_rate(response_url, retry_after):
                        self.wqueue.put(CheckRequest(next_check, hyperlink), False)
                        return 'rate-limited', '', 0
                    return 'broken', error_message, 0

                # Don't claim success/failure during server-side outages
                if status_code == 503:
                    return 'ignored', 'service unavailable', 0

                # For most HTTP failures, continue attempting alternate retrieval methods
                continue

            except Exception as err:
                # Unhandled exception (intermittent or permanent); report that
                # the link is broken.
                return 'broken', str(err), 0

        else:
            # All available retrieval methods have been exhausted; report
            # that the link is broken.
            return 'broken', error_message, 0

        # Success; clear rate limits for the origin
        netloc = urlsplit(req_url).netloc
        self.rate_limits.pop(netloc, None)

        if ((response_url.rstrip('/') == req_url.rstrip('/'))
                or _allowed_redirect(req_url, response_url,
                                     self.allowed_redirects)):
            return 'working', '', 0
        elif redirect_status_code is not None:
            return 'redirected', response_url, redirect_status_code
        else:
            return 'redirected', response_url, 0

    def limit_rate(self, response_url: str, retry_after: str) -> float | None:
        delay = DEFAULT_DELAY
        next_check = None
        if retry_after:
            try:
                # Integer: time to wait before next attempt.
                delay = float(retry_after)
            except ValueError:
                try:
                    # An HTTP-date: time of next attempt.
                    next_check = rfc1123_to_epoch(retry_after)
                except (ValueError, TypeError):
                    # TypeError: Invalid date format.
                    # ValueError: Invalid date, e.g. Oct 52th.
                    pass
                else:
                    delay = next_check - time.time()
            else:
                next_check = time.time() + delay
        netloc = urlsplit(response_url).netloc
        if next_check is None:
            max_delay = self.rate_limit_timeout
            try:
                rate_limit = self.rate_limits[netloc]
            except KeyError:
                delay = DEFAULT_DELAY
            else:
                last_wait_time = rate_limit.delay
                delay = 2.0 * last_wait_time
                if delay > max_delay > last_wait_time:
                    delay = max_delay
            if delay > max_delay:
                return None
            next_check = time.time() + delay
        self.rate_limits[netloc] = RateLimit(delay, next_check)
        return next_check


def _get_request_headers(
    uri: str,
    request_headers: dict[str, dict[str, str]],
) -> dict[str, str]:
    url = urlsplit(uri)
    candidates = (f'{url.scheme}://{url.netloc}',
                  f'{url.scheme}://{url.netloc}/',
                  uri,
                  '*')

    for u in candidates:
        if u in request_headers:
            return {**DEFAULT_REQUEST_HEADERS, **request_headers[u]}
    return {}


def contains_anchor(response: Response, anchor: str) -> bool:
    """Determine if an anchor is contained within an HTTP response."""

    parser = AnchorCheckParser(unquote(anchor))
    # Read file in chunks. If we find a matching anchor, we break
    # the loop early in hopes not to have to download the whole thing.
    for chunk in response.iter_content(chunk_size=4096, decode_unicode=True):
        if isinstance(chunk, bytes):    # requests failed to decode
            chunk = chunk.decode()      # manually try to decode it

        parser.feed(chunk)
        if parser.found:
            break
    parser.close()
    return parser.found


class AnchorCheckParser(HTMLParser):
    """Specialised HTML parser that looks for a specific anchor."""

    def __init__(self, search_anchor: str) -> None:
        super().__init__()

        self.search_anchor = search_anchor
        self.found = False

    def handle_starttag(self, tag: Any, attrs: Any) -> None:
        for key, value in attrs:
            if key in ('id', 'name') and value == self.search_anchor:
                self.found = True
                break


def _allowed_redirect(url: str, new_url: str,
                      allowed_redirects: dict[re.Pattern[str], re.Pattern[str]]) -> bool:
    return any(
        from_url.match(url) and to_url.match(new_url)
        for from_url, to_url
        in allowed_redirects.items()
    )


class RateLimit(NamedTuple):
    delay: float
    next_check: float


def rewrite_github_anchor(app: Sphinx, uri: str) -> str | None:
    """Rewrite anchor name of the hyperlink to github.com

    The hyperlink anchors in github.com are dynamically generated.  This rewrites
    them before checking and makes them comparable.
    """
    parsed = urlparse(uri)
    if parsed.hostname == 'github.com' and parsed.fragment:
        prefixed = parsed.fragment.startswith('user-content-')
        if not prefixed:
            fragment = f'user-content-{parsed.fragment}'
            return urlunparse(parsed._replace(fragment=fragment))
    return None


def compile_linkcheck_allowed_redirects(app: Sphinx, config: Config) -> None:
    """Compile patterns in linkcheck_allowed_redirects to the regexp objects."""
    for url, pattern in list(app.config.linkcheck_allowed_redirects.items()):
        try:
            app.config.linkcheck_allowed_redirects[re.compile(url)] = re.compile(pattern)
        except re.error as exc:
            logger.warning(__('Failed to compile regex in linkcheck_allowed_redirects: %r %s'),
                           exc.pattern, exc.msg)
        finally:
            # Remove the original regexp-string
            app.config.linkcheck_allowed_redirects.pop(url)


def setup(app: Sphinx) -> dict[str, Any]:
    app.add_builder(CheckExternalLinksBuilder)
    app.add_post_transform(HyperlinkCollector)

    app.add_config_value('linkcheck_ignore', [], False)
    app.add_config_value('linkcheck_exclude_documents', [], False)
    app.add_config_value('linkcheck_allowed_redirects', {}, False)
    app.add_config_value('linkcheck_auth', [], False)
    app.add_config_value('linkcheck_request_headers', {}, False)
    app.add_config_value('linkcheck_retries', 1, False)
    app.add_config_value('linkcheck_timeout', None, False, [int, float])
    app.add_config_value('linkcheck_workers', 5, False)
    app.add_config_value('linkcheck_anchors', True, False)
    # Anchors starting with ! are ignored since they are
    # commonly used for dynamic pages
    app.add_config_value('linkcheck_anchors_ignore', ['^!'], False)
    app.add_config_value('linkcheck_anchors_ignore_for_url', (), False, (tuple, list))
    app.add_config_value('linkcheck_rate_limit_timeout', 300.0, False)

    app.add_event('linkcheck-process-uri')

    app.connect('config-inited', compile_linkcheck_allowed_redirects, priority=800)

    # FIXME: Disable URL rewrite handler for github.com temporarily.
    # ref: https://github.com/sphinx-doc/sphinx/issues/9435
    # app.connect('linkcheck-process-uri', rewrite_github_anchor)

    return {
        'version': 'builtin',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
