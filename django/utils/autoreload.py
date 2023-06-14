import itertools
import logging
import os
import signal
import subprocess
import sys
import threading
import time
import traceback
import weakref
import fnmatch
from collections import defaultdict
from functools import lru_cache, wraps
from pathlib import Path
from types import ModuleType
from zipimport import zipimporter
from typing import Callable, Generator, List, Set
from django.utils.autoreload import BaseReloader, common_roots, sys_path_directories

import django
from django.apps import apps
from django.core.signals import request_finished
from django.dispatch import Signal
from django.utils.functional import cached_property
from django.utils.version import get_version_tuple

autoreload_started = Signal()
file_changed = Signal()

DJANGO_AUTORELOAD_ENV = "RUN_MAIN"

logger = logging.getLogger("django.utils.autoreload")

# If an error is raised while importing a file, it's not placed in sys.modules.
# This means that any future modifications aren't caught. Keep a list of these
# file paths to allow watching them in the future.
_error_files = []
_exception = None

try:
    import termios
except ImportError:
    termios = None


try:
    import pywatchman
except ImportError:
    pywatchman = None


try:
    import watchfiles
except ImportError:
    watchfiles = None


def is_django_module(module):
    """Return True if the given module is nested under Django."""
    return module.__name__.startswith("django.")


def is_django_path(path):
    """Return True if the given file path is nested under Django."""
    return Path(django.__file__).parent in Path(path).parents


