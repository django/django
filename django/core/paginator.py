import collections
from math import ceil

from django.utils import six

DOT = '.'


class InvalidPage(Exception):
    pass


class PageNotAnInteger(InvalidPage):
    pass


class EmptyPage(InvalidPage):
    pass


class Paginator(object):

    def __init__(self, object_list, per_page, orphans=0,
                 allow_empty_first_page=True):
        self.object_list = object_list
        self.per_page = int(per_page)
        self.orphans = int(orphans)
        self.allow_empty_first_page = allow_empty_first_page
        self._num_pages = self._count = None

    def validate_number(self, number):
        """
        Validates the given 1-based page number.
        """
        try:
            number = int(number)
        except (TypeError, ValueError):
            raise PageNotAnInteger('That page number is not an integer')
        if number < 1:
            raise EmptyPage('That page number is less than 1')
        if number > self.num_pages:
            if number == 1 and self.allow_empty_first_page:
                pass
            else:
                raise EmptyPage('That page contains no results')
        return number

    def page(self, number):
        """
        Returns a Page object for the given 1-based page number.
        """
        number = self.validate_number(number)
        bottom = (number - 1) * self.per_page
        top = bottom + self.per_page
        if top + self.orphans >= self.count:
            top = self.count
        return self._get_page(self.object_list[bottom:top], number, self)

    def _get_page(self, *args, **kwargs):
        """
        Returns an instance of a single page.

        This hook can be used by subclasses to use an alternative to the
        standard :cls:`Page` object.
        """
        return Page(*args, **kwargs)

    def _get_count(self):
        """
        Returns the total number of objects, across all pages.
        """
        if self._count is None:
            try:
                self._count = self.object_list.count()
            except (AttributeError, TypeError):
                # AttributeError if object_list has no count() method.
                # TypeError if object_list.count() requires arguments
                # (i.e. is of type list).
                self._count = len(self.object_list)
        return self._count
    count = property(_get_count)

    def _get_num_pages(self):
        """
        Returns the total number of pages.
        """
        if self._num_pages is None:
            if self.count == 0 and not self.allow_empty_first_page:
                self._num_pages = 0
            else:
                hits = max(1, self.count - self.orphans)
                self._num_pages = int(ceil(hits / float(self.per_page)))
        return self._num_pages
    num_pages = property(_get_num_pages)

    def _get_page_range(self):
        """
        Returns a 1-based range of pages for iterating through within
        a template for loop.
        """
        return six.moves.range(1, self.num_pages + 1)
    page_range = property(_get_page_range)


QuerySetPaginator = Paginator   # For backwards-compatibility.


class EllipsisPaginator(Paginator):
    """
    Paginator with a special method, which builds page range in a compact form - does not
    display whole range if it does not fit into given size. Instead of full form, it displays
    beginning, middle and end parts of range with ellipsis between them, e.g.:
    1, 2, ..., 40, 41, 42, 43, 44, 45, 46, ..., 49, 50. Originally used in `django.contrib.admin`.
    """

    def __init__(self, *args, **kwargs):
        self.on_each_side = kwargs.pop('on_each_side', 3)
        self.on_ends = kwargs.pop('on_ends', 2)
        self.max_pages_num = kwargs.pop('max_pages_num', 10)
        super(EllipsisPaginator, self).__init__(*args, **kwargs)

    def get_ellipsed_page_range(self, page_num=1):
        if self.num_pages > self.max_pages_num:
            # Insert "smart" pagination links, so that there are always `on_ends`
            # links at either end of the list of pages, and there are always
            # `on_each_side` links at either end of the "current page" link.
            page_range = []
            if page_num > (self.on_each_side + self.on_ends + 1):
                page_range.extend(six.moves.range(1, self.on_ends + 1))
                page_range.append(DOT)
                page_range.extend(six.moves.range(page_num - self.on_each_side, page_num + 1))
            else:
                page_range.extend(six.moves.range(1, page_num + 1))

            if page_num < (self.num_pages - self.on_each_side - self.on_ends):
                page_range.extend(six.moves.range(page_num + 1, page_num + self.on_each_side + 1))
                page_range.append(DOT)
                page_range.extend(six.moves.range(self.num_pages - self.on_ends + 1, self.num_pages + 1))
            else:
                page_range.extend(six.moves.range(page_num + 1, self.num_pages + 1))
        else:
            page_range = self.page_range
        return page_range


class Page(collections.Sequence):

    def __init__(self, object_list, number, paginator):
        self.object_list = object_list
        self.number = number
        self.paginator = paginator

    def __repr__(self):
        return '<Page %s of %s>' % (self.number, self.paginator.num_pages)

    def __len__(self):
        return len(self.object_list)

    def __getitem__(self, index):
        if not isinstance(index, (slice,) + six.integer_types):
            raise TypeError
        # The object_list is converted to a list so that if it was a QuerySet
        # it won't be a database hit per __getitem__.
        if not isinstance(self.object_list, list):
            self.object_list = list(self.object_list)
        return self.object_list[index]

    def has_next(self):
        return self.number < self.paginator.num_pages

    def has_previous(self):
        return self.number > 1

    def has_other_pages(self):
        return self.has_previous() or self.has_next()

    def next_page_number(self):
        return self.paginator.validate_number(self.number + 1)

    def previous_page_number(self):
        return self.paginator.validate_number(self.number - 1)

    def start_index(self):
        """
        Returns the 1-based index of the first object on this page,
        relative to total objects in the paginator.
        """
        # Special case, return zero if no items.
        if self.paginator.count == 0:
            return 0
        return (self.paginator.per_page * (self.number - 1)) + 1

    def end_index(self):
        """
        Returns the 1-based index of the last object on this page,
        relative to total objects found (hits).
        """
        # Special case for the last page because there can be orphans.
        if self.number == self.paginator.num_pages:
            return self.paginator.count
        return self.number * self.paginator.per_page
