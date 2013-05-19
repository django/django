# Example of app layout that causes issue #12658:
# * Both `models` and `tests` are packages.
# * The tests raise a ImportError exception.
# `test_runner` tests performs test discovery on this app.
