# -*- coding: utf-8 -*-
"""
    sphinx.ext.intersphinx
    ~~~~~~~~~~~~~~~~~~~~~~

    Insert links to objects documented in remote Sphinx documentation.

    This works as follows:

    * Each Sphinx HTML build creates a file named "objects.inv" that contains a
      mapping from object names to URIs relative to the HTML set's root.

    * Projects using the Intersphinx extension can specify links to such mapping
      files in the `intersphinx_mapping` config value.  The mapping will then be
      used to resolve otherwise missing references to objects into links to the
      other documentation.

    * By default, the mapping file is assumed to be at the same location as the
      rest of the documentation; however, the location of the mapping file can
      also be specified individually, e.g. if the docs should be buildable
      without Internet access.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from __future__ import print_function

import functools
import posixpath
import sys
import time
import warnings
from os import path

from docutils import nodes
from docutils.utils import relative_path
from six import PY3, iteritems, string_types
from six.moves.urllib.parse import urlsplit, urlunsplit

import sphinx
from sphinx.builders.html import INVENTORY_FILENAME
from sphinx.deprecation import RemovedInSphinx20Warning
from sphinx.locale import _, __
from sphinx.util import requests, logging
from sphinx.util.inventory import InventoryFile

if False:
    # For type annotation
    from typing import Any, Dict, IO, List, Tuple, Union  # NOQA
    from sphinx.application import Sphinx  # NOQA
    from sphinx.config import Config  # NOQA
    from sphinx.environment import BuildEnvironment  # NOQA

    if PY3:
        unicode = str

    Inventory = Dict[unicode, Dict[unicode, Tuple[unicode, unicode, unicode, unicode]]]

logger = logging.getLogger(__name__)


class InventoryAdapter(object):
    """Inventory adapter for environment"""

    def __init__(self, env):
        # type: (BuildEnvironment) -> None
        self.env = env

        if not hasattr(env, 'intersphinx_cache'):
            self.env.intersphinx_cache = {}  # type: ignore
            self.env.intersphinx_inventory = {}  # type: ignore
            self.env.intersphinx_named_inventory = {}  # type: ignore

    @property
    def cache(self):
        # type: () -> Dict[unicode, Tuple[unicode, int, Inventory]]
        return self.env.intersphinx_cache  # type: ignore

    @property
    def main_inventory(self):
        # type: () -> Inventory
        return self.env.intersphinx_inventory  # type: ignore

    @property
    def named_inventory(self):
        # type: () -> Dict[unicode, Inventory]
        return self.env.intersphinx_named_inventory  # type: ignore

    def clear(self):
        # type: () -> None
        self.env.intersphinx_inventory.clear()  # type: ignore
        self.env.intersphinx_named_inventory.clear()  # type: ignore


def _strip_basic_auth(url):
    # type: (unicode) -> unicode
    """Returns *url* with basic auth credentials removed. Also returns the
    basic auth username and password if they're present in *url*.

    E.g.: https://user:pass@example.com => https://example.com

    *url* need not include basic auth credentials.

    :param url: url which may or may not contain basic auth credentials
    :type url: ``str``

    :return: *url* with any basic auth creds removed
    :rtype: ``str``
    """
    frags = list(urlsplit(url))
    # swap out "user[:pass]@hostname" for "hostname"
    if '@' in frags[1]:
        frags[1] = frags[1].split('@')[1]
    return urlunsplit(frags)


def _read_from_url(url, config=None):
    # type: (unicode, Config) -> IO
    """Reads data from *url* with an HTTP *GET*.

    This function supports fetching from resources which use basic HTTP auth as
    laid out by RFC1738 § 3.1. See § 5 for grammar definitions for URLs.

    .. seealso:

       https://www.ietf.org/rfc/rfc1738.txt

    :param url: URL of an HTTP resource
    :type url: ``str``

    :return: data read from resource described by *url*
    :rtype: ``file``-like object
    """
    r = requests.get(url, stream=True, config=config, timeout=config.intersphinx_timeout)
    r.raise_for_status()
    r.raw.url = r.url
    # decode content-body based on the header.
    # ref: https://github.com/kennethreitz/requests/issues/2155
    r.raw.read = functools.partial(r.raw.read, decode_content=True)
    return r.raw


def _get_safe_url(url):
    # type: (unicode) -> unicode
    """Gets version of *url* with basic auth passwords obscured. This function
    returns results suitable for printing and logging.

    E.g.: https://user:12345@example.com => https://user@example.com

    :param url: a url
    :type url: ``str``

    :return: *url* with password removed
    :rtype: ``str``
    """
    parts = urlsplit(url)
    if parts.username is None:
        return url
    else:
        frags = list(parts)
        if parts.port:
            frags[1] = '{0}@{1}:{2}'.format(parts.username, parts.hostname, parts.port)
        else:
            frags[1] = '{0}@{1}'.format(parts.username, parts.hostname)

        return urlunsplit(frags)


def fetch_inventory(app, uri, inv):
    # type: (Sphinx, unicode, Any) -> Any
    """Fetch, parse and return an intersphinx inventory file."""
    # both *uri* (base URI of the links to generate) and *inv* (actual
    # location of the inventory file) can be local or remote URIs
    localuri = '://' not in uri
    if not localuri:
        # case: inv URI points to remote resource; strip any existing auth
        uri = _strip_basic_auth(uri)
    try:
        if '://' in inv:
            f = _read_from_url(inv, config=app.config)
        else:
            f = open(path.join(app.srcdir, inv), 'rb')
    except Exception as err:
        err.args = ('intersphinx inventory %r not fetchable due to %s: %s',
                    inv, err.__class__, str(err))
        raise
    try:
        if hasattr(f, 'url'):
            newinv = f.url  # type: ignore
            if inv != newinv:
                logger.info('intersphinx inventory has moved: %s -> %s', inv, newinv)

                if uri in (inv, path.dirname(inv), path.dirname(inv) + '/'):
                    uri = path.dirname(newinv)
        with f:
            try:
                join = localuri and path.join or posixpath.join
                invdata = InventoryFile.load(f, uri, join)
            except ValueError as exc:
                raise ValueError('unknown or unsupported inventory version: %r' % exc)
    except Exception as err:
        err.args = ('intersphinx inventory %r not readable due to %s: %s',
                    inv, err.__class__.__name__, str(err))
        raise
    else:
        return invdata


def load_mappings(app):
    # type: (Sphinx) -> None
    """Load all intersphinx mappings into the environment."""
    now = int(time.time())
    cache_time = now - app.config.intersphinx_cache_limit * 86400
    inventories = InventoryAdapter(app.builder.env)
    update = False
    for key, value in iteritems(app.config.intersphinx_mapping):
        name = None  # type: unicode
        uri = None   # type: unicode
        inv = None   # type: Union[unicode, Tuple[unicode, ...]]

        if isinstance(value, (list, tuple)):
            # new format
            name, (uri, inv) = key, value
            if not isinstance(name, string_types):
                logger.warning(__('intersphinx identifier %r is not string. Ignored'), name)
                continue
        else:
            # old format, no name
            name, uri, inv = None, key, value
        # we can safely assume that the uri<->inv mapping is not changed
        # during partial rebuilds since a changed intersphinx_mapping
        # setting will cause a full environment reread
        if not isinstance(inv, tuple):
            invs = (inv, )
        else:
            invs = inv  # type: ignore

        failures = []
        for inv in invs:
            if not inv:
                inv = posixpath.join(uri, INVENTORY_FILENAME)
            # decide whether the inventory must be read: always read local
            # files; remote ones only if the cache time is expired
            if '://' not in inv or uri not in inventories.cache \
                    or inventories.cache[uri][1] < cache_time:
                safe_inv_url = _get_safe_url(inv)
                logger.info('loading intersphinx inventory from %s...', safe_inv_url)
                try:
                    invdata = fetch_inventory(app, uri, inv)
                except Exception as err:
                    failures.append(err.args)
                    continue

                if invdata:
                    inventories.cache[uri] = (name, now, invdata)
                    update = True
                    break

        if failures == []:
            pass
        elif len(failures) < len(invs):
            logger.info("encountered some issues with some of the inventories,"
                        " but they had working alternatives:")
            for fail in failures:
                logger.info(*fail)
        else:
            issues = '\n'.join([f[0] % f[1:] for f in failures])
            logger.warning(__("failed to reach any of the inventories "
                              "with the following issues:") + "\n" + issues)

    if update:
        inventories.clear()

        # Duplicate values in different inventories will shadow each
        # other; which one will override which can vary between builds
        # since they are specified using an unordered dict.  To make
        # it more consistent, we sort the named inventories and then
        # add the unnamed inventories last.  This means that the
        # unnamed inventories will shadow the named ones but the named
        # ones can still be accessed when the name is specified.
        cached_vals = list(inventories.cache.values())
        named_vals = sorted(v for v in cached_vals if v[0])
        unnamed_vals = [v for v in cached_vals if not v[0]]
        for name, _x, invdata in named_vals + unnamed_vals:
            if name:
                inventories.named_inventory[name] = invdata
            for type, objects in iteritems(invdata):
                inventories.main_inventory.setdefault(type, {}).update(objects)


def missing_reference(app, env, node, contnode):
    # type: (Sphinx, BuildEnvironment, nodes.Node, nodes.Node) -> None
    """Attempt to resolve a missing reference via intersphinx references."""
    target = node['reftarget']
    inventories = InventoryAdapter(env)
    objtypes = None  # type: List[unicode]
    if node['reftype'] == 'any':
        # we search anything!
        objtypes = ['%s:%s' % (domain.name, objtype)
                    for domain in env.domains.values()
                    for objtype in domain.object_types]
        domain = None
    else:
        domain = node.get('refdomain')
        if not domain:
            # only objects in domains are in the inventory
            return
        objtypes = env.get_domain(domain).objtypes_for_role(node['reftype'])
        if not objtypes:
            return
        objtypes = ['%s:%s' % (domain, objtype) for objtype in objtypes]
    if 'std:cmdoption' in objtypes:
        # until Sphinx-1.6, cmdoptions are stored as std:option
        objtypes.append('std:option')
    to_try = [(inventories.main_inventory, target)]
    if domain:
        full_qualified_name = env.get_domain(domain).get_full_qualified_name(node)
        if full_qualified_name:
            to_try.append((inventories.main_inventory, full_qualified_name))
    in_set = None
    if ':' in target:
        # first part may be the foreign doc set name
        setname, newtarget = target.split(':', 1)
        if setname in inventories.named_inventory:
            in_set = setname
            to_try.append((inventories.named_inventory[setname], newtarget))
            if domain:
                node['reftarget'] = newtarget
                full_qualified_name = env.get_domain(domain).get_full_qualified_name(node)
                if full_qualified_name:
                    to_try.append((inventories.named_inventory[setname], full_qualified_name))
    for inventory, target in to_try:
        for objtype in objtypes:
            if objtype not in inventory or target not in inventory[objtype]:
                continue
            proj, version, uri, dispname = inventory[objtype][target]
            if '://' not in uri and node.get('refdoc'):
                # get correct path in case of subdirectories
                uri = path.join(relative_path(node['refdoc'], '.'), uri)
            if version:
                reftitle = _('(in %s v%s)') % (proj, version)
            else:
                reftitle = _('(in %s)') % (proj,)
            newnode = nodes.reference('', '', internal=False, refuri=uri, reftitle=reftitle)
            if node.get('refexplicit'):
                # use whatever title was given
                newnode.append(contnode)
            elif dispname == '-' or \
                    (domain == 'std' and node['reftype'] == 'keyword'):
                # use whatever title was given, but strip prefix
                title = contnode.astext()
                if in_set and title.startswith(in_set + ':'):
                    newnode.append(contnode.__class__(title[len(in_set) + 1:],
                                                      title[len(in_set) + 1:]))
                else:
                    newnode.append(contnode)
            else:
                # else use the given display name (used for :ref:)
                newnode.append(contnode.__class__(dispname, dispname))
            return newnode
    # at least get rid of the ':' in the target if no explicit title given
    if in_set is not None and not node.get('refexplicit', True):
        if len(contnode) and isinstance(contnode[0], nodes.Text):
            contnode[0] = nodes.Text(newtarget, contnode[0].rawsource)


def setup(app):
    # type: (Sphinx) -> Dict[unicode, Any]
    app.add_config_value('intersphinx_mapping', {}, True)
    app.add_config_value('intersphinx_cache_limit', 5, False)
    app.add_config_value('intersphinx_timeout', None, False)
    app.connect('missing-reference', missing_reference)
    app.connect('builder-inited', load_mappings)
    return {
        'version': sphinx.__display_version__,
        'env_version': 1,
        'parallel_read_safe': True
    }


def debug(argv):
    # type: (List[unicode]) -> None
    """Debug functionality to print out an inventory"""
    warnings.warn('sphinx.ext.intersphinx.debug() is deprecated. '
                  'Please use inspect_main() instead',
                  RemovedInSphinx20Warning, stacklevel=2)
    inspect_main(argv[1:])


def inspect_main(argv):
    # type: (List[unicode]) -> None
    """Debug functionality to print out an inventory"""
    if len(argv) < 1:
        print("Print out an inventory file.\n"
              "Error: must specify local path or URL to an inventory file.",
              file=sys.stderr)
        sys.exit(1)

    class MockConfig(object):
        intersphinx_timeout = None  # type: int
        tls_verify = False

    class MockApp(object):
        srcdir = ''
        config = MockConfig()

        def warn(self, msg):
            # type: (unicode) -> None
            print(msg, file=sys.stderr)

    try:
        filename = argv[0]
        invdata = fetch_inventory(MockApp(), '', filename)  # type: ignore
        for key in sorted(invdata or {}):
            print(key)
            for entry, einfo in sorted(invdata[key].items()):
                print('\t%-40s %s%s' % (entry,
                                        einfo[3] != '-' and '%-40s: ' % einfo[3] or '',
                                        einfo[2]))
    except ValueError as exc:
        print(exc.args[0] % exc.args[1:])
    except Exception as exc:
        print('Unknown error: %r' % exc)


if __name__ == '__main__':
    import logging  # type: ignore
    logging.basicConfig()  # type: ignore

    inspect_main(argv=sys.argv[1:])  # type: ignore
