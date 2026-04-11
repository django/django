import numpy as np

a = np.empty((2, 2)).flat

a.base
a.copy()
a.coords
a.index
iter(a)
next(a)
a[0]
a[...]
a[:]
a.__array__()

b = np.array([1]).flat
a[b]

a[0] = "1"
a[:] = "2"
a[...] = "3"
a[[]] = "4"
a[[0]] = "5"
a[[[0]]] = "6"
a[[[[[0]]]]] = "7"
a[b] = "8"
