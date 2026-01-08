from __future__ import annotations

import errno
import logging
import os
import sys
from timeit import default_timer

LOGGER = logging.getLogger(__name__)


def run(args=None, options=None, env=None):
    env = os.environ if env is None else env
    start = default_timer()
    from virtualenv.run import cli_run  # noqa: PLC0415
    from virtualenv.util.error import ProcessCallFailedError  # noqa: PLC0415

    if args is None:
        args = sys.argv[1:]
    try:
        session = cli_run(args, options, env)
        LOGGER.warning(LogSession(session, start))
    except ProcessCallFailedError as exception:
        print(f"subprocess call failed for {exception.cmd} with code {exception.code}")  # noqa: T201
        print(exception.out, file=sys.stdout, end="")  # noqa: T201
        print(exception.err, file=sys.stderr, end="")  # noqa: T201
        raise SystemExit(exception.code)  # noqa: B904
    except OSError as exception:
        if exception.errno == errno.EMFILE:
            print(  # noqa: T201
                "OSError: [Errno 24] Too many open files. You may need to increase your OS open files limit.\n"
                "  On macOS/Linux, try 'ulimit -n 2048'.\n"
                "  For Windows, this is not a common issue, but you can try to close some applications.",
                file=sys.stderr,
            )
        raise


class LogSession:
    def __init__(self, session, start) -> None:
        self.session = session
        self.start = start

    def __str__(self) -> str:
        spec = self.session.creator.interpreter.spec
        elapsed = (default_timer() - self.start) * 1000
        lines = [
            f"created virtual environment {spec} in {elapsed:.0f}ms",
            f"  creator {self.session.creator!s}",
        ]
        if self.session.seeder.enabled:
            lines.append(f"  seeder {self.session.seeder!s}")
            path = self.session.creator.purelib.iterdir()
            packages = sorted("==".join(i.stem.split("-")) for i in path if i.suffix == ".dist-info")
            lines.append(f"    added seed packages: {', '.join(packages)}")

        if self.session.activators:
            lines.append(f"  activators {','.join(i.__class__.__name__ for i in self.session.activators)}")
        return "\n".join(lines)


def run_with_catch(args=None, env=None):
    from virtualenv.config.cli.parser import VirtualEnvOptions  # noqa: PLC0415

    env = os.environ if env is None else env
    options = VirtualEnvOptions()
    try:
        run(args, options, env)
    except (KeyboardInterrupt, SystemExit, Exception) as exception:  # noqa: BLE001
        try:
            if getattr(options, "with_traceback", False):
                raise
            if not (isinstance(exception, SystemExit) and exception.code == 0):
                LOGGER.error("%s: %s", type(exception).__name__, exception)  # noqa: TRY400
            code = exception.code if isinstance(exception, SystemExit) else 1
            sys.exit(code)
        finally:
            for handler in LOGGER.handlers:  # force flush of log messages before the trace is printed
                handler.flush()


if __name__ == "__main__":  # pragma: no cov
    run_with_catch()  # pragma: no cov