def check_errors(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        global _exception
        try:
            fn(*args, **kwargs)
        except Exception:
            _exception = sys.exc_info()

            et, ev, tb = _exception

            if getattr(ev, "filename", None) is None:
                # get the filename from the last item in the stack
                filename = traceback.extract_tb(tb)[-1][0]
            else:
                filename = ev.filename

            if filename not in _error_files:
                _error_files.append(filename)

            raise

    return wrapper


def raise_last_exception():
    global _exception
    if _exception is not None:
        raise _exception[1]


def ensure_echo_on():
    """
    Ensure that echo mode is enabled. Some tools such as PDB disable
    it which causes usability issues after reload.
    """
    if not termios or not sys.stdin.isatty():
        return
    attr_list = termios.tcgetattr(sys.stdin)
    if not attr_list[3] & termios.ECHO:
        attr_list[3] |= termios.ECHO
        if hasattr(signal, "SIGTTOU"):
            old_handler = signal.signal(signal.SIGTTOU, signal.SIG_IGN)
        else:
            old_handler = None
        termios.tcsetattr(sys.stdin, termios.TCSANOW, attr_list)
        if old_handler is not None:
            signal.signal(signal.SIGTTOU, old_handler)


def iter_all_python_module_files():
    # This is a hot path during reloading. Create a stable sorted list of
    # modules based on the module name and pass it to iter_modules_and_files().
    # This ensures cached results are returned in the usual case that modules
    # aren't loaded on the fly.
    keys = sorted(sys.modules)
    modules = tuple(
        m
        for m in map(sys.modules.__getitem__, keys)
        if not isinstance(m, weakref.ProxyTypes)
    )
    return iter_modules_and_files(modules, frozenset(_error_files))


@lru_cache(maxsize=1)
def iter_modules_and_files(modules, extra_files):
    """Iterate through all modules needed to be watched."""
    sys_file_paths = []
    for module in modules:
        # During debugging (with PyDev) the 'typing.io' and 'typing.re' objects
        # are added to sys.modules, however they are types not modules and so
        # cause issues here.
        if not isinstance(module, ModuleType):
            continue
        if module.__name__ in ("__main__", "__mp_main__"):
            # __main__ (usually manage.py) doesn't always have a __spec__ set.
            # Handle this by falling back to using __file__, resolved below.
            # See https://docs.python.org/reference/import.html#main-spec
            # __file__ may not exists, e.g. when running ipdb debugger.
            if hasattr(module, "__file__"):
                sys_file_paths.append(module.__file__)
            continue
        if getattr(module, "__spec__", None) is None:
            continue
        spec = module.__spec__
        # Modules could be loaded from places without a concrete location. If
        # this is the case, skip them.
        if spec.has_location:
            origin = (
                spec.loader.archive
                if isinstance(spec.loader, zipimporter)
                else spec.origin
            )
            sys_file_paths.append(origin)

    results = set()
    for filename in itertools.chain(sys_file_paths, extra_files):
        if not filename:
            continue
        path = Path(filename)
        try:
            if not path.exists():
                # The module could have been removed, don't fail loudly if this
                # is the case.
                continue
        except ValueError as e:
            # Network filesystems may return null bytes in file paths.
            logger.debug('"%s" raised when resolving path: "%s"', e, path)
            continue
        resolved_path = path.resolve().absolute()
        results.add(resolved_path)
    return frozenset(results)


@lru_cache(maxsize=1)
def common_roots(paths):
    """
    Return a tuple of common roots that are shared between the given paths.
    File system watchers operate on directories and aren't cheap to create.
    Try to find the minimum set of directories to watch that encompass all of
    the files that need to be watched.
    """
    # Inspired from Werkzeug:
    # https://github.com/pallets/werkzeug/blob/7477be2853df70a022d9613e765581b9411c3c39/werkzeug/_reloader.py
    # Create a sorted list of the path components, longest first.
    path_parts = sorted([x.parts for x in paths], key=len, reverse=True)
    tree = {}
    for chunks in path_parts:
        node = tree
        # Add each part of the path to the tree.
        for chunk in chunks:
            node = node.setdefault(chunk, {})
        # Clear the last leaf in the tree.
        node.clear()

    # Turn the tree into a list of Path instances.
    def _walk(node, path):
        for prefix, child in node.items():
            yield from _walk(child, path + (prefix,))
        if not node:
            yield Path(*path)

    return tuple(_walk(tree, ()))


def sys_path_directories():
    """
    Yield absolute directories from sys.path, ignoring entries that don't
    exist.
    """
    for path in sys.path:
        path = Path(path)
        if not path.exists():
            continue
        resolved_path = path.resolve().absolute()
        # If the path is a file (like a zip file), watch the parent directory.
        if resolved_path.is_file():
            yield resolved_path.parent
        else:
            yield resolved_path


def get_child_arguments():
    """
    Return the executable. This contains a workaround for Windows if the
    executable is reported to not have the .exe extension which can cause bugs
    on reloading.
    """
    import __main__

    py_script = Path(sys.argv[0])

    args = [sys.executable] + ["-W%s" % o for o in sys.warnoptions]
    if sys.implementation.name == "cpython":
        args.extend(
            f"-X{key}" if value is True else f"-X{key}={value}"
            for key, value in sys._xoptions.items()
        )
    # __spec__ is set when the server was started with the `-m` option,
    # see https://docs.python.org/3/reference/import.html#main-spec
    # __spec__ may not exist, e.g. when running in a Conda env.
    if getattr(__main__, "__spec__", None) is not None:
        spec = __main__.__spec__
        if (spec.name == "__main__" or spec.name.endswith(".__main__")) and spec.parent:
            name = spec.parent
        else:
            name = spec.name
        args += ["-m", name]
        args += sys.argv[1:]
    elif not py_script.exists():
        # sys.argv[0] may not exist for several reasons on Windows.
        # It may exist with a .exe extension or have a -script.py suffix.
        exe_entrypoint = py_script.with_suffix(".exe")
        if exe_entrypoint.exists():
            # Should be executed directly, ignoring sys.executable.
            return [exe_entrypoint, *sys.argv[1:]]
        script_entrypoint = py_script.with_name("%s-script.py" % py_script.name)
        if script_entrypoint.exists():
            # Should be executed as usual.
            return [*args, script_entrypoint, *sys.argv[1:]]
        raise RuntimeError("Script %s does not exist." % py_script)
    else:
        args += sys.argv
    return args


def trigger_reload(filename):
    logger.info("%s changed, reloading.", filename)
    sys.exit(3)


def restart_with_reloader():
    new_environ = {**os.environ, DJANGO_AUTORELOAD_ENV: "true"}
    args = get_child_arguments()
    while True:
        p = subprocess.run(args, env=new_environ, close_fds=False)
        if p.returncode != 3:
            return p.returncode


class BaseReloader:
    def __init__(self):
        self.extra_files = set()
        self.directory_globs = defaultdict(set)
        self._stop_condition = threading.Event()

    def watch_dir(self, path, glob):
        path = Path(path)
        try:
            path = path.absolute()
        except FileNotFoundError:
            logger.debug(
                "Unable to watch directory %s as it cannot be resolved.",
                path,
                exc_info=True,
            )
            return
        logger.debug("Watching dir %s with glob %s.", path, glob)
        self.directory_globs[path].add(glob)

    def watched_files(self, include_globs=True):
        """
        Yield all files that need to be watched, including module files and
        files within globs.
        """
        yield from iter_all_python_module_files()
        yield from self.extra_files
        if include_globs:
            for directory, patterns in self.directory_globs.items():
                for pattern in patterns:
                    yield from directory.glob(pattern)

    def wait_for_apps_ready(self, app_reg, django_main_thread):
        """
        Wait until Django reports that the apps have been loaded. If the given
        thread has terminated before the apps are ready, then a SyntaxError or
        other non-recoverable error has been raised. In that case, stop waiting
        for the apps_ready event and continue processing.

        Return True if the thread is alive and the ready event has been
        triggered, or False if the thread is terminated while waiting for the
        event.
        """
        while django_main_thread.is_alive():
            if app_reg.ready_event.wait(timeout=0.1):
                return True
        else:
            logger.debug("Main Django thread has terminated before apps are ready.")
            return False

    def run(self, django_main_thread):
        logger.debug("Waiting for apps ready_event.")
        self.wait_for_apps_ready(apps, django_main_thread)
        from django.urls import get_resolver

        # Prevent a race condition where URL modules aren't loaded when the
        # reloader starts by accessing the urlconf_module property.
        try:
            get_resolver().urlconf_module
        except Exception:
            # Loading the urlconf can result in errors during development.
            # If this occurs then swallow the error and continue.
            pass
        logger.debug("Apps ready_event triggered. Sending autoreload_started signal.")
        autoreload_started.send(sender=self)
        self.run_loop()

    def run_loop(self):
        ticker = self.tick()
        while not self.should_stop:
            try:
                next(ticker)
            except StopIteration:
                break
        self.stop()

    def tick(self):
        """
        This generator is called in a loop from run_loop. It's important that
        the method takes care of pausing or otherwise waiting for a period of
        time. This split between run_loop() and tick() is to improve the
        testability of the reloader implementations by decoupling the work they
        do from the loop.
        """
        raise NotImplementedError("subclasses must implement tick().")

    @classmethod
    def check_availability(cls):
        raise NotImplementedError("subclasses must implement check_availability().")

    def notify_file_changed(self, path):
        results = file_changed.send(sender=self, file_path=path)
        logger.debug("%s notified as changed. Signal results: %s.", path, results)
        if not any(res[1] for res in results):
            trigger_reload(path)

    # These are primarily used for testing.
    @property
    def should_stop(self):
        return self._stop_condition.is_set()

    def stop(self):
        self._stop_condition.set()


class StatReloader(BaseReloader):
    SLEEP_TIME = 1  # Check for changes once per second.

    def tick(self):
        mtimes = {}
        while True:
            for filepath, mtime in self.snapshot_files():
                old_time = mtimes.get(filepath)
                mtimes[filepath] = mtime
                if old_time is None:
                    logger.debug("File %s first seen with mtime %s", filepath, mtime)
                    continue
                elif mtime > old_time:
                    logger.debug(
                        "File %s previous mtime: %s, current mtime: %s",
                        filepath,
                        old_time,
                        mtime,
                    )
                    self.notify_file_changed(filepath)

            time.sleep(self.SLEEP_TIME)
            yield

    def snapshot_files(self):
        # watched_files may produce duplicate paths if globs overlap.
        seen_files = set()
        for file in self.watched_files():
            if file in seen_files:
                continue
            try:
                mtime = file.stat().st_mtime
            except OSError:
                # This is thrown when the file does not exist.
                continue
            seen_files.add(file)
            yield file, mtime

    @classmethod
    def check_availability(cls):
        return True


class WatchmanUnavailable(RuntimeError):
    pass


class WatchmanReloader(BaseReloader):
    def __init__(self):
        self.roots = defaultdict(set)
        self.processed_request = threading.Event()
        self.client_timeout = int(os.environ.get("DJANGO_WATCHMAN_TIMEOUT", 5))
        super().__init__()

    @cached_property
    def client(self):
        return pywatchman.client(timeout=self.client_timeout)

    def _watch_root(self, root):
        # In practice this shouldn't occur, however, it's possible that a
        # directory that doesn't exist yet is being watched. If it's outside of
        # sys.path then this will end up a new root. How to handle this isn't
        # clear: Not adding the root will likely break when subscribing to the
        # changes, however, as this is currently an internal API,  no files
        # will be being watched outside of sys.path. Fixing this by checking
        # inside watch_glob() and watch_dir() is expensive, instead this could
        # could fall back to the StatReloader if this case is detected? For
        # now, watching its parent, if possible, is sufficient.
        if not root.exists():
            if not root.parent.exists():
                logger.warning(
                    "Unable to watch root dir %s as neither it or its parent exist.",
                    root,
                )
                return
            root = root.parent
        result = self.client.query("watch-project", str(root.absolute()))
        if "warning" in result:
            logger.warning("Watchman warning: %s", result["warning"])
        logger.debug("Watchman watch-project result: %s", result)
        return result["watch"], result.get("relative_path")

    @lru_cache
    def _get_clock(self, root):
        return self.client.query("clock", root)["clock"]

    def _subscribe(self, directory, name, expression):
        root, rel_path = self._watch_root(directory)
        # Only receive notifications of files changing, filtering out other types
        # like special files: https://facebook.github.io/watchman/docs/type
        only_files_expression = [
            "allof",
            ["anyof", ["type", "f"], ["type", "l"]],
            expression,
        ]
        query = {
            "expression": only_files_expression,
            "fields": ["name"],
            "since": self._get_clock(root),
            "dedup_results": True,
        }
        if rel_path:
            query["relative_root"] = rel_path
        logger.debug(
            "Issuing watchman subscription %s, for root %s. Query: %s",
            name,
            root,
            query,
        )
        self.client.query("subscribe", root, name, query)

    def _subscribe_dir(self, directory, filenames):
        if not directory.exists():
            if not directory.parent.exists():
                logger.warning(
                    "Unable to watch directory %s as neither it or its parent exist.",
                    directory,
                )
                return
            prefix = "files-parent-%s" % directory.name
            filenames = ["%s/%s" % (directory.name, filename) for filename in filenames]
            directory = directory.parent
            expression = ["name", filenames, "wholename"]
        else:
            prefix = "files"
            expression = ["name", filenames]
        self._subscribe(directory, "%s:%s" % (prefix, directory), expression)

    def _watch_glob(self, directory, patterns):
        """
        Watch a directory with a specific glob. If the directory doesn't yet
        exist, attempt to watch the parent directory and amend the patterns to
        include this. It's important this method isn't called more than one per
        directory when updating all subscriptions. Subsequent calls will
        overwrite the named subscription, so it must include all possible glob
        expressions.
        """
        prefix = "glob"
        if not directory.exists():
            if not directory.parent.exists():
                logger.warning(
                    "Unable to watch directory %s as neither it or its parent exist.",
                    directory,
                )
                return
            prefix = "glob-parent-%s" % directory.name
            patterns = ["%s/%s" % (directory.name, pattern) for pattern in patterns]
            directory = directory.parent

        expression = ["anyof"]
        for pattern in patterns:
            expression.append(["match", pattern, "wholename"])
        self._subscribe(directory, "%s:%s" % (prefix, directory), expression)

    def watched_roots(self, watched_files):
        extra_directories = self.directory_globs.keys()
        watched_file_dirs = [f.parent for f in watched_files]
        sys_paths = list(sys_path_directories())
        return frozenset((*extra_directories, *watched_file_dirs, *sys_paths))

    def _update_watches(self):
        watched_files = list(self.watched_files(include_globs=False))
        found_roots = common_roots(self.watched_roots(watched_files))
        logger.debug("Watching %s files", len(watched_files))
        logger.debug("Found common roots: %s", found_roots)
        # Setup initial roots for performance, shortest roots first.
        for root in sorted(found_roots):
            self._watch_root(root)
        for directory, patterns in self.directory_globs.items():
            self._watch_glob(directory, patterns)
        # Group sorted watched_files by their parent directory.
        sorted_files = sorted(watched_files, key=lambda p: p.parent)
        for directory, group in itertools.groupby(sorted_files, key=lambda p: p.parent):
            # These paths need to be relative to the parent directory.
            self._subscribe_dir(
                directory, [str(p.relative_to(directory)) for p in group]
            )

    def update_watches(self):
        try:
            self._update_watches()
        except Exception as ex:
            # If the service is still available, raise the original exception.
            if self.check_server_status(ex):
                raise

    def _check_subscription(self, sub):
        subscription = self.client.getSubscription(sub)
        if not subscription:
            return
        logger.debug("Watchman subscription %s has results.", sub)
        for result in subscription:
            # When using watch-project, it's not simple to get the relative
            # directory without storing some specific state. Store the full
            # path to the directory in the subscription name, prefixed by its
            # type (glob, files).
            root_directory = Path(result["subscription"].split(":", 1)[1])
            logger.debug("Found root directory %s", root_directory)
            for file in result.get("files", []):
                self.notify_file_changed(root_directory / file)

    def request_processed(self, **kwargs):
        logger.debug("Request processed. Setting update_watches event.")
        self.processed_request.set()

    def tick(self):
        request_finished.connect(self.request_processed)
        self.update_watches()
        while True:
            if self.processed_request.is_set():
                self.update_watches()
                self.processed_request.clear()
            try:
                self.client.receive()
            except pywatchman.SocketTimeout:
                pass
            except pywatchman.WatchmanError as ex:
                logger.debug("Watchman error: %s, checking server status.", ex)
                self.check_server_status(ex)
            else:
                for sub in list(self.client.subs.keys()):
                    self._check_subscription(sub)
            yield
            # Protect against busy loops.
            time.sleep(0.1)

    def stop(self):
        self.client.close()
        super().stop()

    def check_server_status(self, inner_ex=None):
        """Return True if the server is available."""
        try:
            self.client.query("version")
        except Exception:
            raise WatchmanUnavailable(str(inner_ex)) from inner_ex
        return True

    @classmethod
    def check_availability(cls):
        if not pywatchman:
            raise WatchmanUnavailable("pywatchman not installed.")
        client = pywatchman.client(timeout=0.1)
        try:
            result = client.capabilityCheck()
        except Exception:
            # The service is down?
            raise WatchmanUnavailable("Cannot connect to the watchman service.")
        version = get_version_tuple(result["version"])
        # Watchman 4.9 includes multiple improvements to watching project
        # directories as well as case insensitive filesystems.
        logger.debug("Watchman version %s", version)
        if version < (4, 9):
            raise WatchmanUnavailable("Watchman 4.9 or later is required.")

class MutableWatcher:
    """
    Watchfiles doesn't give us a way to adjust watches at runtime, but it does give us a way to stop the watcher
    when a condition is set.
    This class wraps this to provide a single iterator that may replace the underlying watchfiles iterator when
    roots are added or removed.
    """

    def __init__(self, filter_func: Callable[[watchfiles.Change, str], bool]):
        self.change_event = threading.Event()
        self.stop_event = threading.Event()
        self.roots: Set[str] = set()
        self.filter_func = filter_func

    def set_roots(self, roots: Set[str]):
        if roots != self.roots:
            self.roots = roots
            self.change_event.set()

    def stop(self):
        self.stop_event.set()

    def __iter__(self) -> Generator[List[watchfiles.Change], None, None]:
        while True:
            self.change_event.clear()
            for changes in watchfiles.watch(*self.roots, watch_filter=self.filter_func,
                                            stop_event=self.stop_event, debounce=0,
                                            rust_timeout=100, yield_on_timeout=True):
                if self.change_event.is_set():
                    break
                yield changes


class WatchfilesReloader(BaseReloader):
    def __init__(self):
        self.watcher = MutableWatcher(self.file_filter)
        self.processed_request = threading.Event()
        super().__init__()

    def file_filter(self, change: watchfiles.Change, path: str) -> bool:
        path = Path(path)
        if path in set(self.watched_files(include_globs=False)):
            return True
        for directory, globs in self.directory_globs.items():
            if path.is_relative_to(directory):
                for glob in globs:
                    if fnmatch.fnmatch(path.relative_to(directory), glob):
                        return True
        return False

    def watched_roots(self, watched_files: List[Path]) -> Set[Path]:
        extra_directories = self.directory_globs.keys()
        watched_file_dirs = {f.parent for f in watched_files}
        sys_paths = set(sys_path_directories())
        return {*extra_directories, *watched_file_dirs, *sys_paths}

    def request_processed(self, **kwargs):
        logger.debug("Request processed. Setting update_watches event.")
        self.processed_request.set()

    def update_watches(self):
        watched_files = list(self.watched_files(include_globs=False))
        roots = common_roots(self.watched_roots(watched_files))
        self.watcher.set_roots(roots)

    def tick(self) -> Generator[None, None, None]:
        request_finished.connect(self.request_processed)
        self.update_watches()

        for changes in self.watcher:
            if self.processed_request.is_set():
                self.update_watches()
                self.processed_request.clear()

            for _, path in changes:
                logger.debug(f"File changed: {path}")
                self.notify_file_changed(Path(path))
            yield

def get_reloader():
    """Return the most suitable reloader for this environment."""
    try:
        WatchmanReloader.check_availability()
    except WatchmanUnavailable:
        return StatReloader()
    return WatchmanReloader()


def start_django(reloader, main_func, *args, **kwargs):
    ensure_echo_on()

    main_func = check_errors(main_func)
    django_main_thread = threading.Thread(
        target=main_func, args=args, kwargs=kwargs, name="django-main-thread"
    )
    django_main_thread.daemon = True
    django_main_thread.start()

    while not reloader.should_stop:
        reloader.run(django_main_thread)


def run_with_reloader(main_func, *args, **kwargs):
    signal.signal(signal.SIGTERM, lambda *args: sys.exit(0))
    try:
        if os.environ.get(DJANGO_AUTORELOAD_ENV) == "true":
            reloader = get_reloader()
            logger.info(
                "Watching for file changes with %s", reloader.__class__.__name__
            )
            start_django(reloader, main_func, *args, **kwargs)
        else:
            exit_code = restart_with_reloader()
            sys.exit(exit_code)
    except KeyboardInterrupt:
        pass
