"""Insert links to objects documented in remote Sphinx documentation.

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
"""

from __future__ import annotations

import concurrent.futures
import functools
import posixpath
import re
import sys
import time
from os import path
from typing import TYPE_CHECKING, cast
from urllib.parse import urlsplit, urlunsplit

from docutils import nodes
from docutils.utils import relative_path

import sphinx
from sphinx.addnodes import pending_xref
from sphinx.builders.html import INVENTORY_FILENAME
from sphinx.errors import ExtensionError
from sphinx.locale import _, __
from sphinx.transforms.post_transforms import ReferencesResolver
from sphinx.util import logging, requests
from sphinx.util.docutils import CustomReSTDispatcher, SphinxRole
from sphinx.util.inventory import InventoryFile

if TYPE_CHECKING:
    from collections.abc import Iterable
    from types import ModuleType
    from typing import IO, Any, Union

    from docutils.nodes import Node, TextElement, system_message
    from docutils.utils import Reporter

    from sphinx.application import Sphinx
    from sphinx.config import Config
    from sphinx.domains import Domain
    from sphinx.environment import BuildEnvironment
    from sphinx.util.typing import Inventory, InventoryItem, RoleFunction

    InventoryCacheEntry = tuple[Union[str, None], int, Inventory]

logger = logging.getLogger(__name__)


class InventoryAdapter:
    """Inventory adapter for environment"""

    def __init__(self, env: BuildEnvironment) -> None:
        self.env = env

        if not hasattr(env, 'intersphinx_cache'):
            # initial storage when fetching inventories before processing
            self.env.intersphinx_cache = {}  # type: ignore[attr-defined]

            self.env.intersphinx_inventory = {}  # type: ignore[attr-defined]
            self.env.intersphinx_named_inventory = {}  # type: ignore[attr-defined]

    @property
    def cache(self) -> dict[str, InventoryCacheEntry]:
        """Intersphinx cache.

        - Key is the URI of the remote inventory
        - Element one is the key given in the Sphinx intersphinx_mapping
          configuration value
        - Element two is a time value for cache invalidation, a float
        - Element three is the loaded remote inventory, type Inventory
        """
        return self.env.intersphinx_cache  # type: ignore[attr-defined]

    @property
    def main_inventory(self) -> Inventory:
        return self.env.intersphinx_inventory  # type: ignore[attr-defined]

    @property
    def named_inventory(self) -> dict[str, Inventory]:
        return self.env.intersphinx_named_inventory  # type: ignore[attr-defined]

    def clear(self) -> None:
        self.env.intersphinx_inventory.clear()  # type: ignore[attr-defined]
        self.env.intersphinx_named_inventory.clear()  # type: ignore[attr-defined]


def _strip_basic_auth(url: str) -> str:
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


def _read_from_url(url: str, *, config: Config) -> IO:
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
    r = requests.get(url, stream=True, timeout=config.intersphinx_timeout,
                     _user_agent=config.user_agent,
                     _tls_info=(config.tls_verify, config.tls_cacerts))
    r.raise_for_status()
    r.raw.url = r.url
    # decode content-body based on the header.
    # ref: https://github.com/psf/requests/issues/2155
    r.raw.read = functools.partial(r.raw.read, decode_content=True)
    return r.raw


def _get_safe_url(url: str) -> str:
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
            frags[1] = f'{parts.username}@{parts.hostname}:{parts.port}'
        else:
            frags[1] = f'{parts.username}@{parts.hostname}'

        return urlunsplit(frags)


