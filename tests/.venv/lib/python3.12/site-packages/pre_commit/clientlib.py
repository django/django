from __future__ import annotations

import functools
import logging
import os.path
import re
import shlex
import sys
from collections.abc import Callable
from collections.abc import Sequence
from typing import Any
from typing import NamedTuple

import cfgv
from identify.identify import ALL_TAGS

import pre_commit.constants as C
from pre_commit.all_languages import language_names
from pre_commit.errors import FatalError
from pre_commit.yaml import yaml_load

logger = logging.getLogger('pre_commit')

check_string_regex = cfgv.check_and(cfgv.check_string, cfgv.check_regex)

HOOK_TYPES = (
    'commit-msg',
    'post-checkout',
    'post-commit',
    'post-merge',
    'post-rewrite',
    'pre-commit',
    'pre-merge-commit',
    'pre-push',
    'pre-rebase',
    'prepare-commit-msg',
)
# `manual` is not invoked by any installed git hook.  See #719
STAGES = (*HOOK_TYPES, 'manual')


def check_type_tag(tag: str) -> None:
    if tag not in ALL_TAGS:
        raise cfgv.ValidationError(
            f'Type tag {tag!r} is not recognized.  '
            f'Try upgrading identify and pre-commit?',
        )


def parse_version(s: str) -> tuple[int, ...]:
    """poor man's version comparison"""
    return tuple(int(p) for p in s.split('.'))


def check_min_version(version: str) -> None:
    if parse_version(version) > parse_version(C.VERSION):
        raise cfgv.ValidationError(
            f'pre-commit version {version} is required but version '
            f'{C.VERSION} is installed.  '
            f'Perhaps run `pip install --upgrade pre-commit`.',
        )


_STAGES = {
    'commit': 'pre-commit',
    'merge-commit': 'pre-merge-commit',
    'push': 'pre-push',
}


def transform_stage(stage: str) -> str:
    return _STAGES.get(stage, stage)


MINIMAL_MANIFEST_SCHEMA = cfgv.Array(
    cfgv.Map(
        'Hook', 'id',
        cfgv.Required('id', cfgv.check_string),
        cfgv.Optional('stages', cfgv.check_array(cfgv.check_string), []),
    ),
)


def warn_for_stages_on_repo_init(repo: str, directory: str) -> None:
    try:
        manifest = cfgv.load_from_filename(
            os.path.join(directory, C.MANIFEST_FILE),
            schema=MINIMAL_MANIFEST_SCHEMA,
            load_strategy=yaml_load,
            exc_tp=InvalidManifestError,
        )
    except InvalidManifestError:
        return  # they'll get a better error message when it actually loads!

    legacy_stages = {}  # sorted set
    for hook in manifest:
        for stage in hook.get('stages', ()):
            if stage in _STAGES:
                legacy_stages[stage] = True

    if legacy_stages:
        logger.warning(
            f'repo `{repo}` uses deprecated stage names '
            f'({", ".join(legacy_stages)}) which will be removed in a '
            f'future version.  '
            f'Hint: often `pre-commit autoupdate --repo {shlex.quote(repo)}` '
            f'will fix this.  '
            f'if it does not -- consider reporting an issue to that repo.',
        )


class StagesMigrationNoDefault(NamedTuple):
    key: str
    default: Sequence[str]

    def check(self, dct: dict[str, Any]) -> None:
        if self.key not in dct:
            return

        with cfgv.validate_context(f'At key: {self.key}'):
            val = dct[self.key]
            cfgv.check_array(cfgv.check_any)(val)

            val = [transform_stage(v) for v in val]
            cfgv.check_array(cfgv.check_one_of(STAGES))(val)

    def apply_default(self, dct: dict[str, Any]) -> None:
        if self.key not in dct:
            return
        dct[self.key] = [transform_stage(v) for v in dct[self.key]]

    def remove_default(self, dct: dict[str, Any]) -> None:
        raise NotImplementedError


class StagesMigration(StagesMigrationNoDefault):
    def apply_default(self, dct: dict[str, Any]) -> None:
        dct.setdefault(self.key, self.default)
        super().apply_default(dct)


class DeprecatedStagesWarning(NamedTuple):
    key: str

    def check(self, dct: dict[str, Any]) -> None:
        if self.key not in dct:
            return

        val = dct[self.key]
        cfgv.check_array(cfgv.check_any)(val)

        legacy_stages = [stage for stage in val if stage in _STAGES]
        if legacy_stages:
            logger.warning(
                f'hook id `{dct["id"]}` uses deprecated stage names '
                f'({", ".join(legacy_stages)}) which will be removed in a '
                f'future version.  '
                f'run: `pre-commit migrate-config` to automatically fix this.',
            )

    def apply_default(self, dct: dict[str, Any]) -> None:
        pass

    def remove_default(self, dct: dict[str, Any]) -> None:
        raise NotImplementedError


