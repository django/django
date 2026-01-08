from __future__ import annotations

from .base import PluginLoader


class Discovery(PluginLoader):
    """Discovery plugins."""


def get_discover(parser, args):
    discover_types = Discovery.entry_points_for("virtualenv.discovery")
    discovery_parser = parser.add_argument_group(
        title="discovery",
        description="discover and provide a target interpreter",
    )
    choices = _get_default_discovery(discover_types)
    # prefer the builtin if present, otherwise fallback to first defined type
    choices = sorted(choices, key=lambda a: 0 if a == "builtin" else 1)
    try:
        default_discovery = next(iter(choices))
    except StopIteration as e:
        msg = "No discovery plugin found. Try reinstalling virtualenv to fix this issue."
        raise RuntimeError(msg) from e
    discovery_parser.add_argument(
        "--discovery",
        choices=choices,
        default=default_discovery,
        required=False,
        help="interpreter discovery method",
    )
    options, _ = parser.parse_known_args(args)
    discover_class = discover_types[options.discovery]
    discover_class.add_parser_arguments(discovery_parser)
    options, _ = parser.parse_known_args(args, namespace=options)
    return discover_class(options)


def _get_default_discovery(discover_types):
    return list(discover_types.keys())


__all__ = [
    "Discovery",
    "get_discover",
]
