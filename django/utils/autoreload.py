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
import subprocess
import sys
import time
import traceback

import _thread

from django.apps import apps
from django.conf import settings
from django.core.signals import request_finished

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

USE_WIN32_CHANGE_NOTIFICATION = False
if sys.platform == "win32":
    try:
        # Test whether Python for Windows Extensions are available
        import win32file
        import win32event
        import win32con

        USE_WIN32_CHANGE_NOTIFICATION = True
    except ImportError:
        pass

RUN_RELOADER = True

FILE_MODIFIED = 1
I18N_MODIFIED = 2

_mtimes = {}
_win = (sys.platform == "win32")

_exception = None
_error_files = []
_cached_modules = set()
_cached_filenames = []


def gen_filenames(only_new=False):
    """
    Return a list of filenames referenced in sys.modules and translation files.
    """
    # N.B. ``list(...)`` is needed, because this runs in parallel with
    # application code which might be mutating ``sys.modules``, and this will
    # fail with RuntimeError: cannot mutate dictionary while iterating
    global _cached_modules, _cached_filenames
    module_values = set(sys.modules.values())
    _cached_filenames = clean_files(_cached_filenames)
    if _cached_modules == module_values:
        # No changes in module list, short-circuit the function
        if only_new:
            return []
        else:
            return _cached_filenames + clean_files(_error_files)

    new_modules = module_values - _cached_modules
    new_filenames = clean_files(
        [filename.__file__ for filename in new_modules
         if hasattr(filename, '__file__')])

    if not _cached_filenames and settings.USE_I18N:
        # Add the names of the .mo files that can be generated
        # by compilemessages management command to the list of files watched.
        basedirs = [os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                 'conf', 'locale'),
                    'locale']
        for app_config in reversed(list(apps.get_app_configs())):
            basedirs.append(os.path.join(app_config.path, 'locale'))
        basedirs.extend(settings.LOCALE_PATHS)
        basedirs = [os.path.abspath(basedir) for basedir in basedirs
                    if os.path.isdir(basedir)]
        for basedir in basedirs:
            for dirpath, dirnames, locale_filenames in os.walk(basedir):
                for filename in locale_filenames:
                    if filename.endswith('.mo'):
                        new_filenames.append(os.path.join(dirpath, filename))

    _cached_modules = _cached_modules.union(new_modules)
    _cached_filenames += new_filenames
    if only_new:
        return new_filenames + clean_files(_error_files)
    else:
        return _cached_filenames + clean_files(_error_files)


def clean_files(filelist):
    filenames = []
    for filename in filelist:
        if not filename:
            continue
        if filename.endswith(".pyc") or filename.endswith(".pyo"):
            filename = filename[:-1]
        if filename.endswith("$py.class"):
            filename = filename[:-9] + ".py"
        if os.path.exists(filename):
            filenames.append(filename)
    return filenames


def reset_translations():
    import gettext
    from django.utils.translation import trans_real
    gettext._translations = {}
    trans_real._translations = {}
    trans_real._default = None
    trans_real._active = threading.local()


def inotify_code_changed():
    """
    Check for changed code using inotify. After being called
    it blocks until a change event has been fired.
    """
    class EventHandler(pyinotify.ProcessEvent):
        modified_code = None

        def process_default(self, event):
            if event.path.endswith('.mo'):
                EventHandler.modified_code = I18N_MODIFIED
            else:
                EventHandler.modified_code = FILE_MODIFIED

    wm = pyinotify.WatchManager()
    notifier = pyinotify.Notifier(wm, EventHandler())

    def update_watch(sender=None, **kwargs):
        if sender and getattr(sender, 'handles_files', False):
            # No need to update watches when request serves files.
            # (sender is supposed to be a django.core.handlers.BaseHandler subclass)
            return
        mask = (
            pyinotify.IN_MODIFY |
            pyinotify.IN_DELETE |
            pyinotify.IN_ATTRIB |
            pyinotify.IN_MOVED_FROM |
            pyinotify.IN_MOVED_TO |
            pyinotify.IN_CREATE |
            pyinotify.IN_DELETE_SELF |
            pyinotify.IN_MOVE_SELF
        )
        for path in gen_filenames(only_new=True):
            wm.add_watch(path, mask)

    # New modules may get imported when a request is processed.
    request_finished.connect(update_watch)

    # Block until an event happens.
    update_watch()
    notifier.check_events(timeout=None)
    notifier.read_events()
    notifier.process_events()
    notifier.stop()

    # If we are here the code must have changed.
    return EventHandler.modified_code


