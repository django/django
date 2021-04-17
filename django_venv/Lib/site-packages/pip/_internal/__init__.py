#!/usr/bin/env python
from __future__ import absolute_import

import locale
import logging
import os
import warnings

import sys

# 2016-06-17 barry@debian.org: urllib3 1.14 added optional support for socks,
# but if invoked (i.e. imported), it will issue a warning to stderr if socks
# isn't available.  requests unconditionally imports urllib3's socks contrib
# module, triggering this warning.  The warning breaks DEP-8 tests (because of
# the stderr output) and is just plain annoying in normal usage.  I don't want
# to add socks as yet another dependency for pip, nor do I want to allow-stderr
# in the DEP-8 tests, so just suppress the warning.  pdb tells me this has to
# be done before the import of pip.vcs.
from pip._vendor.urllib3.exceptions import DependencyWarning
warnings.filterwarnings("ignore", category=DependencyWarning)  # noqa

# We want to inject the use of SecureTransport as early as possible so that any
# references or sessions or what have you are ensured to have it, however we
# only want to do this in the case that we're running on macOS and the linked
# OpenSSL is too old to handle TLSv1.2
try:
    import ssl
except ImportError:
    pass
else:
    # Checks for OpenSSL 1.0.1 on MacOS
    if sys.platform == "darwin" and ssl.OPENSSL_VERSION_NUMBER < 0x1000100f:
        try:
            from pip._vendor.urllib3.contrib import securetransport
        except (ImportError, OSError):
            pass
        else:
            securetransport.inject_into_urllib3()

from pip._internal.cli.autocompletion import autocomplete
from pip._internal.cli.main_parser import parse_command
from pip._internal.commands import commands_dict
from pip._internal.exceptions import PipError
from pip._internal.utils import deprecation
from pip._vendor.urllib3.exceptions import InsecureRequestWarning

logger = logging.getLogger(__name__)

# Hide the InsecureRequestWarning from urllib3
warnings.filterwarnings("ignore", category=InsecureRequestWarning)


def main(args=None):
    if args is None:
        args = sys.argv[1:]

    # Configure our deprecation warnings to be sent through loggers
    deprecation.install_warning_logger()

    autocomplete()

    try:
        cmd_name, cmd_args = parse_command(args)
    except PipError as exc:
        sys.stderr.write("ERROR: %s" % exc)
        sys.stderr.write(os.linesep)
        sys.exit(1)

    # Needed for locale.getpreferredencoding(False) to work
    # in pip._internal.utils.encoding.auto_decode
    try:
        locale.setlocale(locale.LC_ALL, '')
    except locale.Error as e:
        # setlocale can apparently crash if locale are uninitialized
        logger.debug("Ignoring error %s when setting locale", e)
    command = commands_dict[cmd_name](isolated=("--isolated" in cmd_args))
    return command.main(cmd_args)
