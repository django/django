"""
Uses a trace function to switch greenlets at unexpected times.

In the trace function, we switch from the current greenlet to another
greenlet, which switches
"""
import greenlet

g1 = None
g2 = None

switch_to_g2 = False

def tracefunc(*args):
    print('TRACE', *args)
    global switch_to_g2
    if switch_to_g2:
        switch_to_g2 = False
        g2.switch()
    print('\tLEAVE TRACE', *args)

def g1_run():
    print('In g1_run')
    global switch_to_g2
    switch_to_g2 = True
    from_parent = greenlet.getcurrent().parent.switch()
    print('Return to g1_run')
    print('From parent', from_parent)

def g2_run():
    #g1.switch()
    greenlet.getcurrent().parent.switch()

greenlet.settrace(tracefunc)

g1 = greenlet.greenlet(g1_run)
g2 = greenlet.greenlet(g2_run)

# This switch didn't actually finish!
# And if it did, it would raise TypeError
# because g1_run() doesn't take any arguments.
g1.switch(1)
print('Back in main')
g1.switch(2)
