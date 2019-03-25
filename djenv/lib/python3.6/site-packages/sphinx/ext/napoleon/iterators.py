# -*- coding: utf-8 -*-
"""
    sphinx.ext.napoleon.iterators
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


    A collection of helpful iterators.


    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import collections

if False:
    # For type annotation
    from typing import Any, Iterable  # NOQA


class peek_iter(object):
    """An iterator object that supports peeking ahead.

    Parameters
    ----------
    o : iterable or callable
        `o` is interpreted very differently depending on the presence of
        `sentinel`.

        If `sentinel` is not given, then `o` must be a collection object
        which supports either the iteration protocol or the sequence protocol.

        If `sentinel` is given, then `o` must be a callable object.

    sentinel : any value, optional
        If given, the iterator will call `o` with no arguments for each
        call to its `next` method; if the value returned is equal to
        `sentinel`, :exc:`StopIteration` will be raised, otherwise the
        value will be returned.

    See Also
    --------
    `peek_iter` can operate as a drop in replacement for the built-in
    `iter <https://docs.python.org/3/library/functions.html#iter>`_ function.

    Attributes
    ----------
    sentinel
        The value used to indicate the iterator is exhausted. If `sentinel`
        was not given when the `peek_iter` was instantiated, then it will
        be set to a new object instance: ``object()``.

    """
    def __init__(self, *args):
        # type: (Any) -> None
        """__init__(o, sentinel=None)"""
        self._iterable = iter(*args)        # type: Iterable
        self._cache = collections.deque()   # type: collections.deque
        if len(args) == 2:
            self.sentinel = args[1]
        else:
            self.sentinel = object()

    def __iter__(self):
        # type: () -> peek_iter
        return self

    def __next__(self, n=None):
        # type: (int) -> Any
        # note: prevent 2to3 to transform self.next() in next(self) which
        # causes an infinite loop !
        return getattr(self, 'next')(n)

    def _fillcache(self, n):
        # type: (int) -> None
        """Cache `n` items. If `n` is 0 or None, then 1 item is cached."""
        if not n:
            n = 1
        try:
            while len(self._cache) < n:
                self._cache.append(next(self._iterable))  # type: ignore
        except StopIteration:
            while len(self._cache) < n:
                self._cache.append(self.sentinel)

    def has_next(self):
        # type: () -> bool
        """Determine if iterator is exhausted.

        Returns
        -------
        bool
            True if iterator has more items, False otherwise.

        Note
        ----
        Will never raise :exc:`StopIteration`.

        """
        return self.peek() != self.sentinel

    def next(self, n=None):
        # type: (int) -> Any
        """Get the next item or `n` items of the iterator.

        Parameters
        ----------
        n : int or None
            The number of items to retrieve. Defaults to None.

        Returns
        -------
        item or list of items
            The next item or `n` items of the iterator. If `n` is None, the
            item itself is returned. If `n` is an int, the items will be
            returned in a list. If `n` is 0, an empty list is returned.

        Raises
        ------
        StopIteration
            Raised if the iterator is exhausted, even if `n` is 0.

        """
        self._fillcache(n)
        if not n:
            if self._cache[0] == self.sentinel:
                raise StopIteration
            if n is None:
                result = self._cache.popleft()
            else:
                result = []
        else:
            if self._cache[n - 1] == self.sentinel:
                raise StopIteration
            result = [self._cache.popleft() for i in range(n)]
        return result

    def peek(self, n=None):
        # type: (int) -> Any
        """Preview the next item or `n` items of the iterator.

        The iterator is not advanced when peek is called.

        Returns
        -------
        item or list of items
            The next item or `n` items of the iterator. If `n` is None, the
            item itself is returned. If `n` is an int, the items will be
            returned in a list. If `n` is 0, an empty list is returned.

            If the iterator is exhausted, `peek_iter.sentinel` is returned,
            or placed as the last item in the returned list.

        Note
        ----
        Will never raise :exc:`StopIteration`.

        """
        self._fillcache(n)
        if n is None:
            result = self._cache[0]
        else:
            result = [self._cache[i] for i in range(n)]
        return result


class modify_iter(peek_iter):
    """An iterator object that supports modifying items as they are returned.

    Parameters
    ----------
    o : iterable or callable
        `o` is interpreted very differently depending on the presence of
        `sentinel`.

        If `sentinel` is not given, then `o` must be a collection object
        which supports either the iteration protocol or the sequence protocol.

        If `sentinel` is given, then `o` must be a callable object.

    sentinel : any value, optional
        If given, the iterator will call `o` with no arguments for each
        call to its `next` method; if the value returned is equal to
        `sentinel`, :exc:`StopIteration` will be raised, otherwise the
        value will be returned.

    modifier : callable, optional
        The function that will be used to modify each item returned by the
        iterator. `modifier` should take a single argument and return a
        single value. Defaults to ``lambda x: x``.

        If `sentinel` is not given, `modifier` must be passed as a keyword
        argument.

    Attributes
    ----------
    modifier : callable
        `modifier` is called with each item in `o` as it is iterated. The
        return value of `modifier` is returned in lieu of the item.

        Values returned by `peek` as well as `next` are affected by
        `modifier`. However, `modify_iter.sentinel` is never passed through
        `modifier`; it will always be returned from `peek` unmodified.

    Example
    -------
    >>> a = ["     A list    ",
    ...      "   of strings  ",
    ...      "      with     ",
    ...      "      extra    ",
    ...      "   whitespace. "]
    >>> modifier = lambda s: s.strip().replace('with', 'without')
    >>> for s in modify_iter(a, modifier=modifier):
    ...   print('"%s"' % s)
    "A list"
    "of strings"
    "without"
    "extra"
    "whitespace."

    """
    def __init__(self, *args, **kwargs):
        # type: (Any, Any) -> None
        """__init__(o, sentinel=None, modifier=lambda x: x)"""
        if 'modifier' in kwargs:
            self.modifier = kwargs['modifier']
        elif len(args) > 2:
            self.modifier = args[2]
            args = args[:2]
        else:
            self.modifier = lambda x: x
        if not callable(self.modifier):
            raise TypeError('modify_iter(o, modifier): '
                            'modifier must be callable')
        super(modify_iter, self).__init__(*args)

    def _fillcache(self, n):
        # type: (int) -> None
        """Cache `n` modified items. If `n` is 0 or None, 1 item is cached.

        Each item returned by the iterator is passed through the
        `modify_iter.modified` function before being cached.

        """
        if not n:
            n = 1
        try:
            while len(self._cache) < n:
                self._cache.append(self.modifier(next(self._iterable)))  # type: ignore
        except StopIteration:
            while len(self._cache) < n:
                self._cache.append(self.sentinel)
