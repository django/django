import operator

from django.core.exceptions import SuspiciousOperation
from django.core.paginator import InvalidPage
from django.db import models
from django.utils.datastructures import SortedDict
from django.utils.encoding import force_unicode, smart_str
from django.utils.translation import ugettext, ugettext_lazy
from django.utils.http import urlencode

from django.contrib.admin import FieldListFilter
from django.contrib.admin.options import IncorrectLookupParameters
from django.contrib.admin.util import quote, get_fields_from_path

# Changelist settings
ALL_VAR = 'all'
ORDER_VAR = 'o'
ORDER_TYPE_VAR = 'ot'
PAGE_VAR = 'p'
SEARCH_VAR = 'q'
TO_FIELD_VAR = 't'
IS_POPUP_VAR = 'pop'
ERROR_FLAG = 'e'

IGNORED_PARAMS = (
    ALL_VAR, ORDER_VAR, ORDER_TYPE_VAR, SEARCH_VAR, IS_POPUP_VAR, TO_FIELD_VAR)

# Text to display within change-list table cells if the value is blank.
EMPTY_CHANGELIST_VALUE = ugettext_lazy('(None)')

def field_needs_distinct(field):
    if ((hasattr(field, 'rel') and
         isinstance(field.rel, models.ManyToManyRel)) or
        (isinstance(field, models.related.RelatedObject) and
         not field.field.unique)):
         return True
    return False


