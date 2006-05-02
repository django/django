from copy import copy
from math import ceil

class InvalidPage(Exception):
    pass

class ObjectPaginator:
    """
    This class makes pagination easy. Feed it a QuerySet, plus the number of
    objects you want on each page. Then read the hits and pages properties to
    see how many pages it involves. Call get_page with a page number (starting
    at 0) to get back a list of objects for that page.

    Finally, check if a page number has a next/prev page using
    has_next_page(page_number) and has_previous_page(page_number).
    """
    def __init__(self, query_set, num_per_page):
        self.query_set = query_set
        self.num_per_page = num_per_page
        self._hits, self._pages = None, None
        self._has_next = {} # Caches page_number -> has_next_boolean

    def get_page(self, page_number):
        try:
            page_number = int(page_number)
        except ValueError:
            raise InvalidPage
        if page_number < 0:
            raise InvalidPage

        # Retrieve one extra record, and check for the existence of that extra
        # record to determine whether there's a next page.
        limit = self.num_per_page + 1
        offset = page_number * self.num_per_page

        object_list = list(self.query_set[offset:offset+limit])

        if not object_list:
            raise InvalidPage

        self._has_next[page_number] = (len(object_list) > self.num_per_page)
        return object_list[:self.num_per_page]

    def has_next_page(self, page_number):
        "Does page $page_number have a 'next' page?"
        if not self._has_next.has_key(page_number):
            if self._pages is None:
                offset = (page_number + 1) * self.num_per_page
                self._has_next[page_number] = len(self.query_set[offset:offset+1]) > 0
            else:
                self._has_next[page_number] = page_number < (self.pages - 1)
        return self._has_next[page_number]

    def has_previous_page(self, page_number):
        return page_number > 0

    def _get_hits(self):
        if self._hits is None:
            self._hits = self.query_set.count()
        return self._hits

    def _get_pages(self):
        if self._pages is None:
            self._pages = int(ceil(self.hits / float(self.num_per_page)))
        return self._pages

    hits = property(_get_hits)
    pages = property(_get_pages)