class DeprecatedDefaultStagesWarning(NamedTuple):
    key: str

    def check(self, dct: dict[str, Any]) -> None:
        if self.key not in dct:
            return

        val = dct[self.key]
        cfgv.check_array(cfgv.check_any)(val)

        legacy_stages = [stage for stage in val if stage in _STAGES]
        if legacy_stages:
            logger.warning(
                f'top-level `default_stages` uses deprecated stage names '
                f'({", ".join(legacy_stages)}) which will be removed in a '
                f'future version.  '
                f'run: `pre-commit migrate-config` to automatically fix this.',
            )

    def apply_default(self, dct: dict[str, Any]) -> None:
        pass

    def remove_default(self, dct: dict[str, Any]) -> None:
        raise NotImplementedError


def _translate_language(name: str) -> str:
    return {
        'system': 'unsupported',
        'script': 'unsupported_script',
    }.get(name, name)


class LanguageMigration(NamedTuple):  # remove
    key: str
    check_fn: Callable[[object], None]

    def check(self, dct: dict[str, Any]) -> None:
        if self.key not in dct:
            return

        with cfgv.validate_context(f'At key: {self.key}'):
            self.check_fn(_translate_language(dct[self.key]))

    def apply_default(self, dct: dict[str, Any]) -> None:
        if self.key not in dct:
            return

        dct[self.key] = _translate_language(dct[self.key])

    def remove_default(self, dct: dict[str, Any]) -> None:
        raise NotImplementedError


class LanguageMigrationRequired(LanguageMigration):  # replace with Required
    def check(self, dct: dict[str, Any]) -> None:
        if self.key not in dct:
            raise cfgv.ValidationError(f'Missing required key: {self.key}')

        super().check(dct)


MANIFEST_HOOK_DICT = cfgv.Map(
    'Hook', 'id',

    # check first in case it uses some newer, incompatible feature
    cfgv.Optional(
        'minimum_pre_commit_version',
        cfgv.check_and(cfgv.check_string, check_min_version),
        '0',
    ),

    cfgv.Required('id', cfgv.check_string),
    cfgv.Required('name', cfgv.check_string),
    cfgv.Required('entry', cfgv.check_string),
    LanguageMigrationRequired('language', cfgv.check_one_of(language_names)),
    cfgv.Optional('alias', cfgv.check_string, ''),

    cfgv.Optional('files', check_string_regex, ''),
    cfgv.Optional('exclude', check_string_regex, '^$'),
    cfgv.Optional('types', cfgv.check_array(check_type_tag), ['file']),
    cfgv.Optional('types_or', cfgv.check_array(check_type_tag), []),
    cfgv.Optional('exclude_types', cfgv.check_array(check_type_tag), []),

    cfgv.Optional(
        'additional_dependencies', cfgv.check_array(cfgv.check_string), [],
    ),
    cfgv.Optional('args', cfgv.check_array(cfgv.check_string), []),
    cfgv.Optional('always_run', cfgv.check_bool, False),
    cfgv.Optional('fail_fast', cfgv.check_bool, False),
    cfgv.Optional('pass_filenames', cfgv.check_bool, True),
    cfgv.Optional('description', cfgv.check_string, ''),
    cfgv.Optional('language_version', cfgv.check_string, C.DEFAULT),
    cfgv.Optional('log_file', cfgv.check_string, ''),
    cfgv.Optional('require_serial', cfgv.check_bool, False),
    StagesMigration('stages', []),
    cfgv.Optional('verbose', cfgv.check_bool, False),
)
MANIFEST_SCHEMA = cfgv.Array(MANIFEST_HOOK_DICT)


class InvalidManifestError(FatalError):
    pass


def _load_manifest_forward_compat(contents: str) -> object:
    obj = yaml_load(contents)
    if isinstance(obj, dict):
        check_min_version('5')
        raise AssertionError('unreachable')
    else:
        return obj


load_manifest = functools.partial(
    cfgv.load_from_filename,
    schema=MANIFEST_SCHEMA,
    load_strategy=_load_manifest_forward_compat,
    exc_tp=InvalidManifestError,
)


LOCAL = 'local'
META = 'meta'


