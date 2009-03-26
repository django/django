# Copyright (c) 2008-2009 Aryeh Leib Taurog, all rights reserved.
# Released under the New BSD license.
"""
This module contains a base type which provides list-style mutations
This is akin to UserList, but without specific data storage methods.
Possible candidate for a more general position in the source tree,
perhaps django.utils

Author: Aryeh Leib Taurog.
"""
class ListMixin(object):
    """
    A base class which provides complete list interface
    derived classes should implement the following:

    function _getitem_external(self, i):
        Return single item with index i for general use

    function _getitem_internal(self, i):
        Same as above, but for use within the class [Optional]

    function _set_collection(self, length, items):
        Recreate the entire object

    function _set_single(self, i, value):
        Set the single item at index i to value [Optional]
        If left undefined, all mutations will result in rebuilding
        the object using _set_collection.

    function __len__(self):
        Return the length

    function __iter__(self):
        Return an iterator for the object

    int _minlength:
        The minimum legal length [Optional]

    int _maxlength:
        The maximum legal length [Optional]

    iterable _allowed:
        A list of allowed item types [Optional]

    class _IndexError:
        The type of exception to be raise on invalid index [Optional]
    """

    _minlength = 0
    _maxlength = None
    _IndexError = IndexError

    ### Python initialization and list interface methods ###

    def __init__(self, *args, **kwargs):
        if not hasattr(self, '_getitem_internal'):
            self._getitem_internal = self._getitem_external

        if not hasattr(self, '_set_single'):
            self._set_single = self._set_single_rebuild
            self._assign_extended_slice = self._assign_extended_slice_rebuild

        super(ListMixin, self).__init__(*args, **kwargs)

    def __getitem__(self, index):
        "Gets the coordinates of the point(s) at the specified index/slice."
        if isinstance(index, slice):
            return [self._getitem_external(i) for i in xrange(*index.indices(len(self)))]
        else:
            index = self._checkindex(index)
            return self._getitem_external(index)

    def __delitem__(self, index):
        "Delete the point(s) at the specified index/slice."
        if not isinstance(index, (int, long, slice)):
            raise TypeError("%s is not a legal index" % index)

        # calculate new length and dimensions
        origLen     = len(self)
        if isinstance(index, (int, long)):
            index = self._checkindex(index)
            indexRange  = [index]
        else:
            indexRange  = range(*index.indices(origLen))

        newLen      = origLen - len(indexRange)
        newItems    = ( self._getitem_internal(i)
                        for i in xrange(origLen)
                        if i not in indexRange )

        self._rebuild(newLen, newItems)

    def __setitem__(self, index, val):
        "Sets the Geometry at the specified index."
        if isinstance(index, slice):
            self._set_slice(index, val)
        else:
            index = self._checkindex(index)
            self._check_allowed((val,))
            self._set_single(index, val)

    ### Public list interface Methods ###
    def append(self, val):
        "Standard list append method"
        self[len(self):] = [val]

    def extend(self, vals):
        "Standard list extend method"
        self[len(self):] = vals

    def insert(self, index, val):
        "Standard list insert method"
        if not isinstance(index, (int, long)):
            raise TypeError("%s is not a legal index" % index)
        self[index:index] = [val]

    def pop(self, index=-1):
        "Standard list pop method"
        result = self[index]
        del self[index]
        return result

    def index(self, val):
        "Standard list index method"
        for i in xrange(0, len(self)):
            if self[i] == val: return i
        raise ValueError('%s not found in object' % str(val))

    def remove(self, val):
        "Standard list remove method"
        del self[self.index(val)]

    def count(self, val):
        "Standard list count method"
        count = 0
        for i in self:
            if val == i: count += 1
        return count

    ### Private API routines unique to ListMixin ###

    def _rebuild(self, newLen, newItems):
        if newLen < self._minlength:
            raise ValueError('Must have at least %d items' % self._minlength)
        if self._maxlength is not None and newLen > self._maxlength:
            raise ValueError('Cannot have more than %d items' % self._maxlength)

        self._set_collection(newLen, newItems)

    def _set_single_rebuild(self, index, value):
        self._set_slice(slice(index, index + 1, 1), [value])

    def _checkindex(self, index, correct=True):
        length = len(self)
        if 0 <= index < length:
            return index
        if correct and -length <= index < 0:
            return index + length
        raise self._IndexError('invalid index: %s' % str(index))

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

        origLen     = len(self)
        valueList   = list(values)
        start, stop, step = index.indices(origLen)

        # CAREFUL: index.step and step are not the same!
        # step will never be None
        if index.step is None:
            self._assign_simple_slice(start, stop, valueList)
        else:
            self._assign_extended_slice(start, stop, step, valueList)

    def _assign_extended_slice_rebuild(self, start, stop, step, valueList):
        'Assign an extended slice by rebuilding entire list'
        indexList   = range(start, stop, step)
        # extended slice, only allow assigning slice of same size
        if len(valueList) != len(indexList):
            raise ValueError('attempt to assign sequence of size %d '
                             'to extended slice of size %d'
                             % (len(valueList), len(indexList)))

        # we're not changing the length of the sequence
        newLen  = len(self)
        newVals = dict(zip(indexList, valueList))
        def newItems():
            for i in xrange(newLen):
                if i in newVals:
                    yield newVals[i]
                else:
                    yield self._getitem_internal(i)

        self._rebuild(newLen, newItems())

    def _assign_extended_slice(self, start, stop, step, valueList):
        'Assign an extended slice by re-assigning individual items'
        indexList   = range(start, stop, step)
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
        newLen  = origLen - stop + start + len(valueList)
        def newItems():
            for i in xrange(origLen + 1):
                if i == start:
                    for val in valueList:
                        yield val

                if i < origLen:
                    if i < start or i >= stop:
                        yield self._getitem_internal(i)

        self._rebuild(newLen, newItems())
