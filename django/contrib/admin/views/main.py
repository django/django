from django import template
from django.contrib.admin.filterspecs import FilterSpec
from django.contrib.admin.options import IncorrectLookupParameters
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.cache import never_cache
from django.core.paginator import ObjectPaginator, InvalidPage
from django.shortcuts import render_to_response
from django.db import models
from django.db.models.query import handle_legacy_orderlist, QuerySet
from django.http import Http404
from django.utils.encoding import force_unicode, smart_str
from django.utils.translation import ugettext
from django.utils.safestring import mark_safe
import operator

try:
    set
except NameError:
    from sets import Set as set   # Python 2.3 fallback

# The system will display a "Show all" link on the change list only if the
# total result count is less than or equal to this setting.
MAX_SHOW_ALL_ALLOWED = 200

# Changelist settings
ALL_VAR = 'all'
ORDER_VAR = 'o'
ORDER_TYPE_VAR = 'ot'
PAGE_VAR = 'p'
SEARCH_VAR = 'q'
IS_POPUP_VAR = 'pop'
ERROR_FLAG = 'e'

# Text to display within change-list table cells if the value is blank.
EMPTY_CHANGELIST_VALUE = '(None)'

use_raw_id_admin = lambda field: isinstance(field.rel, (models.ManyToOneRel, models.ManyToManyRel)) and field.rel.raw_id_admin

def quote(s):
    """
    Ensure that primary key values do not confuse the admin URLs by escaping
    any '/', '_' and ':' characters. Similar to urllib.quote, except that the
    quoting is slightly different so that it doesn't get automatically
    unquoted by the Web browser.
    """
    if type(s) != type(''):
        return s
    res = list(s)
    for i in range(len(res)):
        c = res[i]
        if c in ':/_':
            res[i] = '_%02X' % ord(c)
    return ''.join(res)

def model_admin_view(request, app_label, model_name, rest_of_url):
    model = models.get_model(app_label, model_name)
    if model is None:
        raise Http404("App %r, model %r, not found" % (app_label, model_name))
    if not model._meta.admin:
        raise Http404("This object has no admin interface.")
    mav = model._meta.admin(model)
    return mav(request, rest_of_url)
model_admin_view = staff_member_required(never_cache(model_admin_view))

class AdminBoundField(object):
    def __init__(self, field, field_mapping, original):
        self.field = field
        self.original = original
        self.form_fields = [field_mapping[name] for name in self.field.get_manipulator_field_names('')]
        self.has_label_first = not isinstance(self.field, models.BooleanField)
        self.raw_id_admin = use_raw_id_admin(field)
        self.is_date_time = isinstance(field, models.DateTimeField)
        self.is_file_field = isinstance(field, models.FileField)
        self.hidden = isinstance(self.field, models.AutoField)
        self.first = False

        classes = []
        if self.raw_id_admin:
            classes.append(u'nowrap')
        if max([bool(f.errors()) for f in self.form_fields]):
            classes.append(u'error')
        if classes:
            self.cell_class_attribute = u' class="%s" ' % ' '.join(classes)
        self._repr_filled = False

    def original_value(self):
        if self.original:
            return self.original.__dict__[self.field.attname]

    def existing_display(self):
        try:
            return self._display
        except AttributeError:
            if isinstance(self.field.rel, models.ManyToOneRel):
                self._display = force_unicode(getattr(self.original, self.field.name), strings_only=True)
            elif isinstance(self.field.rel, models.ManyToManyRel):
                self._display = u", ".join([force_unicode(obj) for obj in getattr(self.original, self.field.name).all()])
            return self._display

    def __repr__(self):
        return repr(self.__dict__)

    def html_error_list(self):
        return mark_safe(" ".join([form_field.html_error_list() for form_field in self.form_fields if form_field.errors]))

    def original_url(self):
        if self.is_file_field and self.original and self.field.attname:
            url_method = getattr(self.original, 'get_%s_url' % self.field.attname)
            if callable(url_method):
                return url_method()
        return ''

