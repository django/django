from django.core.paginator import Page, Paginator


class ValidAdjacentNumsPage(Page):

    def next_page_number(self):
        if not self.has_next():
            return None
        return super(ValidAdjacentNumsPage, self).next_page_number()

    def previous_page_number(self):
        if not self.has_previous():
            return None
        return super(ValidAdjacentNumsPage, self).previous_page_number()


class ValidAdjacentNumsPaginator(Paginator):

    def _get_page(self, *args, **kwargs):
        return ValidAdjacentNumsPage(*args, **kwargs)