def win32_notify_code_changed():
    """
    Check for changed code using Windows API. After being called
    it blocks until a change event has been fired.
    """
    # WaitForMultipleObjects() can wait for only 64 handles max
    # This is why cannot monitor individual files neither each parent
    # directory as this would exceed the limit for a django project.
    #
    # For this reason watch directories, not files and also watch common
    # parent directories to further limit the number of items.
    common_parent_dirs = ['\\site-packages\\', '\\lib\\']
    
    def reduce_path_to_common_dir(dirpath):
        for dirname in common_parent_dirs:
            if dirname in dirpath:
                dirpath = dirpath[:dirpath.rfind(dirname) + len(dirname) - 1]
                break
        return dirpath

    dirs = set()
    watched_dirs = []
    handles = []
    for filename in gen_filenames():
        dirpath = os.path.dirname(filename)
        dirpath = dirpath if dirpath else '.'
        dirpath = reduce_path_to_common_dir(dirpath)
        if dirpath not in dirs:
            dirs.add(dirpath)
            handle = win32file.FindFirstChangeNotification(
                dirpath,
                True,  # watch tree
                win32con.FILE_NOTIFY_CHANGE_SIZE |
                win32con.FILE_NOTIFY_CHANGE_LAST_WRITE
            )
            if handle != win32file.INVALID_HANDLE_VALUE:
                handles.append(handle)
                watched_dirs.append(dirpath)

    dirs = None  # Free memory before wait
    if len(handles) > win32event.MAXIMUM_WAIT_OBJECTS:
        # Cannot watch all files for changes, some changes may not be detected
        for handle in handles[win32event.MAXIMUM_WAIT_OBJECTS:]:
            win32file.FindCloseChangeNotification(handle)
        handles = handles[:win32event.MAXIMUM_WAIT_OBJECTS]

    result = win32event.WaitForMultipleObjects(handles, False, win32event.INFINITE)
    index = result - win32event.WAIT_OBJECT_0
    changed_dir = watched_dirs[index]

    def get_first_changed_file(changed_dir):
        FILE_LIST_DIRECTORY = 0x0001
        dir_handle = win32file.CreateFile(
            changed_dir,
            FILE_LIST_DIRECTORY,
            win32con.FILE_SHARE_READ |
            win32con.FILE_SHARE_WRITE |
            win32con.FILE_SHARE_DELETE,
            None,
            win32con.OPEN_EXISTING,
            win32con.FILE_FLAG_BACKUP_SEMANTICS,
            None
        )
        results = win32file.ReadDirectoryChangesW(
            dir_handle,
            1024,
            True,
            win32con.FILE_NOTIFY_CHANGE_FILE_NAME |
            win32con.FILE_NOTIFY_CHANGE_DIR_NAME |
            win32con.FILE_NOTIFY_CHANGE_ATTRIBUTES |
            win32con.FILE_NOTIFY_CHANGE_SIZE |
            win32con.FILE_NOTIFY_CHANGE_LAST_WRITE |
            win32con.FILE_NOTIFY_CHANGE_SECURITY,
            None,
            None
        )
        path = ''
        for action, filename in results:
            path = os.path.join(changed_dir, filename)
            break

        win32file.CloseHandle(dir_handle)
        return path

    for handle in handles:
        win32file.FindCloseChangeNotification(handle)

    filename = get_first_changed_file(changed_dir)
    return I18N_MODIFIED if filename.endswith('.mo') else FILE_MODIFIED


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
            return I18N_MODIFIED if filename.endswith('.mo') else FILE_MODIFIED
    return False


def check_errors(fn):
    def wrapper(*args, **kwargs):
        global _exception
        try:
            fn(*args, **kwargs)
        except Exception:
            _exception = sys.exc_info()

            et, ev, tb = _exception

            if getattr(ev, 'filename', None) is None:
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
        raise _exception[0](_exception[1]).with_traceback(_exception[2])


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
    elif USE_WIN32_CHANGE_NOTIFICATION:
        fn = win32_notify_code_changed
    else:
        fn = code_changed
    while RUN_RELOADER:
        change = fn()
        if change == FILE_MODIFIED:
            sys.exit(3)  # force reload
        elif change == I18N_MODIFIED:
            reset_translations()
        time.sleep(1)


def restart_with_reloader():
    while True:
        args = [sys.executable] + ['-W%s' % o for o in sys.warnoptions] + sys.argv
        new_environ = os.environ.copy()
        new_environ["RUN_MAIN"] = 'true'
        exit_code = subprocess.call(args, env=new_environ)
        if exit_code != 3:
            return exit_code


def python_reloader(main_func, args, kwargs):
    if os.environ.get("RUN_MAIN") == "true":
        _thread.start_new_thread(main_func, args, kwargs)
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
    _thread.start_new_thread(main_func, args)
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
