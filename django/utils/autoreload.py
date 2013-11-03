# Autoreloading launcher.
# Borrowed from Peter Hunt and the CherryPy project (http://www.cherrypy.org).
# Some taken from Ian Bicking's Paste (http://pythonpaste.org/).
#
# Portions copyright (c) 2004, CherryPy Team (team@cherrypy.org)
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright notice,
#       this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright notice,
#       this list of conditions and the following disclaimer in the documentation
#       and/or other materials provided with the distribution.
#     * Neither the name of the CherryPy Team nor the names of its contributors
#       may be used to endorse or promote products derived from this software
#       without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import os
import signal
import sys
import time
import traceback

from django.conf import settings
from django.core.signals import request_finished
try:
    from django.utils.six.moves import _thread as thread
except ImportError:
    from django.utils.six.moves import _dummy_thread as thread

# This import does nothing, but it's necessary to avoid some race conditions
# in the threading module. See http://code.djangoproject.com/ticket/2330 .
try:
    import threading  # NOQA
except ImportError:
    pass

try:
    import termios
except ImportError:
    termios = None

USE_INOTIFY = False
try:
    # Test whether inotify is enabled and likely to work
    import pyinotify

    fd = pyinotify.INotifyWrapper.create().inotify_init()
    if fd >= 0:
        USE_INOTIFY = True
        os.close(fd)
except ImportError:
    pass

try:
    import select
    select.kevent, select.kqueue
    USE_KQUEUE = True

    import resource
    NOFILES_SOFT, NOFILES_HARD = resource.getrlimit(resource.RLIMIT_NOFILE)

    import subprocess
    command = ["sysctl", "-n", "kern.maxfilesperproc"]
    NOFILES_KERN = int(subprocess.check_output(command).strip())
except (AttributeError, OSError):
    USE_KQUEUE = False

RUN_RELOADER = True

_mtimes = {}
_win = (sys.platform == "win32")

_error_files = []


def gen_filenames():
    """
    Yields a generator over filenames referenced in sys.modules and translation
    files.
    """
    filenames = [filename.__file__ for filename in sys.modules.values()
                if hasattr(filename, '__file__')]

    # Add the names of the .mo files that can be generated
    # by compilemessages management command to the list of files watched.
    basedirs = [os.path.join(os.path.dirname(os.path.dirname(__file__)),
                             'conf', 'locale'),
                'locale']
    basedirs.extend(settings.LOCALE_PATHS)
    basedirs = [os.path.abspath(basedir) for basedir in basedirs
                if os.path.isdir(basedir)]
    for basedir in basedirs:
        for dirpath, dirnames, locale_filenames in os.walk(basedir):
            for filename in locale_filenames:
                if filename.endswith('.mo'):
                    filenames.append(os.path.join(dirpath, filename))

    for filename in filenames + _error_files:
        if not filename:
            continue
        if filename.endswith(".pyc") or filename.endswith(".pyo"):
            filename = filename[:-1]
        if filename.endswith("$py.class"):
            filename = filename[:-9] + ".py"
        if os.path.exists(filename):
            yield filename


def inotify_code_changed():
    """
    Checks for changed code using inotify. After being called
    it blocks until a change event has been fired.
    """
    wm = pyinotify.WatchManager()
    notifier = pyinotify.Notifier(wm)

    def update_watch(sender=None, **kwargs):
        mask = (
            pyinotify.IN_MODIFY |
            pyinotify.IN_DELETE |
            pyinotify.IN_ATTRIB |
            pyinotify.IN_MOVED_FROM |
            pyinotify.IN_MOVED_TO |
            pyinotify.IN_CREATE
        )
        for path in gen_filenames():
            wm.add_watch(path, mask)

    request_finished.connect(update_watch)
    update_watch()

    # Block forever
    notifier.check_events(timeout=None)
    notifier.stop()

    # If we are here the code must have changed.
    return True


