"""
Like fail_switch_three_greenlets, but the call into g1_run would actually be
valid.
"""
import greenlet

g1 = None
g2 = None

switch_to_g2 = True

results = []

def tracefunc(*args):
    results.append(('trace', args[0]))
    print('TRACE', *args)
    global switch_to_g2
    if switch_to_g2:
        switch_to_g2 = False
        g2.switch('g2 from tracefunc')
    print('\tLEAVE TRACE', *args)

def g1_run(arg):
    results.append(('g1 arg', arg))
    print('In g1_run')
    from_parent = greenlet.getcurrent().parent.switch('from g1_run')
    results.append(('g1 from parent', from_parent))
    return 'g1 done'

def g2_run(arg):
    #g1.switch()
    results.append(('g2 arg', arg))
    parent = greenlet.getcurrent().parent.switch('from g2_run')
    global switch_to_g2
    switch_to_g2 = False
    results.append(('g2 from parent', parent))
    return 'g2 done'


greenlet.settrace(tracefunc)

g1 = greenlet.greenlet(g1_run)
g2 = greenlet.greenlet(g2_run)

x = g1.switch('g1 from main')
results.append(('main g1', x))
print('Back in main', x)
x = g1.switch('g2 from main')
results.append(('main g2', x))
print('back in amain again', x)
x = g1.switch('g1 from main 2')
results.append(('main g1.2', x))
x = g2.switch()
results.append(('main g2.2', x))
print("RESULTS:", results)
