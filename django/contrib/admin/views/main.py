from django import template
from django.contrib.admin.filterspecs import FilterSpec
from django.contrib.admin.options import IncorrectLookupParameters
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.cache import never_cache
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import ObjectPaginator, InvalidPage
from django.shortcuts import get_object_or_404, render_to_response
from django.db import models
from django.db.models.query import handle_legacy_orderlist, QuerySet
from django.http import Http404
from django.utils.html import escape
from django.utils.text import capfirst
import operator

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
        self.element_id = self.form_fields[0].get_id()
        self.has_label_first = not isinstance(self.field, models.BooleanField)
        self.raw_id_admin = use_raw_id_admin(field)
        self.is_date_time = isinstance(field, models.DateTimeField)
        self.is_file_field = isinstance(field, models.FileField)
        self.needs_add_label = field.rel and (isinstance(field.rel, models.ManyToOneRel) or isinstance(field.rel, models.ManyToManyRel)) and field.rel.to._meta.admin
        self.hidden = isinstance(self.field, models.AutoField)
        self.first = False

        classes = []
        if self.raw_id_admin:
            classes.append('nowrap')
        if max([bool(f.errors()) for f in self.form_fields]):
            classes.append('error')
        if classes:
            self.cell_class_attribute = ' class="%s" ' % ' '.join(classes)
        self._repr_filled = False

        if field.rel:
            self.related_url = '../../../%s/%s/' % (field.rel.to._meta.app_label, field.rel.to._meta.object_name.lower())

    def original_value(self):
        if self.original:
            return self.original.__dict__[self.field.column]

    def existing_display(self):
        try:
            return self._display
        except AttributeError:
            if isinstance(self.field.rel, models.ManyToOneRel):
                self._display = getattr(self.original, self.field.name)
            elif isinstance(self.field.rel, models.ManyToManyRel):
                self._display = ", ".join([str(obj) for obj in getattr(self.original, self.field.name).all()])
            return self._display

    def __repr__(self):
        return repr(self.__dict__)

    def html_error_list(self):
        return " ".join([form_field.html_error_list() for form_field in self.form_fields if form_field.errors])

    def original_url(self):
        if self.is_file_field and self.original and self.field.attname:
            url_method = getattr(self.original, 'get_%s_url' % self.field.attname)
            if callable(url_method):
                return url_method()
        return ''

def render_change_form(model_admin, model, manipulator, context, add=False, change=False, form_url=''):
    opts = model._meta
    app_label = opts.app_label
    auto_populated_fields = [f for f in opts.fields if f.prepopulate_from]
    original = getattr(manipulator, 'original_object', None)
    ordered_objects = opts.get_ordered_objects()
    inline_related_objects = opts.get_followed_related_objects(manipulator.follow)
    extra_context = {
        'add': add,
        'change': change,
        'has_delete_permission': context['perms'][app_label][opts.get_delete_permission()],
        'has_change_permission': context['perms'][app_label][opts.get_change_permission()],
        'has_file_field': opts.has_field_type(models.FileField),
        'has_absolute_url': hasattr(model, 'get_absolute_url'),
        'auto_populated_fields': auto_populated_fields,
        'ordered_objects': ordered_objects,
        'inline_related_objects': inline_related_objects,
        'form_url': form_url,
        'opts': opts,
        'content_type_id': ContentType.objects.get_for_model(model).id,
        'save_on_top': model_admin.save_on_top,
    }
    context.update(extra_context)
    return render_to_response([
        "admin/%s/%s/change_form.html" % (app_label, opts.object_name.lower()),
        "admin/%s/change_form.html" % app_label,
        "admin/change_form.html"], context_instance=context)

def index(request):
    return render_to_response('admin/index.html', {'title': _('Site administration')}, context_instance=template.RequestContext(request))
index = staff_member_required(never_cache(index))

def _nest_help(obj, depth, val):
    current = obj
    for i in range(depth):
        current = current[-1]
    current.append(val)

