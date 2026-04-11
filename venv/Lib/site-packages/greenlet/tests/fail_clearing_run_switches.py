# -*- coding: utf-8 -*-
"""
If we have a run callable passed to the constructor or set as an
attribute, but we don't actually use that (because ``__getattribute__``
or the like interferes), then when we clear callable before beginning
to run, there's an opportunity for Python code to run.

"""
import greenlet

g = None
main = greenlet.getcurrent()

results = []

class RunCallable:

    def __del__(self):
        results.append(('RunCallable', '__del__'))
        main.switch('from RunCallable')


class G(greenlet.greenlet):

    def __getattribute__(self, name):
        if name == 'run':
            results.append(('G.__getattribute__', 'run'))
            return run_func
        return object.__getattribute__(self, name)


def run_func():
    results.append(('run_func', 'enter'))


g = G(RunCallable())
# Try to start G. It will get to the point where it deletes
# its run callable C++ variable in inner_bootstrap. That triggers
# the __del__ method, which switches back to main before g
# actually even starts running.
x = g.switch()
results.append(('main: g.switch()', x))
# In the C++ code, this results in g->g_switch() appearing to return, even though
# it has yet to run.
print('In main with', x, flush=True)
g.switch()
print('RESULTS', results)
