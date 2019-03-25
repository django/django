"""
Wheel command-line utility.
"""

from __future__ import print_function

import argparse
import os
import sys


def require_pkgresources(name):
    try:
        import pkg_resources  # noqa: F401
    except ImportError:
        raise RuntimeError("'{0}' needs pkg_resources (part of setuptools).".format(name))


class WheelError(Exception):
    pass


def unpack_f(args):
    from .unpack import unpack
    unpack(args.wheelfile, args.dest)


def pack_f(args):
    from .pack import pack
    pack(args.directory, args.dest_dir, args.build_number)


def convert_f(args):
    from .convert import convert
    convert(args.files, args.dest_dir, args.verbose)


def version_f(args):
    from .. import __version__
    print("wheel %s" % __version__)


def parser():
    p = argparse.ArgumentParser()
    s = p.add_subparsers(help="commands")

    unpack_parser = s.add_parser('unpack', help='Unpack wheel')
    unpack_parser.add_argument('--dest', '-d', help='Destination directory',
                               default='.')
    unpack_parser.add_argument('wheelfile', help='Wheel file')
    unpack_parser.set_defaults(func=unpack_f)

    repack_parser = s.add_parser('pack', help='Repack wheel')
    repack_parser.add_argument('directory', help='Root directory of the unpacked wheel')
    repack_parser.add_argument('--dest-dir', '-d', default=os.path.curdir,
                               help="Directory to store the wheel (default %(default)s)")
    repack_parser.add_argument('--build-number', help="Build tag to use in the wheel name")
    repack_parser.set_defaults(func=pack_f)

    convert_parser = s.add_parser('convert', help='Convert egg or wininst to wheel')
    convert_parser.add_argument('files', nargs='*', help='Files to convert')
    convert_parser.add_argument('--dest-dir', '-d', default=os.path.curdir,
                                help="Directory to store wheels (default %(default)s)")
    convert_parser.add_argument('--verbose', '-v', action='store_true')
    convert_parser.set_defaults(func=convert_f)

    version_parser = s.add_parser('version', help='Print version and exit')
    version_parser.set_defaults(func=version_f)

    help_parser = s.add_parser('help', help='Show this help')
    help_parser.set_defaults(func=lambda args: p.print_help())

    return p


def main():
    p = parser()
    args = p.parse_args()
    if not hasattr(args, 'func'):
        p.print_help()
    else:
        try:
            args.func(args)
            return 0
        except WheelError as e:
            print(e, file=sys.stderr)

    return 1