def index(request):
    return render_to_response('admin/index.html', {'title': ugettext('Site administration')}, context_instance=template.RequestContext(request))
index = staff_member_required(never_cache(index))


class ChangeList(object):
    def __init__(self, request, model, list_display, list_display_links, list_filter, date_hierarchy, search_fields, list_select_related, list_per_page, model_admin):
        self.model = model
        self.opts = model._meta
        self.lookup_opts = self.opts
        self.root_query_set = model_admin.queryset_change(request)
        self.list_display = list_display
        self.list_display_links = list_display_links
        self.list_filter = list_filter
        self.date_hierarchy = date_hierarchy
        self.search_fields = search_fields
        self.list_select_related = list_select_related
        self.list_per_page = list_per_page
        self.model_admin = model_admin

        # Get search parameters from the query string.
        try:
            self.page_num = int(request.GET.get(PAGE_VAR, 0))
        except ValueError:
            self.page_num = 0
        self.show_all = ALL_VAR in request.GET
        self.is_popup = IS_POPUP_VAR in request.GET
        self.params = dict(request.GET.items())
        if PAGE_VAR in self.params:
            del self.params[PAGE_VAR]
        if ERROR_FLAG in self.params:
            del self.params[ERROR_FLAG]

        self.order_field, self.order_type = self.get_ordering()
        self.query = request.GET.get(SEARCH_VAR, '')
        self.query_set = self.get_query_set()
        self.get_results(request)
        self.title = (self.is_popup and ugettext('Select %s') % force_unicode(self.opts.verbose_name) or ugettext('Select %s to change') % force_unicode(self.opts.verbose_name))
        self.filter_specs, self.has_filters = self.get_filters(request)
        self.pk_attname = self.lookup_opts.pk.attname

    def get_filters(self, request):
        filter_specs = []
        if self.list_filter and not self.opts.one_to_one_field:
            filter_fields = [self.lookup_opts.get_field(field_name) for field_name in self.list_filter]
            for f in filter_fields:
                spec = FilterSpec.create(f, request, self.params, self.model, self.model_admin)
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
            if k in p and v is None:
                del p[k]
            elif v is not None:
                p[k] = v
        return mark_safe('?' + '&amp;'.join([u'%s=%s' % (k, v) for k, v in p.items()]).replace(' ', '%20'))

    def get_results(self, request):
        paginator = ObjectPaginator(self.query_set, self.list_per_page)

        # Get the number of objects, with admin filters applied.
        try:
            result_count = paginator.hits
        # Naked except! Because we don't have any other way of validating
        # "params". They might be invalid if the keyword arguments are
        # incorrect, or if the values are not in the correct type (which would
        # result in a database error).
        except:
            raise IncorrectLookupParameters

        # Get the total number of objects, with no admin filters applied.
        # Perform a slight optimization: Check to see whether any filters were
        # given. If not, use paginator.hits to calculate the number of objects,
        # because we've already done paginator.hits and the value is cached.
        if isinstance(self.query_set._filters, models.Q) and not self.query_set._filters.kwargs:
            full_result_count = result_count
        else:
            full_result_count = self.root_query_set.count()

        can_show_all = result_count <= MAX_SHOW_ALL_ALLOWED
        multi_page = result_count > self.list_per_page

        # Get the list of objects to display on this page.
        if (self.show_all and can_show_all) or not multi_page:
            result_list = list(self.query_set)
        else:
            try:
                result_list = paginator.get_page(self.page_num)
            except InvalidPage:
                result_list = ()

        self.result_count = result_count
        self.full_result_count = full_result_count
        self.result_list = result_list
        self.can_show_all = can_show_all
        self.multi_page = multi_page
        self.paginator = paginator

    def get_ordering(self):
        lookup_opts, params = self.lookup_opts, self.params
        # For ordering, first check the "ordering" parameter in the admin options,
        # then check the object's default ordering. If neither of those exist,
        # order descending by ID by default. Finally, look for manually-specified
        # ordering from the query string.
        ordering = self.model_admin.ordering or lookup_opts.ordering or ['-' + lookup_opts.pk.name]

        # Normalize it to new-style ordering.
        ordering = handle_legacy_orderlist(ordering)

        if ordering[0].startswith('-'):
            order_field, order_type = ordering[0][1:], 'desc'
        else:
            order_field, order_type = ordering[0], 'asc'
        if ORDER_VAR in params:
            try:
                field_name = self.list_display[int(params[ORDER_VAR])]
                try:
                    f = lookup_opts.get_field(field_name)
                except models.FieldDoesNotExist:
                    # See whether field_name is a name of a non-field
                    # that allows sorting.
                    try:
                        attr = getattr(self.model, field_name)
                        order_field = attr.admin_order_field
                    except AttributeError:
                        pass
                else:
                    if not isinstance(f.rel, models.ManyToOneRel) or not f.null:
                        order_field = f.name
            except (IndexError, ValueError):
                pass # Invalid ordering specified. Just use the default.
        if ORDER_TYPE_VAR in params and params[ORDER_TYPE_VAR] in ('asc', 'desc'):
            order_type = params[ORDER_TYPE_VAR]
        return order_field, order_type

    def get_query_set(self):
        qs = self.root_query_set
        lookup_params = self.params.copy() # a dictionary of the query string
        for i in (ALL_VAR, ORDER_VAR, ORDER_TYPE_VAR, SEARCH_VAR, IS_POPUP_VAR):
            if i in lookup_params:
                del lookup_params[i]
        for key, value in lookup_params.items():
            if not isinstance(key, str):
                # 'key' will be used as a keyword argument later, so Python
                # requires it to be a string.
                del lookup_params[key]
                lookup_params[smart_str(key)] = value

        # Apply lookup parameters from the query string.
        qs = qs.filter(**lookup_params)

        # Use select_related() if one of the list_display options is a field
        # with a relationship.
        if self.list_select_related:
            qs = qs.select_related()
        else:
            for field_name in self.list_display:
                try:
                    f = self.lookup_opts.get_field(field_name)
                except models.FieldDoesNotExist:
                    pass
                else:
                    if isinstance(f.rel, models.ManyToOneRel):
                        qs = qs.select_related()
                        break

        # Calculate lookup_order_field.
        # If the order-by field is a field with a relationship, order by the
        # value in the related table.
        lookup_order_field = self.order_field
        order_type = self.order_type == 'desc' and '-' or ''
        try:
            f = self.lookup_opts.get_field(self.order_field, many_to_many=False)
        except models.FieldDoesNotExist:
            pass
        else:
            if isinstance(f.rel, models.OneToOneRel):
                # For OneToOneFields, don't try to order by the related object's ordering criteria.
                pass
            elif isinstance(f.rel, models.ManyToOneRel):
                rel_ordering = f.rel.to._meta.ordering and f.rel.to._meta.ordering[0] or f.rel.to._meta.pk.column
                if rel_ordering[0] == '-':
                    rel_ordering = rel_ordering[1:]
                    order_type = not order_type and '-' or ''
                lookup_order_field = '%s.%s' % (f.rel.to._meta.db_table, rel_ordering)
                # FIXME: Must use select_related() becuase the lookup field may
                # be in a table not otherwise referenced yet.
                qs = qs.select_related()

        # Set ordering.
        qs = qs.order_by(order_type + lookup_order_field)

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
            for bit in self.query.split():
                or_queries = [models.Q(**{construct_search(field_name): bit}) for field_name in self.search_fields]
                other_qs = QuerySet(self.model)
                if qs._select_related:
                    other_qs = other_qs.select_related()
                other_qs = other_qs.filter(reduce(operator.or_, or_queries))
                qs = qs & other_qs
            for field_name in self.search_fields:
                if '__' in field_name:
                    qs = qs.distinct()
                    break

        if self.opts.one_to_one_field:
            qs = qs.complex_filter(self.opts.one_to_one_field.rel.limit_choices_to)

        return qs

    def url_for_result(self, result):
        return "%s/" % quote(getattr(result, self.pk_attname))
