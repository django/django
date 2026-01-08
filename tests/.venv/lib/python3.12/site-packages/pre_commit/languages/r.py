from __future__ import annotations

import contextlib
import os
import shlex
import shutil
import tempfile
import textwrap
from collections.abc import Generator
from collections.abc import Sequence

from pre_commit import lang_base
from pre_commit.envcontext import envcontext
from pre_commit.envcontext import PatchesT
from pre_commit.envcontext import UNSET
from pre_commit.prefix import Prefix
from pre_commit.util import cmd_output
from pre_commit.util import win_exe

ENVIRONMENT_DIR = 'renv'
get_default_version = lang_base.basic_get_default_version

_RENV_ACTIVATED_OPTS = (
    '--no-save', '--no-restore', '--no-site-file', '--no-environ',
)


def _execute_r(
        code: str, *,
        prefix: Prefix, version: str, args: Sequence[str] = (), cwd: str,
        cli_opts: Sequence[str],
) -> str:
    with in_env(prefix, version), _r_code_in_tempfile(code) as f:
        _, out, _ = cmd_output(
            _rscript_exec(), *cli_opts, f, *args, cwd=cwd,
        )
    return out.rstrip('\n')


def _execute_r_in_renv(
        code: str, *,
        prefix: Prefix, version: str, args: Sequence[str] = (), cwd: str,
) -> str:
    return _execute_r(
        code=code, prefix=prefix, version=version, args=args, cwd=cwd,
        cli_opts=_RENV_ACTIVATED_OPTS,
    )


def _execute_vanilla_r(
        code: str, *,
        prefix: Prefix, version: str, args: Sequence[str] = (), cwd: str,
) -> str:
    return _execute_r(
        code=code, prefix=prefix, version=version, args=args, cwd=cwd,
        cli_opts=('--vanilla',),
    )


def _read_installed_version(envdir: str, prefix: Prefix, version: str) -> str:
    return _execute_r_in_renv(
        'cat(renv::settings$r.version())',
        prefix=prefix, version=version,
        cwd=envdir,
    )


def _read_executable_version(envdir: str, prefix: Prefix, version: str) -> str:
    return _execute_r_in_renv(
        'cat(as.character(getRversion()))',
        prefix=prefix, version=version,
        cwd=envdir,
    )


def _write_current_r_version(
        envdir: str, prefix: Prefix, version: str,
) -> None:
    _execute_r_in_renv(
        'renv::settings$r.version(as.character(getRversion()))',
        prefix=prefix, version=version,
        cwd=envdir,
    )


def health_check(prefix: Prefix, version: str) -> str | None:
    envdir = lang_base.environment_dir(prefix, ENVIRONMENT_DIR, version)

    r_version_installation = _read_installed_version(
        envdir=envdir, prefix=prefix, version=version,
    )
    r_version_current_executable = _read_executable_version(
        envdir=envdir, prefix=prefix, version=version,
    )
    if r_version_installation in {'NULL', ''}:
        return (
            f'Hooks were installed with an unknown R version. R version for '
            f'hook repo now set to {r_version_current_executable}'
        )
    elif r_version_installation != r_version_current_executable:
        return (
            f'Hooks were installed for R version {r_version_installation}, '
            f'but current R executable has version '
            f'{r_version_current_executable}'
        )

    return None


