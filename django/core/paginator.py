from copy import copy
from math import ceil

class InvalidPage(Exception):
    pass

class ObjectPaginator:
    """
    This class makes pagination easy. Feed it a manager (an object with
    get_count() and get_list() methods) or a model which has a default manager,
    and a dictionary of arguments to be passed to those methods, plus the 
    number of objects you want on each page. Then read the hits and pages 
    properties to see how many pages it involves. Call get_page with a page 
    number (starting at 0) to get back a list of objects for that page.
    
    Finally, check if a page number has a next/prev page using
    has_next_page(page_number) and has_previous_page(page_number).
    """
    def __init__(self, manager_or_model, args, num_per_page, count_method='get_count', list_method='get_list'):
        if hasattr(manager_or_model, '_default_manager'):
            manager = manager_or_model._default_manager
        else:
            manager = manager_or_model
        self.manager, self.args = manager, args
        self.num_per_page = num_per_page
        self.count_method, self.list_method = count_method, list_method
        self._hits, self._pages = None, None
        self._has_next = {} # Caches page_number -> has_next_boolean

    def get_page(self, page_number):
        try:
            page_number = int(page_number)
        except ValueError:
            raise InvalidPage
        if page_number < 0:
            raise InvalidPage
        args = copy(self.args)
        args['offset'] = page_number * self.num_per_page
        # Retrieve one extra record, and check for the existence of that extra
        # record to determine whether there's a next page.
        args['limit'] = self.num_per_page + 1
        object_list = getattr(self.manager, self.list_method)(**args)
        if not object_list:
            raise InvalidPage
        self._has_next[page_number] = (len(object_list) > self.num_per_page)
        return object_list[:self.num_per_page]

    def has_next_page(self, page_number):
        "Does page $page_number have a 'next' page?"
        if not self._has_next.has_key(page_number):
            if self._pages is None:
                args = copy(self.args)
                args['offset'] = (page_number + 1) * self.num_per_page
                args['limit'] = 1
                object_list = getattr(self.manager, self.list_method)(**args)
                self._has_next[page_number] = (object_list != [])
            else:
                self._has_next[page_number] = page_number < (self.pages - 1)
        return self._has_next[page_number]

    def has_previous_page(self, page_number):
        return page_number > 0

    def _get_hits(self):
        if self._hits is None:
            order_args = copy(self.args)
            if order_args.has_key('order_by'):
                del order_args['order_by']
            if order_args.has_key('select_related'):
                del order_args['select_related']
            self._hits = getattr(self.manager, self.count_method)(**order_args)
        return self._hits

    def _get_pages(self):
        if self._pages is None:
            self._pages = int(ceil(self.hits / float(self.num_per_page)))
        return self._pages

    hits = property(_get_hits)
    pages = property(_get_pages)
