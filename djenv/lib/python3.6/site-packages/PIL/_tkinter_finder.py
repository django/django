""" Find compiled module linking to Tcl / Tk libraries
"""
import sys

if sys.version_info.major > 2:
    from tkinter import _tkinter as tk
else:
    from Tkinter import tkinter as tk

if hasattr(sys, 'pypy_find_executable'):
    # Tested with packages at https://bitbucket.org/pypy/pypy/downloads.
    # PyPies 1.6, 2.0 do not have tkinter built in.  PyPy3-2.3.1 gives an
    # OSError trying to import tkinter. Otherwise:
    try:  # PyPy 5.1, 4.0.0, 2.6.1, 2.6.0
        TKINTER_LIB = tk.tklib_cffi.__file__
    except AttributeError:
        # PyPy3 2.4, 2.1-beta1; PyPy 2.5.1, 2.5.0, 2.4.0, 2.3, 2.2, 2.1
        TKINTER_LIB = tk.tkffi.verifier.modulefilename
else:
    TKINTER_LIB = tk.__file__
