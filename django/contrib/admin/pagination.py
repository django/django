from django.contrib.admin.options import IncorrectLookupParameters
from django.core.paginator import InvalidPage
from django.template.defaulttags import querystring
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe

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
        self.filter_params = request.GET.copy()
        self.queryset = queryset
        self.setup(request)

    @property
    def pagination_required(self):
        return self.multi_page and not (self.show_all and self.can_show_all)

    @property
    def page_range(self):
        return (
            self.paginator.get_elided_page_range(self.page_num)
            if self.pagination_required
            else []
        )

    @property
    def all_rendered_pages(self):
        """
        HTML for all the pages in the pagination.
        """
        return format_html_join(
            "",
            "{}",
            ((self.render_page(i),) for i in self.page_range),
        )

    @property
    def show_all_url(self):
        """
        Return the query string to display all objects.
        """
        if self.can_show_all and not self.show_all and self.multi_page:
            return querystring(None, self.filter_params, **{ALL_VAR: ""})

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

    def render_page(self, i):
        """
        Generate an individual page index link in a paginated list.
        """
        if i == self.paginator.ELLIPSIS:
            return format_html("{} ", self.paginator.ELLIPSIS)
        if i == self.page_num:
            return format_html('<span class="this-page">{}</span> ', i)
        return format_html(
            '<a href="{}"{}>{}</a> ',
            querystring(None, self.filter_params, **{PAGE_VAR: i}),
            mark_safe(' class="end"' if i == self.paginator.num_pages else ""),
            i,
        )

    def get_objects(self):
        if (self.show_all and self.can_show_all) or not self.multi_page:
            result_list = self.queryset._clone()
        else:
            try:
                result_list = self.paginator.page(self.page_num).object_list
            except InvalidPage:
                raise IncorrectLookupParameters
        return result_list

    def pagination_context(self, **kwargs):
        """
        Return context data for pagination rendering.
        """
        return {
            "pagination": self,
            "pagination_required": self.pagination_required,
            "show_all_url": self.show_all_url,
            "ALL_VAR": ALL_VAR,
            "1": 1,
            **kwargs,
        }
