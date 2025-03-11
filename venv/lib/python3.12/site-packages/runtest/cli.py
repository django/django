from optparse import OptionParser
import sys
import os
import inspect
from .version import __version__


def cli():
    frame = inspect.stack()[-1]
    module = inspect.getmodule(frame[0])
    caller_file = module.__file__
    caller_dir = os.path.dirname(os.path.realpath(caller_file))

    parser = OptionParser(
        description="runtest {0} - Numerically tolerant end-to-end test library for research software.".format(
            __version__
        )
    )

    parser.add_option(
        "--binary-dir",
        "-b",
        action="store",
        default=caller_dir,
        help="directory containing the binary/runscript [default: %default]",
    )
    parser.add_option(
        "--work-dir",
        "-w",
        action="store",
        default=caller_dir,
        help="working directory [default: %default]",
    )
    parser.add_option(
        "--launch-agent",
        "-l",
        action="store",
        default=None,
        help='prepend a launch agent command (e.g. "mpirun -np 8" or "valgrind --leak-check=yes") [default: %default]',
    )
    parser.add_option(
        "--verbose",
        "-v",
        action="store_true",
        default=False,
        help="give more verbose output upon test failure [default: %default]",
    )
    parser.add_option(
        "--skip-run",
        "-s",
        action="store_true",
        default=False,
        help="skip actual calculation(s) [default: %default]",
    )
    parser.add_option(
        "--no-verification",
        "-n",
        action="store_true",
        default=False,
        help="run calculation(s) but do not verify results [default: %default]",
    )

    (options, _args) = parser.parse_args(args=sys.argv[1:])

    return options