def kqueue_code_changed():
    """
    Checks for changed code using kqueue. After being called
    it blocks until a change event has been fired.
    """
    # We must increase the maximum number of open file descriptors because
    # kqueue requires one file descriptor per monitored file and default
    # resource limits are too low.
    #
    # In fact there are two limits:
    # - kernel limit: `sysctl kern.maxfilesperproc` -> 10240 on OS X.9
    # - resource limit: `launchctl limit maxfiles` -> 256 on OS X.9
    #
    # The latter can be changed with Python's resource module. However, it
    # cannot exceed the former. Suprisingly, getrlimit(3) -- used by both
    # launchctl and the resource module -- reports no "hard limit", even
    # though the kernel sets one.

    filenames = list(gen_filenames())

    # If project is too large or kernel limits are too tight, use polling.
    if len(filenames) > NOFILES_KERN:
        return code_changed()

    # Add the number of file descriptors we're going to use to the current
    # resource limit, while staying within the kernel limit.
    nofiles_target = min(len(filenames) + NOFILES_SOFT, NOFILES_KERN)
    resource.setrlimit(resource.RLIMIT_NOFILE, (nofiles_target, NOFILES_HARD))

    kqueue = select.kqueue()
    fds = [open(filename) for filename in filenames]

    _filter = select.KQ_FILTER_VNODE
    flags = select.KQ_EV_ADD
    fflags = select.KQ_NOTE_DELETE | select.KQ_NOTE_WRITE | select.KQ_NOTE_RENAME
    kevents = [select.kevent(fd, _filter, flags, fflags) for fd in fds]
    kqueue.control(kevents, 1)

    for fd in fds:
        fd.close()
    kqueue.close()

    return True


def code_changed():
    global _mtimes, _win
    for filename in gen_filenames():
        stat = os.stat(filename)
        mtime = stat.st_mtime
        if _win:
            mtime -= stat.st_ctime
        if filename not in _mtimes:
            _mtimes[filename] = mtime
            continue
        if mtime != _mtimes[filename]:
            _mtimes = {}
            try:
                del _error_files[_error_files.index(filename)]
            except ValueError:
                pass
            return True
    return False


def check_errors(fn):
    def wrapper(*args, **kwargs):
        try:
            fn(*args, **kwargs)
        except (ImportError, IndentationError, NameError, SyntaxError,
                TypeError, AttributeError):
            et, ev, tb = sys.exc_info()

            if getattr(ev, 'filename', None) is None:
                # get the filename from the last item in the stack
                filename = traceback.extract_tb(tb)[-1][0]
            else:
                filename = ev.filename

            if filename not in _error_files:
                _error_files.append(filename)

            raise

    return wrapper


def ensure_echo_on():
    if termios:
        fd = sys.stdin
        if fd.isatty():
            attr_list = termios.tcgetattr(fd)
            if not attr_list[3] & termios.ECHO:
                attr_list[3] |= termios.ECHO
                if hasattr(signal, 'SIGTTOU'):
                    old_handler = signal.signal(signal.SIGTTOU, signal.SIG_IGN)
                else:
                    old_handler = None
                termios.tcsetattr(fd, termios.TCSANOW, attr_list)
                if old_handler is not None:
                    signal.signal(signal.SIGTTOU, old_handler)


def reloader_thread():
    ensure_echo_on()
    if USE_INOTIFY:
        fn = inotify_code_changed
    elif USE_KQUEUE:
        fn = kqueue_code_changed
    else:
        fn = code_changed
    while RUN_RELOADER:
        if fn():
            sys.exit(3)  # force reload
        time.sleep(1)


def restart_with_reloader():
    while True:
        args = [sys.executable] + ['-W%s' % o for o in sys.warnoptions] + sys.argv
        if sys.platform == "win32":
            args = ['"%s"' % arg for arg in args]
        new_environ = os.environ.copy()
        new_environ["RUN_MAIN"] = 'true'
        exit_code = os.spawnve(os.P_WAIT, sys.executable, args, new_environ)
        if exit_code != 3:
            return exit_code


def python_reloader(main_func, args, kwargs):
    if os.environ.get("RUN_MAIN") == "true":
        thread.start_new_thread(main_func, args, kwargs)
        try:
            reloader_thread()
        except KeyboardInterrupt:
            pass
    else:
        try:
            exit_code = restart_with_reloader()
            if exit_code < 0:
                os.kill(os.getpid(), -exit_code)
            else:
                sys.exit(exit_code)
        except KeyboardInterrupt:
            pass


def jython_reloader(main_func, args, kwargs):
    from _systemrestart import SystemRestart
    thread.start_new_thread(main_func, args)
    while True:
        if code_changed():
            raise SystemRestart
        time.sleep(1)


def main(main_func, args=None, kwargs=None):
    if args is None:
        args = ()
    if kwargs is None:
        kwargs = {}
    if sys.platform.startswith('java'):
        reloader = jython_reloader
    else:
        reloader = python_reloader

    wrapped_main_func = check_errors(main_func)
    reloader(wrapped_main_func, args, kwargs)
