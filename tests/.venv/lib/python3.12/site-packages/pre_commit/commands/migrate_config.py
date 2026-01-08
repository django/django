from __future__ import annotations

import functools
import itertools
import textwrap
from collections.abc import Callable

import cfgv
import yaml
from yaml.nodes import ScalarNode

from pre_commit.clientlib import InvalidConfigError
from pre_commit.yaml import yaml_compose
from pre_commit.yaml import yaml_load
from pre_commit.yaml_rewrite import MappingKey
from pre_commit.yaml_rewrite import MappingValue
from pre_commit.yaml_rewrite import match
from pre_commit.yaml_rewrite import SequenceItem


def _is_header_line(line: str) -> bool:
    return line.startswith(('#', '---')) or not line.strip()


def _migrate_map(contents: str) -> str:
    if isinstance(yaml_load(contents), list):
        # Find the first non-header line
        lines = contents.splitlines(True)
        i = 0
        # Only loop on non empty configuration file
        while i < len(lines) and _is_header_line(lines[i]):
            i += 1

        header = ''.join(lines[:i])
        rest = ''.join(lines[i:])

        # If they are using the "default" flow style of yaml, this operation
        # will yield a valid configuration
        try:
            trial_contents = f'{header}repos:\n{rest}'
            yaml_load(trial_contents)
            contents = trial_contents
        except yaml.YAMLError:
            contents = f'{header}repos:\n{textwrap.indent(rest, " " * 4)}'

    return contents


def _preserve_style(n: ScalarNode, *, s: str) -> str:
    style = n.style or ''
    return f'{style}{s}{style}'


def _fix_stage(n: ScalarNode) -> str:
    return _preserve_style(n, s=f'pre-{n.value}')


def _migrate_composed(contents: str) -> str:
    tree = yaml_compose(contents)
    rewrites: list[tuple[ScalarNode, Callable[[ScalarNode], str]]] = []

    # sha -> rev
    sha_to_rev_replace = functools.partial(_preserve_style, s='rev')
    sha_to_rev_matcher = (
        MappingValue('repos'),
        SequenceItem(),
        MappingKey('sha'),
    )
    for node in match(tree, sha_to_rev_matcher):
        rewrites.append((node, sha_to_rev_replace))

    # python_venv -> python
    language_matcher = (
        MappingValue('repos'),
        SequenceItem(),
        MappingValue('hooks'),
        SequenceItem(),
        MappingValue('language'),
    )
    python_venv_replace = functools.partial(_preserve_style, s='python')
    for node in match(tree, language_matcher):
        if node.value == 'python_venv':
            rewrites.append((node, python_venv_replace))

    # stages rewrites
    default_stages_matcher = (MappingValue('default_stages'), SequenceItem())
    default_stages_match = match(tree, default_stages_matcher)
    hook_stages_matcher = (
        MappingValue('repos'),
        SequenceItem(),
        MappingValue('hooks'),
        SequenceItem(),
        MappingValue('stages'),
        SequenceItem(),
    )
    hook_stages_match = match(tree, hook_stages_matcher)
    for node in itertools.chain(default_stages_match, hook_stages_match):
        if node.value in {'commit', 'push', 'merge-commit'}:
            rewrites.append((node, _fix_stage))

    rewrites.sort(reverse=True, key=lambda nf: nf[0].start_mark.index)

    src_parts = []
    end: int | None = None
    for node, func in rewrites:
        src_parts.append(contents[node.end_mark.index:end])
        src_parts.append(func(node))
        end = node.start_mark.index
    src_parts.append(contents[:end])
    src_parts.reverse()
    return ''.join(src_parts)


def migrate_config(config_file: str, quiet: bool = False) -> int:
    with open(config_file) as f:
        orig_contents = contents = f.read()

    with cfgv.reraise_as(InvalidConfigError):
        with cfgv.validate_context(f'File {config_file}'):
            try:
                yaml_load(orig_contents)
            except Exception as e:
                raise cfgv.ValidationError(str(e))

    contents = _migrate_map(contents)
    contents = _migrate_composed(contents)

    if contents != orig_contents:
        with open(config_file, 'w') as f:
            f.write(contents)

        print('Configuration has been migrated.')
    elif not quiet:
        print('Configuration is already migrated.')
    return 0