@contextlib.contextmanager
def _r_code_in_tempfile(code: str) -> Generator[str]:
    """
    To avoid quoting and escaping issues, avoid `Rscript [options] -e {expr}`
    but use `Rscript [options] path/to/file_with_expr.R`
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        fname = os.path.join(tmpdir, 'script.R')
        with open(fname, 'w') as f:
            f.write(_inline_r_setup(textwrap.dedent(code)))
        yield fname


def get_env_patch(venv: str) -> PatchesT:
    return (
        ('R_PROFILE_USER', os.path.join(venv, 'activate.R')),
        ('RENV_PROJECT', UNSET),
    )


@contextlib.contextmanager
def in_env(prefix: Prefix, version: str) -> Generator[None]:
    envdir = lang_base.environment_dir(prefix, ENVIRONMENT_DIR, version)
    with envcontext(get_env_patch(envdir)):
        yield


def _prefix_if_file_entry(
        entry: list[str],
        prefix: Prefix,
        *,
        is_local: bool,
) -> Sequence[str]:
    if entry[1] == '-e' or is_local:
        return entry[1:]
    else:
        return (prefix.path(entry[1]),)


def _rscript_exec() -> str:
    r_home = os.environ.get('R_HOME')
    if r_home is None:
        return 'Rscript'
    else:
        return os.path.join(r_home, 'bin', win_exe('Rscript'))


def _entry_validate(entry: list[str]) -> None:
    """
    Allowed entries:
    # Rscript -e expr
    # Rscript path/to/file
    """
    if entry[0] != 'Rscript':
        raise ValueError('entry must start with `Rscript`.')

    if entry[1] == '-e':
        if len(entry) > 3:
            raise ValueError('You can supply at most one expression.')
    elif len(entry) > 2:
        raise ValueError(
            'The only valid syntax is `Rscript -e {expr}`'
            'or `Rscript path/to/hook/script`',
        )


def _cmd_from_hook(
        prefix: Prefix,
        entry: str,
        args: Sequence[str],
        *,
        is_local: bool,
) -> tuple[str, ...]:
    cmd = shlex.split(entry)
    _entry_validate(cmd)

    cmd_part = _prefix_if_file_entry(cmd, prefix, is_local=is_local)
    return (cmd[0], *_RENV_ACTIVATED_OPTS, *cmd_part, *args)


def install_environment(
        prefix: Prefix,
        version: str,
        additional_dependencies: Sequence[str],
) -> None:
    lang_base.assert_version_default('r', version)

    env_dir = lang_base.environment_dir(prefix, ENVIRONMENT_DIR, version)
    os.makedirs(env_dir, exist_ok=True)
    shutil.copy(prefix.path('renv.lock'), env_dir)
    shutil.copytree(prefix.path('renv'), os.path.join(env_dir, 'renv'))

    r_code_inst_environment = f"""\
        prefix_dir <- {prefix.prefix_dir!r}
        options(
            repos = c(CRAN = "https://cran.rstudio.com"),
            renv.consent = TRUE
        )
        source("renv/activate.R")
        renv::restore()
        activate_statement <- paste0(
          'suppressWarnings({{',
          'old <- setwd("', getwd(), '"); ',
          'source("renv/activate.R"); ',
          'setwd(old); ',
          'renv::load("', getwd(), '");}})'
        )
        writeLines(activate_statement, 'activate.R')
        is_package <- tryCatch(
          {{
              path_desc <- file.path(prefix_dir, 'DESCRIPTION')
              suppressWarnings(desc <- read.dcf(path_desc))
              "Package" %in% colnames(desc)
          }},
          error = function(...) FALSE
        )
        if (is_package) {{
            renv::install(prefix_dir)
        }}
        """
    _execute_vanilla_r(
        r_code_inst_environment,
        prefix=prefix, version=version, cwd=env_dir,
    )

    _write_current_r_version(envdir=env_dir, prefix=prefix, version=version)
    if additional_dependencies:
        r_code_inst_add = 'renv::install(commandArgs(trailingOnly = TRUE))'
        _execute_r_in_renv(
            code=r_code_inst_add, prefix=prefix, version=version,
            args=additional_dependencies,
            cwd=env_dir,
        )


def _inline_r_setup(code: str) -> str:
    """
    Some behaviour of R cannot be configured via env variables, but can
    only be configured via R options once R has started. These are set here.
    """
    with_option = [
        textwrap.dedent("""\
        options(
            install.packages.compile.from.source = "never",
            pkgType = "binary"
        )
        """),
        code,
    ]
    return '\n'.join(with_option)


def run_hook(
        prefix: Prefix,
        entry: str,
        args: Sequence[str],
        file_args: Sequence[str],
        *,
        is_local: bool,
        require_serial: bool,
        color: bool,
) -> tuple[int, bytes]:
    cmd = _cmd_from_hook(prefix, entry, args, is_local=is_local)
    return lang_base.run_xargs(
        cmd,
        file_args,
        require_serial=require_serial,
        color=color,
    )
