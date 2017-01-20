# Copyright (c) 2008-2009 Aryeh Leib Taurog, all rights reserved.
# Released under the New BSD license.
"""
This module contains a base type which provides list-style mutations
without specific data storage methods.

See also http://static.aryehleib.com/oldsite/MutableLists.html

Author: Aryeh Leib Taurog.
"""
from functools import total_ordering


@total_ordering
class ListMixin:
    """
    A base class which provides complete list interface.
    Derived classes must call ListMixin's __init__() function
    and implement the following:

    function _get_single_external(self, i):
        Return single item with index i for general use.
        The index i will always satisfy 0 <= i < len(self).

    function _get_single_internal(self, i):
        Same as above, but for use within the class [Optional]
        Note that if _get_single_internal and _get_single_internal return
        different types of objects, _set_list must distinguish
        between the two and handle each appropriately.

    function _set_list(self, length, items):
        Recreate the entire object.

        NOTE: items may be a generator which calls _get_single_internal.
        Therefore, it is necessary to cache the values in a temporary:
            temp = list(items)
        before clobbering the original storage.

    function _set_single(self, i, value):
        Set the single item at index i to value [Optional]
        If left undefined, all mutations will result in rebuilding
        the object using _set_list.

    function __len__(self):
        Return the length

    int _minlength:
        The minimum legal length [Optional]

    int _maxlength:
        The maximum legal length [Optional]

    type or tuple _allowed:
        A type or tuple of allowed item types [Optional]
    """

    _minlength = 0
    _maxlength = None

    # ### Python initialization and special list interface methods ###

    def __init__(self, *args, **kwargs):
        if not hasattr(self, '_get_single_internal'):
            self._get_single_internal = self._get_single_external

        if not hasattr(self, '_set_single'):
            self._set_single = self._set_single_rebuild
            self._assign_extended_slice = self._assign_extended_slice_rebuild

        super(ListMixin, self).__init__(*args, **kwargs)

    def __getitem__(self, index):
        "Get the item(s) at the specified index/slice."
        if isinstance(index, slice):
            return [self._get_single_external(i) for i in range(*index.indices(len(self)))]
        else:
            index = self._checkindex(index)
            return self._get_single_external(index)

    def __delitem__(self, index):
        "Delete the item(s) at the specified index/slice."
        if not isinstance(index, (int, slice)):
            raise TypeError("%s is not a legal index" % index)

        # calculate new length and dimensions
        origLen = len(self)
        if isinstance(index, int):
            index = self._checkindex(index)
            indexRange = [index]
        else:
            indexRange = range(*index.indices(origLen))

        newLen = origLen - len(indexRange)
        newItems = (self._get_single_internal(i)
                    for i in range(origLen)
                    if i not in indexRange)

        self._rebuild(newLen, newItems)

    def __setitem__(self, index, val):
        "Set the item(s) at the specified index/slice."
        if isinstance(index, slice):
            self._set_slice(index, val)
        else:
            index = self._checkindex(index)
            self._check_allowed((val,))
            self._set_single(index, val)

    # ### Special methods for arithmetic operations ###
    def __add__(self, other):
        'add another list-like object'
        return self.__class__(list(self) + list(other))

    def __radd__(self, other):
        'add to another list-like object'
        return other.__class__(list(other) + list(self))

    def __iadd__(self, other):
        'add another list-like object to self'
        self.extend(list(other))
        return self

    def __mul__(self, n):
        'multiply'
        return self.__class__(list(self) * n)

    def __rmul__(self, n):
        'multiply'
        return self.__class__(list(self) * n)

    def __imul__(self, n):
        'multiply'
        if n <= 0:
            del self[:]
        else:
            cache = list(self)
            for i in range(n - 1):
                self.extend(cache)
        return self

    def __eq__(self, other):
        olen = len(other)
        for i in range(olen):
            try:
                c = self[i] == other[i]
            except IndexError:
                # self must be shorter
                return False
            if not c:
                return False
        return len(self) == olen

    def __lt__(self, other):
        olen = len(other)
        for i in range(olen):
            try:
                c = self[i] < other[i]
            except IndexError:
                # self must be shorter
                return True
            if c:
                return c
            elif other[i] < self[i]:
                return False
        return len(self) < olen

    # ### Public list interface Methods ###
    # ## Non-mutating ##
    def count(self, val):
        "Standard list count method"
        count = 0
        for i in self:
            if val == i:
                count += 1
        return count

    def index(self, val):
        "Standard list index method"
        for i in range(0, len(self)):
            if self[i] == val:
                return i
        raise ValueError('%s not found in object' % val)

    # ## Mutating ##
    def append(self, val):
        "Standard list append method"
        self[len(self):] = [val]

    def extend(self, vals):
        "Standard list extend method"
        self[len(self):] = vals

    def insert(self, index, val):
        "Standard list insert method"
        if not isinstance(index, int):
            raise TypeError("%s is not a legal index" % index)
        self[index:index] = [val]

    def pop(self, index=-1):
        "Standard list pop method"
        result = self[index]
        del self[index]
        return result

    def remove(self, val):
        "Standard list remove method"
        del self[self.index(val)]

    def reverse(self):
        "Standard list reverse method"
        self[:] = self[-1::-1]

    def sort(self, cmp=None, key=None, reverse=False):
        "Standard list sort method"
        if key:
            temp = [(key(v), v) for v in self]
            temp.sort(key=lambda x: x[0], reverse=reverse)
            self[:] = [v[1] for v in temp]
        else:
            temp = list(self)
            if cmp is not None:
                temp.sort(cmp=cmp, reverse=reverse)
            else:
                temp.sort(reverse=reverse)
            self[:] = temp

    # ### Private routines ###
    def _rebuild(self, newLen, newItems):
        if newLen and newLen < self._minlength:
            raise ValueError('Must have at least %d items' % self._minlength)
        if self._maxlength is not None and newLen > self._maxlength:
            raise ValueError('Cannot have more than %d items' % self._maxlength)

        self._set_list(newLen, newItems)

    def _set_single_rebuild(self, index, value):
        self._set_slice(slice(index, index + 1, 1), [value])

    def _checkindex(self, index, correct=True):
        length = len(self)
        if 0 <= index < length:
            return index
        if correct and -length <= index < 0:
            return index + length
        raise IndexError('invalid index: %s' % index)

    def _check_allowed(self, items):
        if hasattr(self, '_allowed'):
            if False in [isinstance(val, self._allowed) for val in items]:
                raise TypeError('Invalid type encountered in the arguments.')

    def _set_slice(self, index, values):
        "Assign values to a slice of the object"
        try:
            iter(values)
        except TypeError:
            raise TypeError('can only assign an iterable to a slice')

        self._check_allowed(values)

        origLen = len(self)
        valueList = list(values)
        start, stop, step = index.indices(origLen)

        # CAREFUL: index.step and step are not the same!
        # step will never be None
        if index.step is None:
            self._assign_simple_slice(start, stop, valueList)
        else:
            self._assign_extended_slice(start, stop, step, valueList)

    def _assign_extended_slice_rebuild(self, start, stop, step, valueList):
        'Assign an extended slice by rebuilding entire list'
        indexList = range(start, stop, step)
        # extended slice, only allow assigning slice of same size
        if len(valueList) != len(indexList):
            raise ValueError('attempt to assign sequence of size %d '
                             'to extended slice of size %d'
                             % (len(valueList), len(indexList)))

        # we're not changing the length of the sequence
        newLen = len(self)
        newVals = dict(zip(indexList, valueList))

        def newItems():
            for i in range(newLen):
                if i in newVals:
                    yield newVals[i]
                else:
                    yield self._get_single_internal(i)

        self._rebuild(newLen, newItems())

    def _assign_extended_slice(self, start, stop, step, valueList):
        'Assign an extended slice by re-assigning individual items'
        indexList = range(start, stop, step)
        # extended slice, only allow assigning slice of same size
        if len(valueList) != len(indexList):
            raise ValueError('attempt to assign sequence of size %d '
                             'to extended slice of size %d'
                             % (len(valueList), len(indexList)))

        for i, val in zip(indexList, valueList):
            self._set_single(i, val)

    def _assign_simple_slice(self, start, stop, valueList):
        'Assign a simple slice; Can assign slice of any length'
        origLen = len(self)
        stop = max(start, stop)
        newLen = origLen - stop + start + len(valueList)

        def newItems():
            for i in range(origLen + 1):
                if i == start:
                    for val in valueList:
                        yield val

                if i < origLen:
                    if i < start or i >= stop:
                        yield self._get_single_internal(i)

        self._rebuild(newLen, newItems())