def fetch_inventory(app: Sphinx, uri: str, inv: str) -> Inventory:
    """Fetch, parse and return an intersphinx inventory file."""
    # both *uri* (base URI of the links to generate) and *inv* (actual
    # location of the inventory file) can be local or remote URIs
    if '://' in uri:
        # case: inv URI points to remote resource; strip any existing auth
        uri = _strip_basic_auth(uri)
    try:
        if '://' in inv:
            f = _read_from_url(inv, config=app.config)
        else:
            f = open(path.join(app.srcdir, inv), 'rb')  # NoQA: SIM115
    except Exception as err:
        err.args = ('intersphinx inventory %r not fetchable due to %s: %s',
                    inv, err.__class__, str(err))
        raise
    try:
        if hasattr(f, 'url'):
            newinv = f.url
            if inv != newinv:
                logger.info(__('intersphinx inventory has moved: %s -> %s'), inv, newinv)

                if uri in (inv, path.dirname(inv), path.dirname(inv) + '/'):
                    uri = path.dirname(newinv)
        with f:
            try:
                invdata = InventoryFile.load(f, uri, posixpath.join)
            except ValueError as exc:
                raise ValueError('unknown or unsupported inventory version: %r' % exc) from exc
    except Exception as err:
        err.args = ('intersphinx inventory %r not readable due to %s: %s',
                    inv, err.__class__.__name__, str(err))
        raise
    else:
        return invdata


def fetch_inventory_group(
    name: str | None,
    uri: str,
    invs: tuple[str | None, ...],
    cache: dict[str, InventoryCacheEntry],
    app: Sphinx,
    now: int,
) -> bool:
    cache_time = now - app.config.intersphinx_cache_limit * 86400
    failures = []
    try:
        for inv in invs:
            if not inv:
                inv = posixpath.join(uri, INVENTORY_FILENAME)
            # decide whether the inventory must be read: always read local
            # files; remote ones only if the cache time is expired
            if '://' not in inv or uri not in cache or cache[uri][1] < cache_time:
                safe_inv_url = _get_safe_url(inv)
                logger.info(__('loading intersphinx inventory from %s...'), safe_inv_url)
                try:
                    invdata = fetch_inventory(app, uri, inv)
                except Exception as err:
                    failures.append(err.args)
                    continue
                if invdata:
                    cache[uri] = name, now, invdata
                    return True
        return False
    finally:
        if failures == []:
            pass
        elif len(failures) < len(invs):
            logger.info(__("encountered some issues with some of the inventories,"
                           " but they had working alternatives:"))
            for fail in failures:
                logger.info(*fail)
        else:
            issues = '\n'.join([f[0] % f[1:] for f in failures])
            logger.warning(__("failed to reach any of the inventories "
                              "with the following issues:") + "\n" + issues)


def load_mappings(app: Sphinx) -> None:
    """Load all intersphinx mappings into the environment."""
    now = int(time.time())
    inventories = InventoryAdapter(app.builder.env)
    intersphinx_cache: dict[str, InventoryCacheEntry] = inventories.cache

    with concurrent.futures.ThreadPoolExecutor() as pool:
        futures = []
        name: str | None
        uri: str
        invs: tuple[str | None, ...]
        for name, (uri, invs) in app.config.intersphinx_mapping.values():
            futures.append(pool.submit(
                fetch_inventory_group, name, uri, invs, intersphinx_cache, app, now,
            ))
        updated = [f.result() for f in concurrent.futures.as_completed(futures)]

    if any(updated):
        inventories.clear()

        # Duplicate values in different inventories will shadow each
        # other; which one will override which can vary between builds
        # since they are specified using an unordered dict.  To make
        # it more consistent, we sort the named inventories and then
        # add the unnamed inventories last.  This means that the
        # unnamed inventories will shadow the named ones but the named
        # ones can still be accessed when the name is specified.
        named_vals = []
        unnamed_vals = []
        for name, _expiry, invdata in intersphinx_cache.values():
            if name:
                named_vals.append((name, invdata))
            else:
                unnamed_vals.append((name, invdata))
        for name, invdata in sorted(named_vals) + unnamed_vals:
            if name:
                inventories.named_inventory[name] = invdata
            for type, objects in invdata.items():
                inventories.main_inventory.setdefault(type, {}).update(objects)