def _get_deleted_objects(deleted_objects, perms_needed, user, obj, opts, current_depth):
    "Helper function that recursively populates deleted_objects."
    nh = _nest_help # Bind to local variable for performance
    if current_depth > 16:
        return # Avoid recursing too deep.
    opts_seen = []
    for related in opts.get_all_related_objects():
        if related.opts in opts_seen:
            continue
        opts_seen.append(related.opts)
        rel_opts_name = related.get_accessor_name()
        if isinstance(related.field.rel, models.OneToOneRel):
            try:
                sub_obj = getattr(obj, rel_opts_name)
            except ObjectDoesNotExist:
                pass
            else:
                if related.opts.admin:
                    p = '%s.%s' % (related.opts.app_label, related.opts.get_delete_permission())
                    if not user.has_perm(p):
                        perms_needed.add(related.opts.verbose_name)
                        # We don't care about populating deleted_objects now.
                        continue
                if related.field.rel.edit_inline or not related.opts.admin:
                    # Don't display link to edit, because it either has no
                    # admin or is edited inline.
                    nh(deleted_objects, current_depth, ['%s: %s' % (capfirst(related.opts.verbose_name), sub_obj), []])
                else:
                    # Display a link to the admin page.
                    nh(deleted_objects, current_depth, ['%s: <a href="../../../../%s/%s/%s/">%s</a>' % \
                        (capfirst(related.opts.verbose_name), related.opts.app_label, related.opts.object_name.lower(),
                        sub_obj._get_pk_val(), sub_obj), []])
                _get_deleted_objects(deleted_objects, perms_needed, user, sub_obj, related.opts, current_depth+2)
        else:
            has_related_objs = False
            for sub_obj in getattr(obj, rel_opts_name).all():
                has_related_objs = True
                if related.field.rel.edit_inline or not related.opts.admin:
                    # Don't display link to edit, because it either has no
                    # admin or is edited inline.
                    nh(deleted_objects, current_depth, ['%s: %s' % (capfirst(related.opts.verbose_name), escape(str(sub_obj))), []])
                else:
                    # Display a link to the admin page.
                    nh(deleted_objects, current_depth, ['%s: <a href="../../../../%s/%s/%s/">%s</a>' % \
                        (capfirst(related.opts.verbose_name), related.opts.app_label, related.opts.object_name.lower(), sub_obj._get_pk_val(), escape(str(sub_obj))), []])
                _get_deleted_objects(deleted_objects, perms_needed, user, sub_obj, related.opts, current_depth+2)
            # If there were related objects, and the user doesn't have
            # permission to delete them, add the missing perm to perms_needed.
            if related.opts.admin and has_related_objs:
                p = '%s.%s' % (related.opts.app_label, related.opts.get_delete_permission())
                if not user.has_perm(p):
                    perms_needed.add(related.opts.verbose_name)
    for related in opts.get_all_related_many_to_many_objects():
        if related.opts in opts_seen:
            continue
        opts_seen.append(related.opts)
        rel_opts_name = related.get_accessor_name()
        has_related_objs = False
        rel_objs = getattr(obj, rel_opts_name, None)
        if rel_objs:
            has_related_objs = True

        if has_related_objs:
            for sub_obj in rel_objs.all():
                if related.field.rel.edit_inline or not related.opts.admin:
                    # Don't display link to edit, because it either has no
                    # admin or is edited inline.
                    nh(deleted_objects, current_depth, [_('One or more %(fieldname)s in %(name)s: %(obj)s') % \
                        {'fieldname': related.field.verbose_name, 'name': related.opts.verbose_name, 'obj': escape(str(sub_obj))}, []])
                else:
                    # Display a link to the admin page.
                    nh(deleted_objects, current_depth, [
                        (_('One or more %(fieldname)s in %(name)s:') % {'fieldname': related.field.verbose_name, 'name':related.opts.verbose_name}) + \
                        (' <a href="../../../../%s/%s/%s/">%s</a>' % \
                            (related.opts.app_label, related.opts.module_name, sub_obj._get_pk_val(), escape(str(sub_obj)))), []])
        # If there were related objects, and the user doesn't have
        # permission to change them, add the missing perm to perms_needed.
        if related.opts.admin and has_related_objs:
            p = '%s.%s' % (related.opts.app_label, related.opts.get_change_permission())
            if not user.has_perm(p):
                perms_needed.add(related.opts.verbose_name)

class ChangeList(object):
    def __init__(self, request, model, list_display, list_display_links, list_filter, date_hierarchy, search_fields, list_select_related, list_per_page, model_admin):
        self.model = model
        self.opts = model._meta
        self.lookup_opts = self.opts
        self.root_query_set = model_admin.change_list_queryset(request)
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
        self.show_all = request.GET.has_key(ALL_VAR)
        self.is_popup = request.GET.has_key(IS_POPUP_VAR)
        self.params = dict(request.GET.items())
        if self.params.has_key(PAGE_VAR):
            del self.params[PAGE_VAR]
        if self.params.has_key(ERROR_FLAG):
            del self.params[ERROR_FLAG]

        self.order_field, self.order_type = self.get_ordering()
        self.query = request.GET.get(SEARCH_VAR, '')
        self.query_set = self.get_query_set()
        self.get_results(request)
        self.title = (self.is_popup and _('Select %s') % self.opts.verbose_name or _('Select %s to change') % self.opts.verbose_name)
        self.filter_specs, self.has_filters = self.get_filters(request)
        self.pk_attname = self.lookup_opts.pk.attname

    def get_filters(self, request):
        filter_specs = []
        if self.list_filter and not self.opts.one_to_one_field:
            filter_fields = [self.lookup_opts.get_field(field_name) for field_name in self.list_filter]
            for f in filter_fields:
                spec = FilterSpec.create(f, request, self.params, self.model)
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
            if p.has_key(k) and v is None:
                del p[k]
            elif v is not None:
                p[k] = v
        return '?' + '&amp;'.join(['%s=%s' % (k, v) for k, v in p.items()]).replace(' ', '%20')

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
        if params.has_key(ORDER_VAR):
            try:
                try:
                    f = lookup_opts.get_field(self.list_display[int(params[ORDER_VAR])])
                except models.FieldDoesNotExist:
                    pass
                else:
                    if not isinstance(f.rel, models.ManyToOneRel) or not f.null:
                        order_field = f.name
            except (IndexError, ValueError):
                pass # Invalid ordering specified. Just use the default.
        if params.has_key(ORDER_TYPE_VAR) and params[ORDER_TYPE_VAR] in ('asc', 'desc'):
            order_type = params[ORDER_TYPE_VAR]
        return order_field, order_type

    def get_query_set(self):
        qs = self.root_query_set
        lookup_params = self.params.copy() # a dictionary of the query string
        for i in (ALL_VAR, ORDER_VAR, ORDER_TYPE_VAR, SEARCH_VAR, IS_POPUP_VAR):
            if lookup_params.has_key(i):
                del lookup_params[i]

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
                lookup_order_field = '%s.%s' % (f.rel.to._meta.db_table, rel_ordering)

        # Set ordering.
        qs = qs.order_by((self.order_type == 'desc' and '-' or '') + lookup_order_field)

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

        if self.opts.one_to_one_field:
            qs = qs.complex_filter(self.opts.one_to_one_field.rel.limit_choices_to)

        return qs

    def url_for_result(self, result):
        return "%s/" % quote(getattr(result, self.pk_attname))
