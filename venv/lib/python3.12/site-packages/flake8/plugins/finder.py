"""Functions related to finding and loading plugins."""
from __future__ import annotations

import configparser
import importlib.metadata
import inspect
import itertools
import logging
import sys
from typing import Any
from typing import Generator
from typing import Iterable
from typing import NamedTuple

from flake8 import utils
from flake8.defaults import VALID_CODE_PREFIX
from flake8.exceptions import ExecutionError
from flake8.exceptions import FailedToLoadPlugin

LOG = logging.getLogger(__name__)

FLAKE8_GROUPS = frozenset(("flake8.extension", "flake8.report"))

BANNED_PLUGINS = {
    "flake8-colors": "5.0",
    "flake8-per-file-ignores": "3.7",
}


class Plugin(NamedTuple):
    """A plugin before loading."""

    package: str
    version: str
    entry_point: importlib.metadata.EntryPoint


class LoadedPlugin(NamedTuple):
    """Represents a plugin after being imported."""

    plugin: Plugin
    obj: Any
    parameters: dict[str, bool]

    @property
    def entry_name(self) -> str:
        """Return the name given in the packaging metadata."""
        return self.plugin.entry_point.name

    @property
    def display_name(self) -> str:
        """Return the name for use in user-facing / error messages."""
        return f"{self.plugin.package}[{self.entry_name}]"


class Checkers(NamedTuple):
    """Classified plugins needed for checking."""

    tree: list[LoadedPlugin]
    logical_line: list[LoadedPlugin]
    physical_line: list[LoadedPlugin]


class Plugins(NamedTuple):
    """Classified plugins."""

    checkers: Checkers
    reporters: dict[str, LoadedPlugin]
    disabled: list[LoadedPlugin]

    def all_plugins(self) -> Generator[LoadedPlugin, None, None]:
        """Return an iterator over all :class:`LoadedPlugin`s."""
        yield from self.checkers.tree
        yield from self.checkers.logical_line
        yield from self.checkers.physical_line
        yield from self.reporters.values()

    def versions_str(self) -> str:
        """Return a user-displayed list of plugin versions."""
        return ", ".join(
            sorted(
                {
                    f"{loaded.plugin.package}: {loaded.plugin.version}"
                    for loaded in self.all_plugins()
                    if loaded.plugin.package not in {"flake8", "local"}
                }
            )
        )


class PluginOptions(NamedTuple):
    """Options related to plugin loading."""

    local_plugin_paths: tuple[str, ...]
    enable_extensions: frozenset[str]
    require_plugins: frozenset[str]

    @classmethod
    def blank(cls) -> PluginOptions:
        """Make a blank PluginOptions, mostly used for tests."""
        return cls(
            local_plugin_paths=(),
            enable_extensions=frozenset(),
            require_plugins=frozenset(),
        )


def _parse_option(
    cfg: configparser.RawConfigParser,
    cfg_opt_name: str,
    opt: str | None,
) -> list[str]:
    # specified on commandline: use that
    if opt is not None:
        return utils.parse_comma_separated_list(opt)
    else:
        # ideally this would reuse our config parsing framework but we need to
        # parse this from preliminary options before plugins are enabled
        for opt_name in (cfg_opt_name, cfg_opt_name.replace("_", "-")):
            val = cfg.get("flake8", opt_name, fallback=None)
            if val is not None:
                return utils.parse_comma_separated_list(val)
        else:
            return []


def parse_plugin_options(
    cfg: configparser.RawConfigParser,
    cfg_dir: str,
    *,
    enable_extensions: str | None,
    require_plugins: str | None,
) -> PluginOptions:
    """Parse plugin loading related options."""
    paths_s = cfg.get("flake8:local-plugins", "paths", fallback="").strip()
    paths = utils.parse_comma_separated_list(paths_s)
    paths = utils.normalize_paths(paths, cfg_dir)

    return PluginOptions(
        local_plugin_paths=tuple(paths),
        enable_extensions=frozenset(
            _parse_option(cfg, "enable_extensions", enable_extensions),
        ),
        require_plugins=frozenset(
            _parse_option(cfg, "require_plugins", require_plugins),
        ),
    )


def _flake8_plugins(
    eps: Iterable[importlib.metadata.EntryPoint],
    name: str,
    version: str,
) -> Generator[Plugin, None, None]:
    pyflakes_meta = importlib.metadata.distribution("pyflakes").metadata
    pycodestyle_meta = importlib.metadata.distribution("pycodestyle").metadata

    for ep in eps:
        if ep.group not in FLAKE8_GROUPS:
            continue

        if ep.name == "F":
            yield Plugin(pyflakes_meta["name"], pyflakes_meta["version"], ep)
        elif ep.name in "EW":
            # pycodestyle provides both `E` and `W` -- but our default select
            # handles those
            # ideally pycodestyle's plugin entrypoints would exactly represent
            # the codes they produce...
            yield Plugin(
                pycodestyle_meta["name"], pycodestyle_meta["version"], ep
            )
        else:
            yield Plugin(name, version, ep)