def _create_element_from_result(domain: Domain, inv_name: str | None,
                                data: InventoryItem,
                                node: pending_xref, contnode: TextElement) -> nodes.reference:
    proj, version, uri, dispname = data
    if '://' not in uri and node.get('refdoc'):
        # get correct path in case of subdirectories
        uri = posixpath.join(relative_path(node['refdoc'], '.'), uri)
    if version:
        reftitle = _('(in %s v%s)') % (proj, version)
    else:
        reftitle = _('(in %s)') % (proj,)
    newnode = nodes.reference('', '', internal=False, refuri=uri, reftitle=reftitle)
    if node.get('refexplicit'):
        # use whatever title was given
        newnode.append(contnode)
    elif dispname == '-' or \
            (domain.name == 'std' and node['reftype'] == 'keyword'):
        # use whatever title was given, but strip prefix
        title = contnode.astext()
        if inv_name is not None and title.startswith(inv_name + ':'):
            newnode.append(contnode.__class__(title[len(inv_name) + 1:],
                                              title[len(inv_name) + 1:]))
        else:
            newnode.append(contnode)
    else:
        # else use the given display name (used for :ref:)
        newnode.append(contnode.__class__(dispname, dispname))
    return newnode


def _resolve_reference_in_domain_by_target(
        inv_name: str | None, inventory: Inventory,
        domain: Domain, objtypes: Iterable[str],
        target: str,
        node: pending_xref, contnode: TextElement) -> nodes.reference | None:
    for objtype in objtypes:
        if objtype not in inventory:
            # Continue if there's nothing of this kind in the inventory
            continue

        if target in inventory[objtype]:
            # Case sensitive match, use it
            data = inventory[objtype][target]
        elif objtype == 'std:term':
            # Check for potential case insensitive matches for terms only
            target_lower = target.lower()
            insensitive_matches = list(filter(lambda k: k.lower() == target_lower,
                                              inventory[objtype].keys()))
            if insensitive_matches:
                data = inventory[objtype][insensitive_matches[0]]
            else:
                # No case insensitive match either, continue to the next candidate
                continue
        else:
            # Could reach here if we're not a term but have a case insensitive match.
            # This is a fix for terms specifically, but potentially should apply to
            # other types.
            continue
        return _create_element_from_result(domain, inv_name, data, node, contnode)
    return None


def _resolve_reference_in_domain(env: BuildEnvironment,
                                 inv_name: str | None, inventory: Inventory,
                                 honor_disabled_refs: bool,
                                 domain: Domain, objtypes: Iterable[str],
                                 node: pending_xref, contnode: TextElement,
                                 ) -> nodes.reference | None:
    obj_types: dict[str, None] = {}.fromkeys(objtypes)

    # we adjust the object types for backwards compatibility
    if domain.name == 'std' and 'cmdoption' in obj_types:
        # cmdoptions were stored as std:option until Sphinx 1.6
        obj_types['option'] = None
    if domain.name == 'py' and 'attribute' in obj_types:
        # properties are stored as py:method since Sphinx 2.1
        obj_types['method'] = None

    # the inventory contains domain:type as objtype
    domain_name = domain.name
    obj_types = {f"{domain_name}:{obj_type}": None for obj_type in obj_types}

    # now that the objtypes list is complete we can remove the disabled ones
    if honor_disabled_refs:
        disabled = set(env.config.intersphinx_disabled_reftypes)
        obj_types = {obj_type: None
                     for obj_type in obj_types
                     if obj_type not in disabled}

    objtypes = [*obj_types.keys()]

    # without qualification
    res = _resolve_reference_in_domain_by_target(inv_name, inventory, domain, objtypes,
                                                 node['reftarget'], node, contnode)
    if res is not None:
        return res

    # try with qualification of the current scope instead
    full_qualified_name = domain.get_full_qualified_name(node)
    if full_qualified_name is None:
        return None
    return _resolve_reference_in_domain_by_target(inv_name, inventory, domain, objtypes,
                                                  full_qualified_name, node, contnode)


