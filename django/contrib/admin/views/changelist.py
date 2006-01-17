from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.admin.views.main import get_model_and_app
from django.contrib.admin.filterspecs import FilterSpec
from django.db import models
from django.db.models.query import handle_legacy_orderlist
from django.http import HttpResponse, HttpResponseRedirect
from django.core.paginator import ObjectPaginator, InvalidPage
from django.template import RequestContext as Context
from django.core.extensions import render_to_response
from django.utils.dates import MONTHS

# The system will display a "Show all" link only if the total result count
# is less than or equal to this setting.
MAX_SHOW_ALL_ALLOWED = 200

DEFAULT_RESULTS_PER_PAGE = 100

ALL_VAR = 'all'
ORDER_VAR = 'o'
ORDER_TYPE_VAR = 'ot'
PAGE_VAR = 'p'
SEARCH_VAR = 'q'
IS_POPUP_VAR = 'pop'

# Text to display within changelist table cells if the value is blank.
EMPTY_CHANGELIST_VALUE = '(None)'

class IncorrectLookupParameters(Exception):
    pass

class ChangeList(object):
    def __init__(self, request, path):
        self.resolve_model(path, request)
        self.get_search_parameters(request)
        self.get_ordering()
        self.query = request.GET.get(SEARCH_VAR, '')
        self.get_lookup_params()
        self.get_results(request)
        self.title = (self.is_popup
                      and _('Select %s') % self.opts.verbose_name
                      or _('Select %s to change') % self.opts.verbose_name)
        self.get_filters(request)
        self.pk_attname = self.lookup_opts.pk.attname

    def get_filters(self, request):
        self.filter_specs = []
        if self.lookup_opts.admin.list_filter and not self.opts.one_to_one_field:
            filter_fields = [self.lookup_opts.get_field(field_name) \
                              for field_name in self.lookup_opts.admin.list_filter]
            for f in filter_fields:
                spec = FilterSpec.create(f, request, self.params)
                if spec and spec.has_output():
                    self.filter_specs.append(spec)
        self.has_filters = bool(self.filter_specs)

    def get_query_string(self, new_params={}, remove=[]):
        p = self.params.copy()
        for r in remove:
            for k in p.keys():
                if k.startswith(r):
                    del p[k]
        for k, v in new_params.items():
            if p.has_key(k) and v is None:
                del p[k]
            elif v is not None:
                p[k] = v
        return '?' + '&amp;'.join(['%s=%s' % (k, v) for k, v in p.items()]).replace(' ', '%20')

    def resolve_model(self, path, request):
        self.model, self.app_label = get_model_and_app(path)
        self.opts = self.model._meta

        if not request.user.has_perm(self.app_label + '.' + self.opts.get_change_permission()):
            raise PermissionDenied

        self.lookup_opts = self.opts
        self.manager = self.model._default_manager

    def get_search_parameters(self, request):
        # Get search parameters from the query string.
        try:
            self.page_num = int(request.GET.get(PAGE_VAR, 0))
        except ValueError:
            self.page_num = 0
        self.show_all = request.GET.has_key(ALL_VAR)
        self.is_popup = request.GET.has_key(IS_POPUP_VAR)
        self.params = dict(request.GET.items())
        if self.params.has_key(PAGE_VAR):
            del self.params[PAGE_VAR]

    def get_results(self, request):
        manager, lookup_params, show_all, page_num = \
            self.manager, self.lookup_params, self.show_all, self.page_num
        # Get the results.
        try:
            paginator = ObjectPaginator(manager, lookup_params, DEFAULT_RESULTS_PER_PAGE)
        # Naked except! Because we don't have any other way of validating "params".
        # They might be invalid if the keyword arguments are incorrect, or if the
        # values are not in the correct type (which would result in a database
        # error).
        except Exception:
            raise
            raise IncorrectLookupParameters()

        # Get the total number of objects, with no filters applied.
        real_lookup_params = lookup_params.copy()
        del real_lookup_params['order_by']
        if real_lookup_params:
            full_result_count = manager.get_count()
        else:
            full_result_count = paginator.hits
        del real_lookup_params
        result_count = paginator.hits
        can_show_all = result_count <= MAX_SHOW_ALL_ALLOWED
        multi_page = result_count > DEFAULT_RESULTS_PER_PAGE

        # Get the list of objects to display on this page.
        if (show_all and can_show_all) or not multi_page:
            result_list = manager.get_list(**lookup_params)
        else:
            try:
                result_list = paginator.get_page(page_num)
            except InvalidPage:
                result_list = []
        (self.result_count, self.full_result_count, self.result_list,
            self.can_show_all, self.multi_page, self.paginator) = (result_count,
                  full_result_count, result_list, can_show_all, multi_page, paginator )

    def url_for_result(self, result):
        return "%s/change/" % getattr(result, self.pk_attname)

    def get_ordering(self):
        lookup_opts, params = self.lookup_opts, self.params
        # For ordering, first check the "ordering" parameter in the admin options,
        # then check the object's default ordering. If neither of those exist,
        # order descending by ID by default. Finally, look for manually-specified
        # ordering from the query string.
        ordering = lookup_opts.admin.ordering or lookup_opts.ordering or ['-' + lookup_opts.pk.name]

        # Normalize it to new-style ordering.
        ordering = handle_legacy_orderlist(ordering)

        if ordering[0].startswith('-'):
            order_field, order_type = ordering[0][1:], 'desc'
        else:
            order_field, order_type = ordering[0], 'asc'
        if params.has_key(ORDER_VAR):
            try:
                try:
                    f = lookup_opts.get_field(lookup_opts.admin.list_display[int(params[ORDER_VAR])])
                except models.FieldDoesNotExist:
                    pass
                else:
                    if not isinstance(f.rel, models.ManyToOne) or not f.null:
                        order_field = f.name
            except (IndexError, ValueError):
                pass # Invalid ordering specified. Just use the default.
        if params.has_key(ORDER_TYPE_VAR) and params[ORDER_TYPE_VAR] in ('asc', 'desc'):
            order_type = params[ORDER_TYPE_VAR]
        self.order_field, self.order_type = order_field, order_type

    def get_lookup_params(self):
        # Prepare the lookup parameters for the API lookup.
        (params, order_field, lookup_opts, order_type, opts, query) = \
           (self.params, self.order_field, self.lookup_opts, self.order_type, self.opts, self.query)

        lookup_params = params.copy()
        for i in (ALL_VAR, ORDER_VAR, ORDER_TYPE_VAR, SEARCH_VAR, IS_POPUP_VAR):
            if lookup_params.has_key(i):
                del lookup_params[i]
        # If the order-by field is a field with a relationship, order by the value
        # in the related table.
        lookup_order_field = order_field
        try:
            f = lookup_opts.get_field(order_field)
        except models.FieldDoesNotExist:
            pass
        else:
            if isinstance(lookup_opts.get_field(order_field).rel, models.ManyToOne):
                f = lookup_opts.get_field(order_field)
                rel_ordering = f.rel.to._meta.ordering and f.rel.to._meta.ordering[0] or f.rel.to._meta.pk.column
                lookup_order_field = '%s.%s' % (f.rel.to._meta.db_table, rel_ordering)
        # Use select_related if one of the list_display options is a field with a
        # relationship.
        if lookup_opts.admin.list_select_related:
            lookup_params['select_related'] = True
        else:
            for field_name in lookup_opts.admin.list_display:
                try:
                    f = lookup_opts.get_field(field_name)
                except models.FieldDoesNotExist:
                    pass
                else:
                    if isinstance(f.rel, models.ManyToOne):
                        lookup_params['select_related'] = True
                        break
        lookup_params['order_by'] = ((order_type == 'desc' and '-' or '') + lookup_order_field,)
        if lookup_opts.admin.search_fields and query:
            complex_queries = []
            for bit in query.split():
                or_queries = []
                for field_name in lookup_opts.admin.search_fields:
                    or_queries.append(models.Q(**{'%s__icontains' % field_name: bit}))
                complex_queries.append(reduce(operator.or_, or_queries))
            lookup_params['complex'] = reduce(operator.and_, complex_queries)
        if opts.one_to_one_field:
            lookup_params.update(opts.one_to_one_field.rel.limit_choices_to)
        self.lookup_params = lookup_params

def change_list(request, path):
    try:
        cl = ChangeList(request, path)
    except IncorrectLookupParameters:
        return HttpResponseRedirect(request.path)

    c = Context(request, {
        'title': cl.title,
        'is_popup': cl.is_popup,
        'cl': cl,
        'path': path[:path.rindex('/')]
    })
    c.update({'has_add_permission': c['perms'][cl.app_label][cl.opts.get_add_permission()]}),
    return render_to_response(['admin/%s/%s/change_list' % (cl.app_label, cl.opts.object_name.lower()),
                               'admin/%s/change_list' % cl.app_label,
                               'admin/change_list'], context_instance=c)
change_list = staff_member_required(change_list)