class WarnMutableRev(cfgv.Conditional):
    def check(self, dct: dict[str, Any]) -> None:
        super().check(dct)

        if self.key in dct:
            rev = dct[self.key]

            if '.' not in rev and not re.match(r'^[a-fA-F0-9]+$', rev):
                logger.warning(
                    f'The {self.key!r} field of repo {dct["repo"]!r} '
                    f'appears to be a mutable reference '
                    f'(moving tag / branch).  Mutable references are never '
                    f'updated after first install and are not supported.  '
                    f'See https://pre-commit.com/#using-the-latest-version-for-a-repository '  # noqa: E501
                    f'for more details.  '
                    f'Hint: `pre-commit autoupdate` often fixes this.',
                )


class OptionalSensibleRegexAtHook(cfgv.OptionalNoDefault):
    def check(self, dct: dict[str, Any]) -> None:
        super().check(dct)

        if '/*' in dct.get(self.key, ''):
            logger.warning(
                f'The {self.key!r} field in hook {dct.get("id")!r} is a '
                f"regex, not a glob -- matching '/*' probably isn't what you "
                f'want here',
            )
        for fwd_slash_re in (r'[\\/]', r'[\/]', r'[/\\]'):
            if fwd_slash_re in dct.get(self.key, ''):
                logger.warning(
                    fr'pre-commit normalizes slashes in the {self.key!r} '
                    fr'field in hook {dct.get("id")!r} to forward slashes, '
                    fr'so you can use / instead of {fwd_slash_re}',
                )


class OptionalSensibleRegexAtTop(cfgv.OptionalNoDefault):
    def check(self, dct: dict[str, Any]) -> None:
        super().check(dct)

        if '/*' in dct.get(self.key, ''):
            logger.warning(
                f'The top-level {self.key!r} field is a regex, not a glob -- '
                f"matching '/*' probably isn't what you want here",
            )
        for fwd_slash_re in (r'[\\/]', r'[\/]', r'[/\\]'):
            if fwd_slash_re in dct.get(self.key, ''):
                logger.warning(
                    fr'pre-commit normalizes the slashes in the top-level '
                    fr'{self.key!r} field to forward slashes, so you '
                    fr'can use / instead of {fwd_slash_re}',
                )


def _entry(modname: str) -> str:
    """the hook `entry` is passed through `shlex.split()` by the command
    runner, so to prevent issues with spaces and backslashes (on Windows)
    it must be quoted here.
    """
    return f'{shlex.quote(sys.executable)} -m pre_commit.meta_hooks.{modname}'


def warn_unknown_keys_root(
        extra: Sequence[str],
        orig_keys: Sequence[str],
        dct: dict[str, str],
) -> None:
    logger.warning(f'Unexpected key(s) present at root: {", ".join(extra)}')


def warn_unknown_keys_repo(
        extra: Sequence[str],
        orig_keys: Sequence[str],
        dct: dict[str, str],
) -> None:
    logger.warning(
        f'Unexpected key(s) present on {dct["repo"]}: {", ".join(extra)}',
    )


_meta = (
    (
        'check-hooks-apply', (
            ('name', 'Check hooks apply to the repository'),
            ('files', f'^{re.escape(C.CONFIG_FILE)}$'),
            ('entry', _entry('check_hooks_apply')),
        ),
    ),
    (
        'check-useless-excludes', (
            ('name', 'Check for useless excludes'),
            ('files', f'^{re.escape(C.CONFIG_FILE)}$'),
            ('entry', _entry('check_useless_excludes')),
        ),
    ),
    (
        'identity', (
            ('name', 'identity'),
            ('verbose', True),
            ('entry', _entry('identity')),
        ),
    ),
)


class NotAllowed(cfgv.OptionalNoDefault):
    def check(self, dct: dict[str, Any]) -> None:
        if self.key in dct:
            raise cfgv.ValidationError(f'{self.key!r} cannot be overridden')


_COMMON_HOOK_WARNINGS = (
    OptionalSensibleRegexAtHook('files', cfgv.check_string),
    OptionalSensibleRegexAtHook('exclude', cfgv.check_string),
    DeprecatedStagesWarning('stages'),
)