def _resolve_reference(env: BuildEnvironment, inv_name: str | None, inventory: Inventory,
                       honor_disabled_refs: bool,
                       node: pending_xref, contnode: TextElement) -> nodes.reference | None:
    # disabling should only be done if no inventory is given
    honor_disabled_refs = honor_disabled_refs and inv_name is None

    if honor_disabled_refs and '*' in env.config.intersphinx_disabled_reftypes:
        return None

    typ = node['reftype']
    if typ == 'any':
        for domain_name, domain in env.domains.items():
            if (honor_disabled_refs
                    and (domain_name + ":*") in env.config.intersphinx_disabled_reftypes):
                continue
            objtypes: Iterable[str] = domain.object_types.keys()
            res = _resolve_reference_in_domain(env, inv_name, inventory,
                                               honor_disabled_refs,
                                               domain, objtypes,
                                               node, contnode)
            if res is not None:
                return res
        return None
    else:
        domain_name = node.get('refdomain')
        if not domain_name:
            # only objects in domains are in the inventory
            return None
        if honor_disabled_refs \
                and (domain_name + ":*") in env.config.intersphinx_disabled_reftypes:
            return None
        domain = env.get_domain(domain_name)
        objtypes = domain.objtypes_for_role(typ) or ()
        if not objtypes:
            return None
        return _resolve_reference_in_domain(env, inv_name, inventory,
                                            honor_disabled_refs,
                                            domain, objtypes,
                                            node, contnode)


def inventory_exists(env: BuildEnvironment, inv_name: str) -> bool:
    return inv_name in InventoryAdapter(env).named_inventory


def resolve_reference_in_inventory(env: BuildEnvironment,
                                   inv_name: str,
                                   node: pending_xref, contnode: TextElement,
                                   ) -> nodes.reference | None:
    """Attempt to resolve a missing reference via intersphinx references.

    Resolution is tried in the given inventory with the target as is.

    Requires ``inventory_exists(env, inv_name)``.
    """
    assert inventory_exists(env, inv_name)
    return _resolve_reference(env, inv_name, InventoryAdapter(env).named_inventory[inv_name],
                              False, node, contnode)


def resolve_reference_any_inventory(env: BuildEnvironment,
                                    honor_disabled_refs: bool,
                                    node: pending_xref, contnode: TextElement,
                                    ) -> nodes.reference | None:
    """Attempt to resolve a missing reference via intersphinx references.

    Resolution is tried with the target as is in any inventory.
    """
    return _resolve_reference(env, None, InventoryAdapter(env).main_inventory,
                              honor_disabled_refs,
                              node, contnode)


def resolve_reference_detect_inventory(env: BuildEnvironment,
                                       node: pending_xref, contnode: TextElement,
                                       ) -> nodes.reference | None:
    """Attempt to resolve a missing reference via intersphinx references.

    Resolution is tried first with the target as is in any inventory.
    If this does not succeed, then the target is split by the first ``:``,
    to form ``inv_name:newtarget``. If ``inv_name`` is a named inventory, then resolution
    is tried in that inventory with the new target.
    """

    # ordinary direct lookup, use data as is
    res = resolve_reference_any_inventory(env, True, node, contnode)
    if res is not None:
        return res

    # try splitting the target into 'inv_name:target'
    target = node['reftarget']
    if ':' not in target:
        return None
    inv_name, newtarget = target.split(':', 1)
    if not inventory_exists(env, inv_name):
        return None
    node['reftarget'] = newtarget
    res_inv = resolve_reference_in_inventory(env, inv_name, node, contnode)
    node['reftarget'] = target
    return res_inv


def missing_reference(app: Sphinx, env: BuildEnvironment, node: pending_xref,
                      contnode: TextElement) -> nodes.reference | None:
    """Attempt to resolve a missing reference via intersphinx references."""

    return resolve_reference_detect_inventory(env, node, contnode)


class IntersphinxDispatcher(CustomReSTDispatcher):
    """Custom dispatcher for external role.

    This enables :external:***:/:external+***: roles on parsing reST document.
    """

    def role(
        self, role_name: str, language_module: ModuleType, lineno: int, reporter: Reporter,
    ) -> tuple[RoleFunction, list[system_message]]:
        if len(role_name) > 9 and role_name.startswith(('external:', 'external+')):
            return IntersphinxRole(role_name), []
        else:
            return super().role(role_name, language_module, lineno, reporter)


