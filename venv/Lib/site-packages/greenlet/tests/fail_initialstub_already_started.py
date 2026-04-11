"""
Testing initialstub throwing an already started exception.
"""

import greenlet

a = None
b = None
c = None
main = greenlet.getcurrent()

# If we switch into a dead greenlet,
# we go looking for its parents.
# if a parent is not yet started, we start it.

results = []

def a_run(*args):
    #results.append('A')
    results.append(('Begin A', args))


def c_run():
    results.append('Begin C')
    b.switch('From C')
    results.append('C done')

class A(greenlet.greenlet): pass

class B(greenlet.greenlet):
    doing_it = False
    def __getattribute__(self, name):
        if name == 'run' and not self.doing_it:
            assert greenlet.getcurrent() is c
            self.doing_it = True
            results.append('Switch to b from B.__getattribute__ in '
                           + type(greenlet.getcurrent()).__name__)
            b.switch()
            results.append('B.__getattribute__ back from main in '
                           + type(greenlet.getcurrent()).__name__)
        if name == 'run':
            name = '_B_run'
        return object.__getattribute__(self, name)

    def _B_run(self, *arg):
        results.append(('Begin B', arg))
        results.append('_B_run switching to main')
        main.switch('From B')

class C(greenlet.greenlet):
    pass
a = A(a_run)
b = B(parent=a)
c = C(c_run, b)

# Start a child; while running, it will start B,
# but starting B will ALSO start B.
result = c.switch()
results.append(('main from c', result))

# Switch back to C, which was in the middle of switching
# already. This will throw the ``GreenletStartedWhileInPython``
# exception, which results in parent A getting started (B is finished)
c.switch()

results.append(('A dead?', a.dead, 'B dead?', b.dead, 'C dead?', c.dead))

# A and B should both be dead now.
assert a.dead
assert b.dead
assert not c.dead

result = c.switch()
results.append(('main from c.2', result))
# Now C is dead
assert c.dead

print("RESULTS:", results)
