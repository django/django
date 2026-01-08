from __future__ import annotations

import argparse
import subprocess
from collections.abc import Sequence

from pre_commit.parse_shebang import normalize_cmd


def add_parsers(parser: argparse.ArgumentParser) -> None:
    subparsers = parser.add_subparsers(dest='tool')

    cd_parser = subparsers.add_parser(
        'cd', help='cd to a subdir and run the command',
    )
    cd_parser.add_argument('subdir')
    cd_parser.add_argument('cmd', nargs=argparse.REMAINDER)

    ignore_exit_code_parser = subparsers.add_parser(
        'ignore-exit-code', help='run the command but ignore the exit code',
    )
    ignore_exit_code_parser.add_argument('cmd', nargs=argparse.REMAINDER)

    n1_parser = subparsers.add_parser(
        'n1', help='run the command once per filename',
    )
    n1_parser.add_argument('cmd', nargs=argparse.REMAINDER)


def _cmd_filenames(cmd: tuple[str, ...]) -> tuple[
    tuple[str, ...],
    tuple[str, ...],
]:
    for idx, val in enumerate(reversed(cmd)):
        if val == '--':
            split = len(cmd) - idx
            break
    else:
        raise SystemExit('hazmat entry must end with `--`')

    return cmd[:split - 1], cmd[split:]


def cd(subdir: str, cmd: tuple[str, ...]) -> int:
    cmd, filenames = _cmd_filenames(cmd)

    prefix = f'{subdir}/'
    new_filenames = []
    for filename in filenames:
        if not filename.startswith(prefix):
            raise SystemExit(f'unexpected file without {prefix=}: {filename}')
        else:
            new_filenames.append(filename.removeprefix(prefix))

    cmd = normalize_cmd(cmd)
    return subprocess.call((*cmd, *new_filenames), cwd=subdir)


def ignore_exit_code(cmd: tuple[str, ...]) -> int:
    cmd = normalize_cmd(cmd)
    subprocess.call(cmd)
    return 0


def n1(cmd: tuple[str, ...]) -> int:
    cmd, filenames = _cmd_filenames(cmd)
    cmd = normalize_cmd(cmd)
    ret = 0
    for filename in filenames:
        ret |= subprocess.call((*cmd, filename))
    return ret


def impl(args: argparse.Namespace) -> int:
    args.cmd = tuple(args.cmd)
    if args.tool == 'cd':
        return cd(args.subdir, args.cmd)
    elif args.tool == 'ignore-exit-code':
        return ignore_exit_code(args.cmd)
    elif args.tool == 'n1':
        return n1(args.cmd)
    else:
        raise NotImplementedError(f'unexpected tool: {args.tool}')


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    add_parsers(parser)
    args = parser.parse_args(argv)

    return impl(args)


if __name__ == '__main__':
    raise SystemExit(main())
