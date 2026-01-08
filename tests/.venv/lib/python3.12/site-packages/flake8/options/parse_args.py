"""Procedure for parsing args, config, loading plugins."""
from __future__ import annotations

import argparse
from collections.abc import Sequence

import flake8
from flake8.main import options
from flake8.options import aggregator
from flake8.options import config
from flake8.options import manager
from flake8.plugins import finder


def parse_args(
    argv: Sequence[str],
) -> tuple[finder.Plugins, argparse.Namespace]:
    """Procedure for parsing args, config, loading plugins."""
    prelim_parser = options.stage1_arg_parser()

    args0, rest = prelim_parser.parse_known_args(argv)
    # XXX (ericvw): Special case "forwarding" the output file option so
    # that it can be reparsed again for the BaseFormatter.filename.
    if args0.output_file:
        rest.extend(("--output-file", args0.output_file))

    flake8.configure_logging(args0.verbose, args0.output_file)

    cfg, cfg_dir = config.load_config(
        config=args0.config,
        extra=args0.append_config,
        isolated=args0.isolated,
    )

    plugin_opts = finder.parse_plugin_options(
        cfg,
        cfg_dir,
        enable_extensions=args0.enable_extensions,
        require_plugins=args0.require_plugins,
    )
    raw_plugins = finder.find_plugins(cfg, plugin_opts)
    plugins = finder.load_plugins(raw_plugins, plugin_opts)

    option_manager = manager.OptionManager(
        version=flake8.__version__,
        plugin_versions=plugins.versions_str(),
        parents=[prelim_parser],
        formatter_names=list(plugins.reporters),
    )
    options.register_default_options(option_manager)
    option_manager.register_plugins(plugins)

    opts = aggregator.aggregate_options(option_manager, cfg, cfg_dir, rest)

    for loaded in plugins.all_plugins():
        parse_options = getattr(loaded.obj, "parse_options", None)
        if parse_options is None:
            continue

        # XXX: ideally we wouldn't have two forms of parse_options
        try:
            parse_options(
                option_manager,
                opts,
                opts.filenames,
            )
        except TypeError:
            parse_options(opts)

    return plugins, opts
