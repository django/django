"""
>>> from django.utils.datastructures import SortedDict

>>> d = SortedDict()
>>> d[7] = 'seven'
>>> d[1] = 'one'
>>> d[9] = 'nine'
>>> d.keys()
[7, 1, 9]
>>> d.values()
['seven', 'one', 'nine']
>>> d.items()
[(7, 'seven'), (1, 'one'), (9, 'nine')]

# Overwriting an item keeps it's place.
>>> d[1] = 'ONE'
>>> d.values()
['seven', 'ONE', 'nine']

# New items go to the end.
>>> d[0] = 'nil'
>>> d.keys()
[7, 1, 9, 0]

# Deleting an item, then inserting the same key again will place it at the end.
>>> del d[7]
>>> d.keys()
[1, 9, 0]
>>> d[7] = 'lucky number 7'
>>> d.keys()
[1, 9, 0, 7]

# Changing the keys won't do anything, it's only a copy of the keys dict.
>>> k = d.keys()
>>> k.remove(9)
>>> d.keys()
[1, 9, 0, 7]

# Initialising a SortedDict with two keys will just take the first one. A real
# dict will actually take the second value so we will too, but we'll keep the
# ordering from the first key found.
>>> tuples = ((2, 'two'), (1, 'one'), (2, 'second-two'))
>>> d = SortedDict(tuples)
>>> d.keys()
[2, 1]
>>> real_dict = dict(tuples)
>>> sorted(real_dict.values())
['one', 'second-two']
>>> d.values() # Here the order of SortedDict values *is* what we are testing
['second-two', 'one']
"""