def _find_importlib_plugins() -> Generator[Plugin, None, None]:
    # some misconfigured pythons (RHEL) have things on `sys.path` twice
    seen = set()
    for dist in importlib.metadata.distributions():
        # assigned to prevent continual reparsing
        eps = dist.entry_points

        # perf: skip parsing `.metadata` (slow) if no entry points match
        if not any(ep.group in FLAKE8_GROUPS for ep in eps):
            continue

        # assigned to prevent continual reparsing
        meta = dist.metadata

        if meta["name"] in seen:
            continue
        else:
            seen.add(meta["name"])

        if meta["name"] in BANNED_PLUGINS:
            LOG.warning(
                "%s plugin is obsolete in flake8>=%s",
                meta["name"],
                BANNED_PLUGINS[meta["name"]],
            )
            continue
        elif meta["name"] == "flake8":
            # special case flake8 which provides plugins for pyflakes /
            # pycodestyle
            yield from _flake8_plugins(eps, meta["name"], meta["version"])
            continue

        for ep in eps:
            if ep.group in FLAKE8_GROUPS:
                yield Plugin(meta["name"], meta["version"], ep)


def _find_local_plugins(
    cfg: configparser.RawConfigParser,
) -> Generator[Plugin, None, None]:
    for plugin_type in ("extension", "report"):
        group = f"flake8.{plugin_type}"
        for plugin_s in utils.parse_comma_separated_list(
            cfg.get("flake8:local-plugins", plugin_type, fallback="").strip(),
            regexp=utils.LOCAL_PLUGIN_LIST_RE,
        ):
            name, _, entry_str = plugin_s.partition("=")
            name, entry_str = name.strip(), entry_str.strip()
            ep = importlib.metadata.EntryPoint(name, entry_str, group)
            yield Plugin("local", "local", ep)


def _check_required_plugins(
    plugins: list[Plugin],
    expected: frozenset[str],
) -> None:
    plugin_names = {
        utils.normalize_pypi_name(plugin.package) for plugin in plugins
    }
    expected_names = {utils.normalize_pypi_name(name) for name in expected}
    missing_plugins = expected_names - plugin_names

    if missing_plugins:
        raise ExecutionError(
            f"required plugins were not installed!\n"
            f"- installed: {', '.join(sorted(plugin_names))}\n"
            f"- expected: {', '.join(sorted(expected_names))}\n"
            f"- missing: {', '.join(sorted(missing_plugins))}"
        )


def find_plugins(
    cfg: configparser.RawConfigParser,
    opts: PluginOptions,
) -> list[Plugin]:
    """Discovers all plugins (but does not load them)."""
    ret = [*_find_importlib_plugins(), *_find_local_plugins(cfg)]

    # for determinism, sort the list
    ret.sort()

    _check_required_plugins(ret, opts.require_plugins)

    return ret


def _parameters_for(func: Any) -> dict[str, bool]:
    """Return the parameters for the plugin.

    This will inspect the plugin and return either the function parameters
    if the plugin is a function or the parameters for ``__init__`` after
    ``self`` if the plugin is a class.

    :returns:
        A dictionary mapping the parameter name to whether or not it is
        required (a.k.a., is positional only/does not have a default).
    """
    is_class = not inspect.isfunction(func)
    if is_class:
        func = func.__init__

    parameters = {
        parameter.name: parameter.default is inspect.Parameter.empty
        for parameter in inspect.signature(func).parameters.values()
        if parameter.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    }

    if is_class:
        parameters.pop("self", None)

    return parameters


def _load_plugin(plugin: Plugin) -> LoadedPlugin:
    try:
        obj = plugin.entry_point.load()
    except Exception as e:
        raise FailedToLoadPlugin(plugin.package, e)

    if not callable(obj):
        err = TypeError("expected loaded plugin to be callable")
        raise FailedToLoadPlugin(plugin.package, err)

    return LoadedPlugin(plugin, obj, _parameters_for(obj))


def _import_plugins(
    plugins: list[Plugin],
    opts: PluginOptions,
) -> list[LoadedPlugin]:
    sys.path.extend(opts.local_plugin_paths)
    return [_load_plugin(p) for p in plugins]


def _classify_plugins(
    plugins: list[LoadedPlugin],
    opts: PluginOptions,
) -> Plugins:
    tree = []
    logical_line = []
    physical_line = []
    reporters = {}
    disabled = []

    for loaded in plugins:
        if (
            getattr(loaded.obj, "off_by_default", False)
            and loaded.plugin.entry_point.name not in opts.enable_extensions
        ):
            disabled.append(loaded)
        elif loaded.plugin.entry_point.group == "flake8.report":
            reporters[loaded.entry_name] = loaded
        elif "tree" in loaded.parameters:
            tree.append(loaded)
        elif "logical_line" in loaded.parameters:
            logical_line.append(loaded)
        elif "physical_line" in loaded.parameters:
            physical_line.append(loaded)
        else:
            raise NotImplementedError(f"what plugin type? {loaded}")

    for loaded in itertools.chain(tree, logical_line, physical_line):
        if not VALID_CODE_PREFIX.match(loaded.entry_name):
            raise ExecutionError(
                f"plugin code for `{loaded.display_name}` does not match "
                f"{VALID_CODE_PREFIX.pattern}"
            )

    return Plugins(
        checkers=Checkers(
            tree=tree,
            logical_line=logical_line,
            physical_line=physical_line,
        ),
        reporters=reporters,
        disabled=disabled,
    )


def load_plugins(
    plugins: list[Plugin],
    opts: PluginOptions,
) -> Plugins:
    """Load and classify all flake8 plugins.

    - first: extends ``sys.path`` with ``paths`` (to import local plugins)
    - next: converts the ``Plugin``s to ``LoadedPlugins``
    - finally: classifies plugins into their specific types
    """
    return _classify_plugins(_import_plugins(plugins, opts), opts)