class ChangeList(object):
    def __init__(self, request, model, list_display, list_display_links,
            list_filter, date_hierarchy, search_fields, list_select_related,
            list_per_page, list_max_show_all, list_editable, model_admin):
        self.model = model
        self.opts = model._meta
        self.lookup_opts = self.opts
        self.root_query_set = model_admin.queryset(request)
        self.list_display = list_display
        self.list_display_links = list_display_links
        self.list_filter = list_filter
        self.date_hierarchy = date_hierarchy
        self.search_fields = search_fields
        self.list_select_related = list_select_related
        self.list_per_page = list_per_page
        self.list_max_show_all = list_max_show_all
        self.model_admin = model_admin

        # Get search parameters from the query string.
        try:
            self.page_num = int(request.GET.get(PAGE_VAR, 0))
        except ValueError:
            self.page_num = 0
        self.show_all = ALL_VAR in request.GET
        self.is_popup = IS_POPUP_VAR in request.GET
        self.to_field = request.GET.get(TO_FIELD_VAR)
        self.params = dict(request.GET.items())
        if PAGE_VAR in self.params:
            del self.params[PAGE_VAR]
        if ERROR_FLAG in self.params:
            del self.params[ERROR_FLAG]

        if self.is_popup:
            self.list_editable = ()
        else:
            self.list_editable = list_editable
        self.ordering = self.get_ordering(request)
        self.query = request.GET.get(SEARCH_VAR, '')
        self.query_set = self.get_query_set(request)
        self.get_results(request)
        if self.is_popup:
            title = ugettext('Select %s')
        else:
            title = ugettext('Select %s to change')
        self.title = title % force_unicode(self.opts.verbose_name)
        self.pk_attname = self.lookup_opts.pk.attname

    def get_filters(self, request, use_distinct=False):
        filter_specs = []
        cleaned_params, use_distinct = self.get_lookup_params(use_distinct)
        if self.list_filter:
            for list_filter in self.list_filter:
                if callable(list_filter):
                    # This is simply a custom list filter class.
                    spec = list_filter(request, cleaned_params,
                        self.model, self.model_admin)
                else:
                    field_path = None
                    if isinstance(list_filter, (tuple, list)):
                        # This is a custom FieldListFilter class for a given field.
                        field, field_list_filter_class = list_filter
                    else:
                        # This is simply a field name, so use the default
                        # FieldListFilter class that has been registered for
                        # the type of the given field.
                        field, field_list_filter_class = list_filter, FieldListFilter.create
                    if not isinstance(field, models.Field):
                        field_path = field
                        field = get_fields_from_path(self.model, field_path)[-1]
                    spec = field_list_filter_class(field, request, cleaned_params,
                        self.model, self.model_admin, field_path=field_path)
                if spec and spec.has_output():
                    filter_specs.append(spec)
        return filter_specs, bool(filter_specs)

    def get_query_string(self, new_params=None, remove=None):
        if new_params is None: new_params = {}
        if remove is None: remove = []
        p = self.params.copy()
        for r in remove:
            for k in p.keys():
                if k.startswith(r):
                    del p[k]
        for k, v in new_params.items():
            if v is None:
                if k in p:
                    del p[k]
            else:
                p[k] = v
        return '?%s' % urlencode(p)

    def get_results(self, request):
        paginator = self.model_admin.get_paginator(request, self.query_set, self.list_per_page)
        # Get the number of objects, with admin filters applied.
        result_count = paginator.count

        # Get the total number of objects, with no admin filters applied.
        # Perform a slight optimization: Check to see whether any filters were
        # given. If not, use paginator.hits to calculate the number of objects,
        # because we've already done paginator.hits and the value is cached.
        if not self.query_set.query.where:
            full_result_count = result_count
        else:
            full_result_count = self.root_query_set.count()

        can_show_all = result_count <= self.list_max_show_all
        multi_page = result_count > self.list_per_page

        # Get the list of objects to display on this page.
        if (self.show_all and can_show_all) or not multi_page:
            result_list = self.query_set._clone()
        else:
            try:
                result_list = paginator.page(self.page_num+1).object_list
            except InvalidPage:
                raise IncorrectLookupParameters

        self.result_count = result_count
        self.full_result_count = full_result_count
        self.result_list = result_list
        self.can_show_all = can_show_all
        self.multi_page = multi_page
        self.paginator = paginator

    def _get_default_ordering(self):
        ordering = []
        if self.model_admin.ordering:
            ordering = self.model_admin.ordering
        elif self.lookup_opts.ordering:
            ordering = self.lookup_opts.ordering
        return ordering

    def get_ordering(self, request):
        params = self.params
        # For ordering, first check the if exists the "get_ordering" method
        # in model admin, then check "ordering" parameter in the admin
        # options, then check the object's default ordering. Finally, a
        # manually-specified ordering from the query string overrides anything.
        ordering = self.model_admin.get_ordering(request) or self._get_default_ordering()

        if ORDER_VAR in params:
            # Clear ordering and used params
            ordering = []
            order_params = params[ORDER_VAR].split('.')
            for p in order_params:
                try:
                    none, pfx, idx = p.rpartition('-')
                    field_name = self.list_display[int(idx)]
                    try:
                        f = self.lookup_opts.get_field(field_name)
                    except models.FieldDoesNotExist:
                        # See whether field_name is a name of a non-field
                        # that allows sorting.
                        try:
                            if callable(field_name):
                                attr = field_name
                            elif hasattr(self.model_admin, field_name):
                                attr = getattr(self.model_admin, field_name)
                            else:
                                attr = getattr(self.model, field_name)
                            field_name = attr.admin_order_field
                        except AttributeError:
                            continue # No 'admin_order_field', skip it
                    else:
                        field_name = f.name

                    ordering.append(pfx + field_name)

                except (IndexError, ValueError):
                    continue # Invalid ordering specified, skip it.

        return ordering

    def get_ordering_field_columns(self):
        # Returns a SortedDict of ordering field column numbers and asc/desc

        # We must cope with more than one column having the same underlying sort
        # field, so we base things on column numbers.
        ordering = self._get_default_ordering()
        ordering_fields = SortedDict()
        if ORDER_VAR not in self.params:
            # for ordering specified on ModelAdmin or model Meta, we don't know
            # the right column numbers absolutely, because there might be more
            # than one column associated with that ordering, so we guess.
            for field in ordering:
                if field.startswith('-'):
                    field = field[1:]
                    order_type = 'desc'
                else:
                    order_type = 'asc'
                index = None
                try:
                    # Search for simply field name first
                    index = list(self.list_display).index(field)
                except ValueError:
                    # No match, but there might be a match if we take into
                    # account 'admin_order_field'
                    for _index, attr in enumerate(self.list_display):
                        if getattr(attr, 'admin_order_field', '') == field:
                            index = _index
                            break
                if index is not None:
                    ordering_fields[index] = order_type
        else:
            for p in self.params[ORDER_VAR].split('.'):
                none, pfx, idx = p.rpartition('-')
                try:
                    idx = int(idx)
                except ValueError:
                    continue # skip it
                ordering_fields[idx] = 'desc' if pfx == '-' else 'asc'
        return ordering_fields

    def get_lookup_params(self, use_distinct=False):
        lookup_params = self.params.copy() # a dictionary of the query string

        for ignored in IGNORED_PARAMS:
            if ignored in lookup_params:
                del lookup_params[ignored]

        for key, value in lookup_params.items():
            if not isinstance(key, str):
                # 'key' will be used as a keyword argument later, so Python
                # requires it to be a string.
                del lookup_params[key]
                lookup_params[smart_str(key)] = value

            field = None
            if not use_distinct:
                # Check if it's a relationship that might return more than one
                # instance
                field_name = key.split('__', 1)[0]
                try:
                    field = self.lookup_opts.get_field_by_name(field_name)[0]
                    use_distinct = field_needs_distinct(field)
                except models.FieldDoesNotExist:
                    # It might be a custom NonFieldFilter
                    pass

            # if key ends with __in, split parameter into separate values
            if key.endswith('__in'):
                value = value.split(',')
                lookup_params[key] = value

            # if key ends with __isnull, special case '' and false
            if key.endswith('__isnull'):
                if value.lower() in ('', 'false'):
                    value = False
                else:
                    value = True
                lookup_params[key] = value

            if field and not self.model_admin.lookup_allowed(key, value):
                raise SuspiciousOperation("Filtering by %s not allowed" % key)

        return lookup_params, use_distinct

    def get_query_set(self, request):
        lookup_params, use_distinct = self.get_lookup_params(use_distinct=False)
        self.filter_specs, self.has_filters = self.get_filters(request, use_distinct)

        try:
            # First, let every list filter modify the qs and params to its
            # liking.
            qs = self.root_query_set
            for filter_spec in self.filter_specs:
                new_qs = filter_spec.queryset(request, qs)
                if new_qs is not None:
                    qs = new_qs
                    for param in filter_spec.used_params():
                        try:
                            del lookup_params[param]
                        except KeyError:
                            pass

            # Then, apply the remaining lookup parameters from the query string
            # (i.e. those that haven't already been processed by the filters).
            qs = qs.filter(**lookup_params)
        except Exception, e:
            # Naked except! Because we don't have any other way of validating
            # "lookup_params". They might be invalid if the keyword arguments
            # are incorrect, or if the values are not in the correct type, so
            # we might get FieldError, ValueError, ValicationError, or ? from a
            # custom field that raises yet something else when handed
            # impossible data.
            raise IncorrectLookupParameters(e)

        # Use select_related() if one of the list_display options is a field
        # with a relationship and the provided queryset doesn't already have
        # select_related defined.
        if not qs.query.select_related:
            if self.list_select_related:
                qs = qs.select_related()
            else:
                for field_name in self.list_display:
                    try:
                        field = self.lookup_opts.get_field(field_name)
                    except models.FieldDoesNotExist:
                        pass
                    else:
                        if isinstance(field.rel, models.ManyToOneRel):
                            qs = qs.select_related()
                            break

        # Set ordering.
        if self.ordering:
            qs = qs.order_by(*self.ordering)

        # Apply keyword searches.
        def construct_search(field_name):
            if field_name.startswith('^'):
                return "%s__istartswith" % field_name[1:]
            elif field_name.startswith('='):
                return "%s__iexact" % field_name[1:]
            elif field_name.startswith('@'):
                return "%s__search" % field_name[1:]
            else:
                return "%s__icontains" % field_name

        if self.search_fields and self.query:
            orm_lookups = [construct_search(str(search_field))
                           for search_field in self.search_fields]
            for bit in self.query.split():
                or_queries = [models.Q(**{orm_lookup: bit})
                              for orm_lookup in orm_lookups]
                qs = qs.filter(reduce(operator.or_, or_queries))
            if not use_distinct:
                for search_spec in orm_lookups:
                    field_name = search_spec.split('__', 1)[0]
                    f = self.lookup_opts.get_field_by_name(field_name)[0]
                    if field_needs_distinct(f):
                        use_distinct = True
                        break

        if use_distinct:
            return qs.distinct()
        else:
            return qs

    def url_for_result(self, result):
        return "%s/" % quote(getattr(result, self.pk_attname))
