from django.core.paginator import AsyncPage, AsyncPaginator, Page, Paginator


class ValidAdjacentNumsPage(Page):
    def next_page_number(self):
        if not self.has_next():
            return None
        return super().next_page_number()

    def previous_page_number(self):
        if not self.has_previous():
            return None
        return super().previous_page_number()


class ValidAdjacentNumsPaginator(Paginator):
    def _get_page(self, *args, **kwargs):
        return ValidAdjacentNumsPage(*args, **kwargs)


class AsyncValidAdjacentNumsPage(AsyncPage):
    async def anext_page_number(self):
        if not await self.ahas_next():
            return None
        return await super().anext_page_number()

    async def aprevious_page_number(self):
        if not await self.ahas_previous():
            return None
        return await super().aprevious_page_number()


class AsyncValidAdjacentNumsPaginator(AsyncPaginator):
    def _get_page(self, *args, **kwargs):
        return AsyncValidAdjacentNumsPage(*args, **kwargs)
