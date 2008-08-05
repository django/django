"""
Code used in a couple of places to work with the current thread's environment.
Current users include i18n and request prefix handling.
"""

try:
    import threading
    currentThread = threading.currentThread
except ImportError:
    def currentThread():
        return "no threading"

