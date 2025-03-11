"""Aggregation function for CLI specified options and config file options.

This holds the logic that uses the collected and merged config files and
applies the user-specified command-line configuration on top of it.
"""
from __future__ import annotations

import argparse
import configparser
import logging
from typing import Sequence

from flake8.options import config
from flake8.options.manager import OptionManager

LOG = logging.getLogger(__name__)


def aggregate_options(
    manager: OptionManager,
    cfg: configparser.RawConfigParser,
    cfg_dir: str,
    argv: Sequence[str] | None,
) -> argparse.Namespace:
    """Aggregate and merge CLI and config file options."""
    # Get defaults from the option parser
    default_values = manager.parse_args([])

    # Get the parsed config
    parsed_config = config.parse_config(manager, cfg, cfg_dir)

    # store the plugin-set extended default ignore / select
    default_values.extended_default_ignore = manager.extended_default_ignore
    default_values.extended_default_select = manager.extended_default_select

    # Merge values parsed from config onto the default values returned
    for config_name, value in parsed_config.items():
        dest_name = config_name
        # If the config name is somehow different from the destination name,
        # fetch the destination name from our Option
        if not hasattr(default_values, config_name):
            dest_val = manager.config_options_dict[config_name].dest
            assert isinstance(dest_val, str)
            dest_name = dest_val

        LOG.debug(
            'Overriding default value of (%s) for "%s" with (%s)',
            getattr(default_values, dest_name, None),
            dest_name,
            value,
        )
        # Override the default values with the config values
        setattr(default_values, dest_name, value)

    # Finally parse the command-line options
    return manager.parse_args(argv, default_values)
