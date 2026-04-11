# -*- coding: utf-8 -*-
"""
A test helper for seeing what happens when slp_switch()
fails.
"""
# pragma: no cover

import greenlet


print('fail_slp_switch is running', flush=True)

runs = []
def func():
    runs.append(1)
    greenlet.getcurrent().parent.switch()
    runs.append(2)
    greenlet.getcurrent().parent.switch()
    runs.append(3)

g = greenlet._greenlet.UnswitchableGreenlet(func)
g.switch()
assert runs == [1]
g.switch()
assert runs == [1, 2]
g.force_slp_switch_error = True

# This should crash.
g.switch()
