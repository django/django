# Copyright 2014-2021 The aiosmtpd Developers
# SPDX-License-Identifier: Apache-2.0

import logging
import os
import signal
import ssl
import sys
from argparse import ArgumentParser, Namespace
from contextlib import suppress
from functools import partial
from importlib import import_module
from pathlib import Path
from typing import Optional, Sequence, Tuple

from public import public

from aiosmtpd import __version__, _get_or_new_eventloop
from aiosmtpd.smtp import DATA_SIZE_DEFAULT, SMTP

try:
    import pwd
except ImportError:  # pragma: has-pwd
    pwd = None  # type: ignore[assignment]


DEFAULT_HOST = "localhost"
DEFAULT_PORT = 8025
DEFAULT_CLASS = "aiosmtpd.handlers.Debugging"

# Make the program name a little nicer, especially when `python3 -m aiosmtpd`
# is used.
PROGRAM = "aiosmtpd" if "__main__.py" in sys.argv[0] else sys.argv[0]


# Need to emit ArgumentParser by itself so autoprogramm extension can do its magic
def _parser() -> ArgumentParser:
    parser = ArgumentParser(
        prog=PROGRAM, description="An RFC 5321 SMTP server with extensions."
    )
    parser.add_argument(
        "-v", "--version", action="version", version="%(prog)s {}".format(__version__)
    )
    parser.add_argument(
        "-n",
        "--nosetuid",
        dest="setuid",
        default=True,
        action="store_false",
        help=(
            "This program generally tries to setuid ``nobody``, unless this "
            "flag is set.  The setuid call will fail if this program is not "
            "run as root (in which case, use this flag)."
        ),
    )
    parser.add_argument(
        "-c",
        "--class",
        dest="classpath",
        metavar="CLASSPATH",
        default=DEFAULT_CLASS,
        help=(
            f"Use the given class, as a Python dotted import path, as the "
            f"handler class for SMTP events.  This class can process "
            f"received messages and do other actions during the SMTP "
            f"dialog.  Uses ``{DEFAULT_CLASS}`` by default."
        ),
    )
    parser.add_argument(
        "-s",
        "--size",
        metavar="SIZE",
        type=int,
        help=(
            f"Restrict the total size of the incoming message to "
            f"``SIZE`` number of bytes via the RFC 1870 SIZE extension. "
            f"Defaults to {DATA_SIZE_DEFAULT:,} bytes."
        ),
    )
    parser.add_argument(
        "-u",
        "--smtputf8",
        default=False,
        action="store_true",
        help="""Enable the ``SMTPUTF8`` extension as defined in RFC 6531.""",
    )
    parser.add_argument(
        "-d",
        "--debug",
        default=0,
        action="count",
        help=(
            "Increase debugging output. Every ``-d`` increases debugging level by one."
        )
    )
    parser.add_argument(
        "-l",
        "--listen",
        metavar="[HOST][:PORT]",
        nargs="?",
        default=None,
        help=(
            "Optional host and port to listen on.  If the ``PORT`` part is not "
            "given, then port ``{port}`` is used.  If only ``:PORT`` is given, "
            "then ``{host}`` is used for the hostname.  If neither are given, "
            "``{host}:{port}`` is used.".format(host=DEFAULT_HOST, port=DEFAULT_PORT)
        ),
    )
    parser.add_argument(
        "--smtpscert",
        metavar="CERTFILE",
        type=Path,
        default=None,
        help=(
            "The certificate file for implementing **SMTPS**. If given, the parameter "
            "``--smtpskey`` must also be specified."
        ),
    )
    parser.add_argument(
        "--smtpskey",
        metavar="KEYFILE",
        type=Path,
        default=None,
        help=(
            "The key file for implementing **SMTPS**. If given, the parameter "
            "``--smtpscert`` must also be specified."
        ),
    )
    parser.add_argument(
        "--tlscert",
        metavar="CERTFILE",
        type=Path,
        default=None,
        help=(
            "The certificate file for implementing **STARTTLS**. If given, the "
            "parameter ``--tlskey`` must also be specified."
        ),
    )
    parser.add_argument(
        "--tlskey",
        metavar="KEYFILE",
        type=Path,
        default=None,
        help=(
            "The key file for implementing **STARTTLS**. If given, the parameter "
            "``--tlscert`` must also be specified."
        ),
    )
    parser.add_argument(
        "--no-requiretls",
        dest="requiretls",
        default=True,
        action="store_false",
        help=(
            "If specified, disables ``require_starttls`` of the SMTP class. "
            "(By default, ``require_starttls`` is True.) "
            "Has no effect if ``--tlscert`` and ``--tlskey`` are not specified."
        ),
    )
    parser.add_argument(
        "classargs",
        metavar="CLASSARGS",
        nargs="*",
        default=(),
        help="""Additional arguments passed to the handler CLASS.""",
    )
    return parser


