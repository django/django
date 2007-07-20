class InvalidPage(Exception):
    pass

class ObjectPaginator(object):
    """
    This class makes pagination easy. Feed it a QuerySet or list, plus the number
    of objects you want on each page. Then read the hits and pages properties to
    see how many pages it involves. Call get_page with a page number (starting
    at 0) to get back a list of objects for that page.

    Finally, check if a page number has a next/prev page using
    has_next_page(page_number) and has_previous_page(page_number).
    
    Use orphans to avoid small final pages. For example:
    13 records, num_per_page=10, orphans=2 --> pages==2, len(self.get_page(0))==10
    12 records, num_per_page=10, orphans=2 --> pages==1, len(self.get_page(0))==12
    """
    def __init__(self, query_set, num_per_page, orphans=0):
        self.query_set = query_set
        self.num_per_page = num_per_page
        self.orphans = orphans
        self._hits = self._pages = None

    def validate_page_number(self, page_number):
        try:
            page_number = int(page_number)
        except ValueError:
            raise InvalidPage
        if page_number < 0 or page_number > self.pages - 1:
            raise InvalidPage
        return page_number

    def get_page(self, page_number):
        page_number = self.validate_page_number(page_number)
        bottom = page_number * self.num_per_page
        top = bottom + self.num_per_page
        if top + self.orphans >= self.hits:
            top = self.hits
        return self.query_set[bottom:top]

    def has_next_page(self, page_number):
        "Does page $page_number have a 'next' page?"
        return page_number < self.pages - 1

    def has_previous_page(self, page_number):
        return page_number > 0

    def first_on_page(self, page_number):
        """
        Returns the 1-based index of the first object on the given page,
        relative to total objects found (hits).
        """
        page_number = self.validate_page_number(page_number)
        return (self.num_per_page * page_number) + 1

    def last_on_page(self, page_number):
        """
        Returns the 1-based index of the last object on the given page,
        relative to total objects found (hits).
        """
        page_number = self.validate_page_number(page_number)
        page_number += 1   # 1-base
        if page_number == self.pages:
            return self.hits
        return page_number * self.num_per_page

    def _get_hits(self):
        if self._hits is None:
            # Try .count() or fall back to len().
            try:
                self._hits = int(self.query_set.count())
            except (AttributeError, TypeError, ValueError):
                # AttributeError if query_set has no object count.
                # TypeError if query_set.count() required arguments.
                # ValueError if int() fails.
                self._hits = len(self.query_set)
        return self._hits

    def _get_pages(self):
        if self._pages is None:
            hits = (self.hits - 1 - self.orphans)
            if hits < 1:
                hits = 0
            self._pages = hits // self.num_per_page + 1
        return self._pages

    hits = property(_get_hits)
    pages = property(_get_pages)
