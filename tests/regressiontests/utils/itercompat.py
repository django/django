"""
# Tests of the utils itercompat library.

>>> from django.utils.itercompat import sorted as compat_sorted

# Check the replacement version of sorted
>>> x = [5,1,4,2,3]
>>> y = compat_sorted(x)
>>> print y
[1, 2, 3, 4, 5]

>>> print x 
[5, 1, 4, 2, 3]

"""