META_HOOK_DICT = cfgv.Map(
    'Hook', 'id',
    cfgv.Required('id', cfgv.check_string),
    cfgv.Required('id', cfgv.check_one_of(tuple(k for k, _ in _meta))),
    # language must be `unsupported`
    cfgv.Optional(
        'language', cfgv.check_one_of({'unsupported'}), 'unsupported',
    ),
    # entry cannot be overridden
    NotAllowed('entry', cfgv.check_any),
    *(
        # default to the hook definition for the meta hooks
        cfgv.ConditionalOptional(key, cfgv.check_any, value, 'id', hook_id)
        for hook_id, values in _meta
        for key, value in values
    ),
    *(
        # default to the "manifest" parsing
        cfgv.OptionalNoDefault(item.key, item.check_fn)
        # these will always be defaulted above
        if item.key in {'name', 'language', 'entry'} else
        item
        for item in MANIFEST_HOOK_DICT.items
    ),
    *_COMMON_HOOK_WARNINGS,
)
CONFIG_HOOK_DICT = cfgv.Map(
    'Hook', 'id',

    cfgv.Required('id', cfgv.check_string),

    # All keys in manifest hook dict are valid in a config hook dict, but
    # are optional.
    # No defaults are provided here as the config is merged on top of the
    # manifest.
    *(
        cfgv.OptionalNoDefault(item.key, item.check_fn)
        for item in MANIFEST_HOOK_DICT.items
        if item.key != 'id'
        if item.key != 'stages'
        if item.key != 'language'  # remove
    ),
    StagesMigrationNoDefault('stages', []),
    LanguageMigration('language', cfgv.check_one_of(language_names)),  # remove
    *_COMMON_HOOK_WARNINGS,
)
LOCAL_HOOK_DICT = cfgv.Map(
    'Hook', 'id',

    *MANIFEST_HOOK_DICT.items,
    *_COMMON_HOOK_WARNINGS,
)
CONFIG_REPO_DICT = cfgv.Map(
    'Repository', 'repo',

    cfgv.Required('repo', cfgv.check_string),

    cfgv.ConditionalRecurse(
        'hooks', cfgv.Array(CONFIG_HOOK_DICT),
        'repo', cfgv.NotIn(LOCAL, META),
    ),
    cfgv.ConditionalRecurse(
        'hooks', cfgv.Array(LOCAL_HOOK_DICT),
        'repo', LOCAL,
    ),
    cfgv.ConditionalRecurse(
        'hooks', cfgv.Array(META_HOOK_DICT),
        'repo', META,
    ),

    WarnMutableRev(
        'rev', cfgv.check_string,
        condition_key='repo',
        condition_value=cfgv.NotIn(LOCAL, META),
        ensure_absent=True,
    ),
    cfgv.WarnAdditionalKeys(('repo', 'rev', 'hooks'), warn_unknown_keys_repo),
)
DEFAULT_LANGUAGE_VERSION = cfgv.Map(
    'DefaultLanguageVersion', None,
    cfgv.NoAdditionalKeys(language_names),
    *(cfgv.Optional(x, cfgv.check_string, C.DEFAULT) for x in language_names),
)
CONFIG_SCHEMA = cfgv.Map(
    'Config', None,

    # check first in case it uses some newer, incompatible feature
    cfgv.Optional(
        'minimum_pre_commit_version',
        cfgv.check_and(cfgv.check_string, check_min_version),
        '0',
    ),

    cfgv.RequiredRecurse('repos', cfgv.Array(CONFIG_REPO_DICT)),
    cfgv.Optional(
        'default_install_hook_types',
        cfgv.check_array(cfgv.check_one_of(HOOK_TYPES)),
        ['pre-commit'],
    ),
    cfgv.OptionalRecurse(
        'default_language_version', DEFAULT_LANGUAGE_VERSION, {},
    ),
    StagesMigration('default_stages', STAGES),
    DeprecatedDefaultStagesWarning('default_stages'),
    cfgv.Optional('files', check_string_regex, ''),
    cfgv.Optional('exclude', check_string_regex, '^$'),
    cfgv.Optional('fail_fast', cfgv.check_bool, False),
    cfgv.WarnAdditionalKeys(
        (
            'repos',
            'default_install_hook_types',
            'default_language_version',
            'default_stages',
            'files',
            'exclude',
            'fail_fast',
            'minimum_pre_commit_version',
            'ci',
        ),
        warn_unknown_keys_root,
    ),
    OptionalSensibleRegexAtTop('files', cfgv.check_string),
    OptionalSensibleRegexAtTop('exclude', cfgv.check_string),

    # do not warn about configuration for pre-commit.ci
    cfgv.OptionalNoDefault('ci', cfgv.check_type(dict)),
)


class InvalidConfigError(FatalError):
    pass


load_config = functools.partial(
    cfgv.load_from_filename,
    schema=CONFIG_SCHEMA,
    load_strategy=yaml_load,
    exc_tp=InvalidConfigError,
)
