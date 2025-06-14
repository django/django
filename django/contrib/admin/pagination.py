from django.contrib.admin.options import IncorrectLookupParameters
from django.core.paginator import InvalidPage

ALL_VAR = "all"
PAGE_VAR = "p"


class Pagination:
    def __init__(
        self,
        request,
        model,
        queryset,
        list_per_page,
        list_max_show_all,
        model_admin,
    ):
        self.model = model
        self.opts = model._meta
        self.list_per_page = list_per_page
        self.list_max_show_all = list_max_show_all
        self.model_admin = model_admin
        try:
            self.page_num = int(request.GET.get(PAGE_VAR, 1))
        except ValueError:
            self.page_num = 1
        self.show_all = ALL_VAR in request.GET
        self.params = request.GET.copy()
        self.queryset = queryset
        self.setup(request)

    def setup(self, request):
        paginator = self.model_admin.get_paginator(
            request, self.queryset, self.list_per_page
        )
        result_count = paginator.count
        can_show_all = result_count <= self.list_max_show_all
        multi_page = result_count > self.list_per_page

        self.result_count = result_count
        self.can_show_all = can_show_all
        self.multi_page = multi_page
        self.paginator = paginator

    def get_objects(self):
        if (self.show_all and self.can_show_all) or not self.multi_page:
            result_list = self.queryset._clone()
        else:
            try:
                result_list = self.paginator.page(self.page_num).object_list
            except InvalidPage:
                raise IncorrectLookupParameters
        return result_list
