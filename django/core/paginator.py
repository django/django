class InvalidPage(Exception):
    pass

class Paginator(object):
    def __init__(self, object_list, per_page, orphans=0, allow_empty_first_page=True):
        self.object_list = object_list
        self.per_page = per_page
        self.orphans = orphans
        self.allow_empty_first_page = allow_empty_first_page
        self._num_pages = self._count = None

    def validate_number(self, number):
        "Validates the given 1-based page number."
        try:
            number = int(number)
        except ValueError:
            raise InvalidPage('That page number is not an integer')
        if number < 1:
            raise InvalidPage('That page number is less than 1')
        if number > self.num_pages:
            if number == 1 and self.allow_empty_first_page:
                pass
            else:
                raise InvalidPage('That page contains no results')
        return number

    def page(self, number):
        "Returns a Page object for the given 1-based page number."
        number = self.validate_number(number)
        bottom = (number - 1) * self.per_page
        top = bottom + self.per_page
        if top + self.orphans >= self.count:
            top = self.count
        return Page(self.object_list[bottom:top], number, self)

    def _get_count(self):
        "Returns the total number of objects, across all pages."
        if self._count is None:
            from django.db.models.query import QuerySet
            if isinstance(self.object_list, QuerySet):
                self._count = self.object_list.count()
            else:
                self._count = len(self.object_list)
        return self._count
    count = property(_get_count)

    def _get_num_pages(self):
        "Returns the total number of pages."
        if self._num_pages is None:
            hits = self.count - 1 - self.orphans
            if hits < 1:
                hits = 0
            if hits == 0 and not self.allow_empty_first_page:
                self._num_pages = 0
            else:
                self._num_pages = hits // self.per_page + 1
        return self._num_pages
    num_pages = property(_get_num_pages)

    def _get_page_range(self):
        """
        Returns a 1-based range of pages for iterating through within
        a template for loop.
        """
        return range(1, self.num_pages + 1)
    page_range = property(_get_page_range)

QuerySetPaginator = Paginator # For backwards-compatibility.

class Page(object):
    def __init__(self, object_list, number, paginator):
        self.object_list = object_list
        self.number = number
        self.paginator = paginator

    def __repr__(self):
        return '<Page %s of %s>' % (self.number, self.paginator.num_pages)

    def has_next(self):
        return self.number < self.paginator.num_pages

    def has_previous(self):
        return self.number > 1

    def has_other_pages(self):
        return self.has_previous() or self.has_next()

    def next_page_number(self):
        return self.number + 1

    def previous_page_number(self):
        return self.number - 1

    def start_index(self):
        """
        Returns the 1-based index of the first object on this page,
        relative to total objects in the paginator.
        """
        return (self.paginator.per_page * (self.number - 1)) + 1

    def end_index(self):
        """
        Returns the 1-based index of the last object on this page,
        relative to total objects found (hits).
        """
        if self.number == self.paginator.num_pages:
            return self.paginator.count
        return self.number * self.paginator.per_page

class ObjectPaginator(Paginator):
    """
    Legacy ObjectPaginator class, for backwards compatibility.

    Note that each method on this class that takes page_number expects a
    zero-based page number, whereas the new API (Paginator/Page) uses one-based
    page numbers.
    """
    def __init__(self, query_set, num_per_page, orphans=0):
        Paginator.__init__(self, query_set, num_per_page, orphans)
        import warnings
        warnings.warn("The ObjectPaginator is deprecated. Use django.core.paginator.Paginator instead.", DeprecationWarning)

        # Keep these attributes around for backwards compatibility.
        self.query_set = query_set
        self.num_per_page = num_per_page
        self._hits = self._pages = None

    def validate_page_number(self, page_number):
        try:
            page_number = int(page_number) + 1
        except ValueError:
            raise InvalidPage
        return self.validate_number(page_number)

    def get_page(self, page_number):
        try:
            page_number = int(page_number) + 1
        except ValueError:
            raise InvalidPage
        return self.page(page_number).object_list

    def has_next_page(self, page_number):
        return page_number < self.pages - 1

    def has_previous_page(self, page_number):
        return page_number > 0

    def first_on_page(self, page_number):
        """
        Returns the 1-based index of the first object on the given page,
        relative to total objects found (hits).
        """
        page_number = self.validate_page_number(page_number)
        return (self.num_per_page * (page_number - 1)) + 1

    def last_on_page(self, page_number):
        """
        Returns the 1-based index of the last object on the given page,
        relative to total objects found (hits).
        """
        page_number = self.validate_page_number(page_number)
        if page_number == self.num_pages:
            return self.count
        return page_number * self.num_per_page

    def _get_count(self):
        # The old API allowed for self.object_list to be either a QuerySet or a
        # list. Here, we handle both.
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

    # The old API called it "hits" instead of "count".
    hits = count

    # The old API called it "pages" instead of "num_pages".
    pages = Paginator.num_pages