class IntersphinxRole(SphinxRole):
    # group 1: just for the optionality of the inventory name
    # group 2: the inventory name (optional)
    # group 3: the domain:role or role part
    _re_inv_ref = re.compile(r"(\+([^:]+))?:(.*)")

    def __init__(self, orig_name: str) -> None:
        self.orig_name = orig_name

    def run(self) -> tuple[list[Node], list[system_message]]:
        assert self.name == self.orig_name.lower()
        inventory, name_suffix = self.get_inventory_and_name_suffix(self.orig_name)
        if inventory and not inventory_exists(self.env, inventory):
            logger.warning(__('inventory for external cross-reference not found: %s'),
                           inventory, location=(self.env.docname, self.lineno))
            return [], []

        role_name = self.get_role_name(name_suffix)
        if role_name is None:
            logger.warning(__('role for external cross-reference not found: %s'), name_suffix,
                           location=(self.env.docname, self.lineno))
            return [], []

        result, messages = self.invoke_role(role_name)
        for node in result:
            if isinstance(node, pending_xref):
                node['intersphinx'] = True
                node['inventory'] = inventory

        return result, messages

    def get_inventory_and_name_suffix(self, name: str) -> tuple[str | None, str]:
        assert name.startswith('external'), name
        # either we have an explicit inventory name, i.e,
        # :external+inv:role:        or
        # :external+inv:domain:role:
        # or we look in all inventories, i.e.,
        # :external:role:            or
        # :external:domain:role:
        suffix = name[9:]
        if name[8] == '+':
            inv_name, suffix = suffix.split(':', 1)
            return inv_name, suffix
        elif name[8] == ':':
            return None, suffix
        else:
            msg = f'Malformed :external: role name: {name}'
            raise ValueError(msg)

    def get_role_name(self, name: str) -> tuple[str, str] | None:
        names = name.split(':')
        if len(names) == 1:
            # role
            default_domain = self.env.temp_data.get('default_domain')
            domain = default_domain.name if default_domain else None
            role = names[0]
        elif len(names) == 2:
            # domain:role:
            domain = names[0]
            role = names[1]
        else:
            return None

        if domain and self.is_existent_role(domain, role):
            return (domain, role)
        elif self.is_existent_role('std', role):
            return ('std', role)
        else:
            return None

    def is_existent_role(self, domain_name: str, role_name: str) -> bool:
        try:
            domain = self.env.get_domain(domain_name)
            return role_name in domain.roles
        except ExtensionError:
            return False

    def invoke_role(self, role: tuple[str, str]) -> tuple[list[Node], list[system_message]]:
        domain = self.env.get_domain(role[0])
        if domain:
            role_func = domain.role(role[1])
            assert role_func is not None

            return role_func(':'.join(role), self.rawtext, self.text, self.lineno,
                             self.inliner, self.options, self.content)
        else:
            return [], []


class IntersphinxRoleResolver(ReferencesResolver):
    """pending_xref node resolver for intersphinx role.

    This resolves pending_xref nodes generated by :intersphinx:***: role.
    """

    default_priority = ReferencesResolver.default_priority - 1

    def run(self, **kwargs: Any) -> None:
        for node in self.document.findall(pending_xref):
            if 'intersphinx' not in node:
                continue
            contnode = cast(nodes.TextElement, node[0].deepcopy())
            inv_name = node['inventory']
            if inv_name is not None:
                assert inventory_exists(self.env, inv_name)
                newnode = resolve_reference_in_inventory(self.env, inv_name, node, contnode)
            else:
                newnode = resolve_reference_any_inventory(self.env, False, node, contnode)
            if newnode is None:
                typ = node['reftype']
                msg = (__('external %s:%s reference target not found: %s') %
                       (node['refdomain'], typ, node['reftarget']))
                logger.warning(msg, location=node, type='ref', subtype=typ)
                node.replace_self(contnode)
            else:
                node.replace_self(newnode)