def parseargs(args: Optional[Sequence[str]] = None) -> Tuple[ArgumentParser, Namespace]:
    parser = _parser()
    parsed = parser.parse_args(args)
    # Find the handler class.
    path, dot, name = parsed.classpath.rpartition(".")
    module = import_module(path)
    handler_class = getattr(module, name)
    if hasattr(handler_class, "from_cli"):
        parsed.handler = handler_class.from_cli(parser, *parsed.classargs)
    else:
        if len(parsed.classargs) > 0:
            parser.error(f"Handler class {path} takes no arguments")
        parsed.handler = handler_class()
    # Parse the host:port argument.
    if parsed.listen is None:
        parsed.host = DEFAULT_HOST
        parsed.port = DEFAULT_PORT
    else:
        host, colon, port = parsed.listen.rpartition(":")
        if len(colon) == 0:
            parsed.host = port
            parsed.port = DEFAULT_PORT
        else:
            parsed.host = DEFAULT_HOST if len(host) == 0 else host
            try:
                parsed.port = int(DEFAULT_PORT if len(port) == 0 else port)
            except ValueError:
                parser.error("Invalid port number: {}".format(port))

    if bool(parsed.smtpscert) ^ bool(parsed.smtpskey):
        parser.error("--smtpscert and --smtpskey must be specified together")
    if parsed.smtpscert and not parsed.smtpscert.exists():
        parser.error(f"Cert file {parsed.smtpscert} not found")
    if parsed.smtpskey and not parsed.smtpskey.exists():
        parser.error(f"Key file {parsed.smtpskey} not found")

    if bool(parsed.tlscert) ^ bool(parsed.tlskey):
        parser.error("--tlscert and --tlskey must be specified together")
    if parsed.tlscert and not parsed.tlscert.exists():
        parser.error(f"Cert file {parsed.tlscert} not found")
    if parsed.tlskey and not parsed.tlskey.exists():
        parser.error(f"Key file {parsed.tlskey} not found")

    return parser, parsed


@public
def main(args: Optional[Sequence[str]] = None) -> None:
    parser, ns = parseargs(args=args)

    if ns.setuid:  # pragma: on-win32
        if pwd is None:
            print(  # type: ignore[unreachable]
                'Cannot import module "pwd"; try running with -n option.',
                file=sys.stderr,
            )
            sys.exit(1)
        nobody = pwd.getpwnam("nobody").pw_uid
        try:
            os.setuid(nobody)
        except PermissionError:
            print(
                'Cannot setuid "nobody"; try running with -n option.', file=sys.stderr
            )
            sys.exit(1)

    if ns.tlscert and ns.tlskey:
        tls_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        tls_context.check_hostname = False
        tls_context.load_cert_chain(str(ns.tlscert), str(ns.tlskey))
    else:
        tls_context = None

    factory = partial(
        SMTP,
        ns.handler,
        data_size_limit=ns.size,
        enable_SMTPUTF8=ns.smtputf8,
        tls_context=tls_context,
        require_starttls=ns.requiretls,
    )

    logging.basicConfig(level=logging.ERROR)
    log = logging.getLogger("mail.log")
    loop = _get_or_new_eventloop()

    if ns.debug > 0:
        log.setLevel(logging.INFO)
    if ns.debug > 1:
        log.setLevel(logging.DEBUG)
    if ns.debug > 2:
        loop.set_debug(enabled=True)

    if ns.smtpscert and ns.smtpskey:
        smtps_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        smtps_context.check_hostname = False
        smtps_context.load_cert_chain(str(ns.smtpscert), str(ns.smtpskey))
    else:
        smtps_context = None

    log.debug("Attempting to start server on %s:%s", ns.host, ns.port)
    server = server_loop = None
    try:
        server = loop.create_server(
            factory, host=ns.host, port=ns.port, ssl=smtps_context
        )
        server_loop = loop.run_until_complete(server)
    except RuntimeError:  # pragma: nocover
        raise
    log.debug(f"server_loop = {server_loop}")
    log.info("Server is listening on %s:%s", ns.host, ns.port)

    # Signal handlers are only supported on *nix, so just ignore the failure
    # to set this on Windows.
    with suppress(NotImplementedError):
        loop.add_signal_handler(signal.SIGINT, loop.stop)

    log.debug("Starting asyncio loop")
    with suppress(KeyboardInterrupt):
        loop.run_forever()
    server_loop.close()
    log.debug("Completed asyncio loop")
    loop.run_until_complete(server_loop.wait_closed())
    loop.close()


if __name__ == "__main__":  # pragma: nocover
    main()