def install_dispatcher(app: Sphinx, docname: str, source: list[str]) -> None:
    """Enable IntersphinxDispatcher.

    .. note:: The installed dispatcher will be uninstalled on disabling sphinx_domain
              automatically.
    """
    dispatcher = IntersphinxDispatcher()
    dispatcher.enable()


def normalize_intersphinx_mapping(app: Sphinx, config: Config) -> None:
    for key, value in config.intersphinx_mapping.copy().items():
        try:
            if isinstance(value, (list, tuple)):
                # new format
                name, (uri, inv) = key, value
                if not isinstance(name, str):
                    logger.warning(__('intersphinx identifier %r is not string. Ignored'),
                                   name)
                    config.intersphinx_mapping.pop(key)
                    continue
            else:
                # old format, no name
                # xref RemovedInSphinx80Warning
                name, uri, inv = None, key, value
                msg = (
                    "The pre-Sphinx 1.0 'intersphinx_mapping' format is "
                    "deprecated and will be removed in Sphinx 8. Update to the "
                    "current format as described in the documentation. "
                    f"Hint: \"intersphinx_mapping = {{'<name>': {(uri, inv)!r}}}\"."
                    "https://www.sphinx-doc.org/en/master/usage/extensions/intersphinx.html#confval-intersphinx_mapping"  # NoQA: E501
                )
                logger.warning(msg)

            if not isinstance(inv, tuple):
                config.intersphinx_mapping[key] = (name, (uri, (inv,)))
            else:
                config.intersphinx_mapping[key] = (name, (uri, inv))
        except Exception as exc:
            logger.warning(__('Failed to read intersphinx_mapping[%s], ignored: %r'), key, exc)
            config.intersphinx_mapping.pop(key)


def setup(app: Sphinx) -> dict[str, Any]:
    app.add_config_value('intersphinx_mapping', {}, True)
    app.add_config_value('intersphinx_cache_limit', 5, False)
    app.add_config_value('intersphinx_timeout', None, False)
    app.add_config_value('intersphinx_disabled_reftypes', ['std:doc'], True)
    app.connect('config-inited', normalize_intersphinx_mapping, priority=800)
    app.connect('builder-inited', load_mappings)
    app.connect('source-read', install_dispatcher)
    app.connect('missing-reference', missing_reference)
    app.add_post_transform(IntersphinxRoleResolver)
    return {
        'version': sphinx.__display_version__,
        'env_version': 1,
        'parallel_read_safe': True,
    }


def inspect_main(argv: list[str], /) -> int:
    """Debug functionality to print out an inventory"""
    if len(argv) < 1:
        print("Print out an inventory file.\n"
              "Error: must specify local path or URL to an inventory file.",
              file=sys.stderr)
        return 1

    class MockConfig:
        intersphinx_timeout: int | None = None
        tls_verify = False
        tls_cacerts: str | dict[str, str] | None = None
        user_agent: str = ''

    class MockApp:
        srcdir = ''
        config = MockConfig()

    try:
        filename = argv[0]
        inv_data = fetch_inventory(MockApp(), '', filename)  # type: ignore[arg-type]
        for key in sorted(inv_data or {}):
            print(key)
            inv_entries = sorted(inv_data[key].items())
            for entry, (_proj, _ver, url_path, display_name) in inv_entries:
                display_name = display_name * (display_name != '-')
                print(f'    {entry:<40} {display_name:<40}: {url_path}')
    except ValueError as exc:
        print(exc.args[0] % exc.args[1:], file=sys.stderr)
        return 1
    except Exception as exc:
        print(f'Unknown error: {exc!r}', file=sys.stderr)
        return 1
    else:
        return 0


if __name__ == '__main__':
    import logging as _logging
    _logging.basicConfig()

    raise SystemExit(inspect_main(sys.argv[1:]))
