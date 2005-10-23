# Generic admin views.

from django.contrib.admin.views.decorators import staff_member_required
from django.core import formfields, meta, template
from django.core.template import loader
from django.core.meta.fields import BoundField, BoundFieldLine, BoundFieldSet
from django.core.exceptions import Http404, ObjectDoesNotExist, PermissionDenied
from django.core.extensions import DjangoContext as Context
from django.core.extensions import get_object_or_404, render_to_response
from django.models.admin import log
from django.utils.html import strip_tags
from django.utils.httpwrappers import HttpResponse, HttpResponseRedirect
from django.utils.text import capfirst, get_text_list
from django.conf.settings import ADMIN_MEDIA_PREFIX
import operator

# Text to display within changelist table cells if the value is blank.
EMPTY_CHANGELIST_VALUE = '(None)'

def _get_mod_opts(app_label, module_name):
    "Helper function that returns a tuple of (module, opts), raising Http404 if necessary."
    try:
        mod = meta.get_module(app_label, module_name)
    except ImportError:
        raise Http404 # Invalid app or module name. Maybe it's not in INSTALLED_APPS.
    opts = mod.Klass._meta
    if not opts.admin:
        raise Http404 # This object is valid but has no admin interface.
    return mod, opts

def get_query_string(original_params, new_params={}, remove=[]):
    """
    >>> get_query_string({'first_name': 'adrian', 'last_name': 'smith'})
    '?first_name=adrian&amp;last_name=smith'
    >>> get_query_string({'first_name': 'adrian', 'last_name': 'smith'}, {'first_name': 'john'})
    '?first_name=john&amp;last_name=smith'
    >>> get_query_string({'test': 'yes'}, {'blah': 'no'}, ['te'])
    '?blah=no'
    """
    p = original_params.copy()
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

def index(request):
    return render_to_response('admin/index', {'title': 'Site administration'}, context_instance=Context(request))
index = staff_member_required(index)

def change_list(request, app_label, module_name):
    from django.core import paginator
    from django.utils import dateformat
    from django.utils.dates import MONTHS
    from django.utils.html import escape
    import datetime

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

    mod, opts = _get_mod_opts(app_label, module_name)
    if not request.user.has_perm(app_label + '.' + opts.get_change_permission()):
        raise PermissionDenied

    lookup_mod, lookup_opts = mod, opts

    if opts.one_to_one_field:
        lookup_mod = opts.one_to_one_field.rel.to.get_model_module()
        lookup_opts = lookup_mod.Klass._meta
        # If lookup_opts doesn't have admin set, give it the default meta.Admin().
        if not lookup_opts.admin:
            lookup_opts.admin = meta.Admin()

    # Get search parameters from the query string.
    try:
        page_num = int(request.GET.get(PAGE_VAR, 0))
    except ValueError:
        page_num = 0
    show_all = request.GET.has_key(ALL_VAR)
    is_popup = request.GET.has_key(IS_POPUP_VAR)
    params = dict(request.GET.copy())
    if params.has_key(PAGE_VAR):
        del params[PAGE_VAR]
    # For ordering, first check the "ordering" parameter in the admin options,
    # then check the object's default ordering. If neither of those exist,
    # order descending by ID by default. Finally, look for manually-specified
    # ordering from the query string.
    ordering = lookup_opts.admin.ordering or lookup_opts.ordering or ['-' + lookup_opts.pk.name]

    # Normalize it to new-style ordering.
    ordering = meta.handle_legacy_orderlist(ordering)

    if ordering[0].startswith('-'):
        order_field, order_type = ordering[0][1:], 'desc'
    else:
        order_field, order_type = ordering[0], 'asc'
    if params.has_key(ORDER_VAR):
        try:
            try:
                f = lookup_opts.get_field(lookup_opts.admin.list_display[int(params[ORDER_VAR])])
            except meta.FieldDoesNotExist:
                pass
            else:
                if not isinstance(f.rel, meta.ManyToOne) or not f.null:
                    order_field = f.name
        except (IndexError, ValueError):
            pass # Invalid ordering specified. Just use the default.
    if params.has_key(ORDER_TYPE_VAR) and params[ORDER_TYPE_VAR] in ('asc', 'desc'):
        order_type = params[ORDER_TYPE_VAR]
    query = request.GET.get(SEARCH_VAR, '')

    # Prepare the lookup parameters for the API lookup.
    lookup_params = params.copy()
    for i in (ALL_VAR, ORDER_VAR, ORDER_TYPE_VAR, SEARCH_VAR, IS_POPUP_VAR):
        if lookup_params.has_key(i):
            del lookup_params[i]
    # If the order-by field is a field with a relationship, order by the value
    # in the related table.
    lookup_order_field = order_field
    if isinstance(lookup_opts.get_field(order_field).rel, meta.ManyToOne):
        f = lookup_opts.get_field(order_field)
        rel_ordering = f.rel.to.ordering and f.rel.to.ordering[0] or f.rel.to.pk.column
        lookup_order_field = '%s.%s' % (f.rel.to.db_table, rel_ordering)
    # Use select_related if one of the list_display options is a field with a
    # relationship.
    for field_name in lookup_opts.admin.list_display:
        try:
            f = lookup_opts.get_field(field_name)
        except meta.FieldDoesNotExist:
            pass
        else:
            if isinstance(f.rel, meta.ManyToOne):
                lookup_params['select_related'] = True
                break
    lookup_params['order_by'] = ((order_type == 'desc' and '-' or '') + lookup_order_field,)
    if lookup_opts.admin.search_fields and query:
        or_queries = []
        for bit in query.split():
            or_query = []
            for field_name in lookup_opts.admin.search_fields:
                or_query.append(('%s__icontains' % field_name, bit))
            or_queries.append(or_query)
        lookup_params['_or'] = or_queries

    if opts.one_to_one_field:
        lookup_params.update(opts.one_to_one_field.rel.limit_choices_to)

    # Get the results.
    try:
        p = paginator.ObjectPaginator(lookup_mod, lookup_params, DEFAULT_RESULTS_PER_PAGE)
    # Naked except! Because we don't have any other way of validating "params".
    # They might be invalid if the keyword arguments are incorrect, or if the
    # values are not in the correct type (which would result in a database
    # error).
    except:
        return HttpResponseRedirect(request.path)

    # Get the total number of objects, with no filters applied.
    real_lookup_params = lookup_params.copy()
    del real_lookup_params['order_by']
    if real_lookup_params:
        full_result_count = lookup_mod.get_count()
    else:
        full_result_count = p.hits
    del real_lookup_params
    result_count = p.hits
    can_show_all = result_count <= MAX_SHOW_ALL_ALLOWED
    multi_page = result_count > DEFAULT_RESULTS_PER_PAGE

    # Get the list of objects to display on this page.
    if (show_all and can_show_all) or not multi_page:
        result_list = lookup_mod.get_list(**lookup_params)
    else:
        try:
            result_list = p.get_page(page_num)
        except paginator.InvalidPage:
            result_list = []

    # Calculate filters first, because a CSS class high in the document depends
    # on whether they are available.
    filter_template = []
    if lookup_opts.admin.list_filter and not opts.one_to_one_field:
        filter_fields = [lookup_opts.get_field(field_name) for field_name in lookup_opts.admin.list_filter]
        for f in filter_fields:
            # Many-to-many or many-to-one filter.
            if f.rel:
                if isinstance(f, meta.ManyToManyField):
                    lookup_title = f.rel.to.verbose_name
                else:
                    lookup_title = f.verbose_name
                lookup_kwarg = '%s__%s__exact' % (f.name, f.rel.to.pk.name)
                lookup_val = request.GET.get(lookup_kwarg, None)
                lookup_choices = f.rel.to.get_model_module().get_list()
                if len(lookup_choices) > 1:
                    filter_template.append('<h3>By %s:</h3>\n<ul>\n' % lookup_title)
                    filter_template.append('<li%s><a href="%s">All</a></li>\n' % \
                        ((lookup_val is None and ' class="selected"' or ''),
                        get_query_string(params, {}, [lookup_kwarg])))
                    for val in lookup_choices:
                        pk_val = getattr(val, f.rel.to.pk.column)
                        filter_template.append('<li%s><a href="%s">%r</a></li>\n' % \
                            ((lookup_val == str(pk_val) and ' class="selected"' or ''),
                            get_query_string(params, {lookup_kwarg: pk_val}), val))
                    filter_template.append('</ul>\n\n')
            # Field with choices.
            elif f.choices:
                lookup_kwarg = '%s__exact' % f.name
                lookup_val = request.GET.get(lookup_kwarg, None)
                filter_template.append('<h3>By %s:</h3><ul>\n' % f.verbose_name)
                filter_template.append('<li%s><a href="%s">All</a></li>\n' % \
                    ((lookup_val is None and ' class="selected"' or ''),
                    get_query_string(params, {}, [lookup_kwarg])))
                for k, v in f.choices:
                    filter_template.append('<li%s><a href="%s">%s</a></li>' % \
                        ((str(k) == lookup_val) and ' class="selected"' or '',
                        get_query_string(params, {lookup_kwarg: k}), v))
                filter_template.append('</ul>\n\n')
            # Date filter.
            elif isinstance(f, meta.DateField):
                today = datetime.date.today()
                one_week_ago = today - datetime.timedelta(days=7)
                field_generic = '%s__' % f.name
                filter_template.append('<h3>By %s:</h3><ul>\n' % f.verbose_name)
                date_params = dict([(k, v) for k, v in params.items() if k.startswith(field_generic)])
                today_str = isinstance(f, meta.DateTimeField) and today.strftime('%Y-%m-%d 23:59:59') or today.strftime('%Y-%m-%d')
                for title, param_dict in (
                    ('Any date', {}),
                    ('Today', {'%s__year' % f.name: str(today.year), '%s__month' % f.name: str(today.month), '%s__day' % f.name: str(today.day)}),
                    ('Past 7 days', {'%s__gte' % f.name: one_week_ago.strftime('%Y-%m-%d'), '%s__lte' % f.name: today_str}),
                    ('This month', {'%s__year' % f.name: str(today.year), '%s__month' % f.name: str(today.month)}),
                    ('This year', {'%s__year' % f.name: str(today.year)})
                ):
                    filter_template.append('<li%s><a href="%s">%s</a></li>\n' % \
                        ((date_params == param_dict) and ' class="selected"' or '',
                        get_query_string(params, param_dict, field_generic), title))
                filter_template.append('</ul>\n\n')
            elif isinstance(f, meta.BooleanField) or isinstance(f, meta.NullBooleanField):
                lookup_kwarg = '%s__exact' % f.name
                lookup_kwarg2 = '%s__isnull' % f.name
                lookup_val = request.GET.get(lookup_kwarg, None)
                lookup_val2 = request.GET.get(lookup_kwarg2, None)
                filter_template.append('<h3>By %s:</h3><ul>\n' % f.verbose_name)
                for k, v in (('All', None), ('Yes', '1'), ('No', '0')):
                    filter_template.append('<li%s><a href="%s">%s</a></li>\n' % \
                        (((lookup_val == v and not lookup_val2) and ' class="selected"' or ''),
                        get_query_string(params, {lookup_kwarg: v}, [lookup_kwarg2]), k))
                if isinstance(f, meta.NullBooleanField):
                    filter_template.append('<li%s><a href="%s">%s</a></li>\n' % \
                        (((lookup_val2 == 'True') and ' class="selected"' or ''),
                        get_query_string(params, {lookup_kwarg2: 'True'}, [lookup_kwarg]), 'Unknown'))
                filter_template.append('</ul>\n\n')
            else:
                pass # Invalid argument to "list_filter"

    raw_template = ['{% extends "admin/base_site" %}\n']
    raw_template.append('{% block bodyclass %}change-list{% endblock %}\n')
    if not is_popup:
        raw_template.append('{%% block breadcrumbs %%}<div class="breadcrumbs"><a href="../../">Home</a> &rsaquo; %s</div>{%% endblock %%}\n' % capfirst(opts.verbose_name_plural))
    raw_template.append('{% block coltype %}flex{% endblock %}')
    raw_template.append('{% block content %}\n')
    raw_template.append('<div id="content-main">\n')
    if request.user.has_perm(app_label + '.' + lookup_opts.get_add_permission()):
        raw_template.append('<ul class="object-tools"><li><a href="add/%s" class="addlink">Add %s</a></li></ul>\n' % ((is_popup and '?_popup=1' or ''), opts.verbose_name))
    raw_template.append('<div class="module%s" id="changelist">\n' % (filter_template and ' filtered' or ''))

    # Search form.
    if lookup_opts.admin.search_fields:
        raw_template.append('<div id="toolbar">\n<form id="changelist-search" action="" method="get">\n')
        raw_template.append('<label><img src="%simg/admin/icon_searchbox.png" /></label> ' % ADMIN_MEDIA_PREFIX)
        raw_template.append('<input type="text" size="40" name="%s" value="%s" id="searchbar" /> ' % \
            (SEARCH_VAR, escape(query)))
        raw_template.append('<input type="submit" value="Go" /> ')
        if result_count != full_result_count and not opts.one_to_one_field:
            raw_template.append('<span class="small quiet">%s result%s (<a href="?">%s total</a>)</span>' % \
                (result_count, (result_count != 1 and 's' or ''), full_result_count))
        for k, v in params.items():
            if k != SEARCH_VAR:
                raw_template.append('<input type="hidden" name="%s" value="%s" />' % (escape(k), escape(v)))
        raw_template.append('</form></div>\n')
        raw_template.append('<script type="text/javascript">document.getElementById("searchbar").focus();</script>')

    # Date-based navigation.
    if lookup_opts.admin.date_hierarchy:
        field_name = lookup_opts.admin.date_hierarchy

        year_field = '%s__year' % field_name
        month_field = '%s__month' % field_name
        day_field = '%s__day' % field_name
        field_generic = '%s__' % field_name
        year_lookup = params.get(year_field)
        month_lookup = params.get(month_field)
        day_lookup = params.get(day_field)

        raw_template.append('<div class="xfull">\n<ul class="toplinks">\n')
        if year_lookup and month_lookup and day_lookup:
            raw_template.append('<li class="date-back"><a href="%s">&lsaquo; %s %s </a></li>' % \
                (get_query_string(params, {year_field: year_lookup, month_field: month_lookup}, [field_generic]), MONTHS[int(month_lookup)], year_lookup))
            raw_template.append('<li>%s %s</li>' % (MONTHS[int(month_lookup)], day_lookup))
        elif year_lookup and month_lookup:
            raw_template.append('<li class="date-back"><a href="%s">&lsaquo; %s</a></li>' % \
                (get_query_string(params, {year_field: year_lookup}, [field_generic]), year_lookup))
            date_lookup_params = lookup_params.copy()
            date_lookup_params.update({year_field: year_lookup, month_field: month_lookup})
            for day in getattr(lookup_mod, 'get_%s_list' % field_name)('day', **date_lookup_params):
                raw_template.append('<li><a href="%s">%s</a></li>' % \
                    (get_query_string(params, {year_field: year_lookup, month_field: month_lookup, day_field: day.day}, [field_generic]), day.strftime('%B %d')))
        elif year_lookup:
            raw_template.append('<li class="date-back"><a href="%s">&lsaquo; All dates</a></li>' % \
                get_query_string(params, {}, [year_field]))
            date_lookup_params = lookup_params.copy()
            date_lookup_params.update({year_field: year_lookup})
            for month in getattr(lookup_mod, 'get_%s_list' % field_name)('month', **date_lookup_params):
                raw_template.append('<li><a href="%s">%s %s</a></li>' % \
                    (get_query_string(params, {year_field: year_lookup, month_field: month.month}, [field_generic]), month.strftime('%B'), month.year))
        else:
            for year in getattr(lookup_mod, 'get_%s_list' % field_name)('year', **lookup_params):
                raw_template.append('<li><a href="%s">%s</a></li>\n' % \
                    (get_query_string(params, {year_field: year.year}, [field_generic]), year.year))
        raw_template.append('</ul><br class="clear" />\n</div>\n')

    # Filters.
    if filter_template:
        raw_template.append('<div id="changelist-filter">\n<h2>Filter</h2>\n')
        raw_template.extend(filter_template)
        raw_template.append('</div>')
    del filter_template

    # Result table.
    if result_list:
        # Table headers.
        raw_template.append('<table cellspacing="0">\n<thead>\n<tr>\n')
        for i, field_name in enumerate(lookup_opts.admin.list_display):
            try:
                f = lookup_opts.get_field(field_name)
            except meta.FieldDoesNotExist:
                # For non-field list_display values, check for the function
                # attribute "short_description". If that doesn't exist, fall
                # back to the method name. And __repr__ is a special-case.
                if field_name == '__repr__':
                    header = lookup_opts.verbose_name
                else:
                    func = getattr(mod.Klass, field_name) # Let AttributeErrors propogate.
                    try:
                        header = func.short_description
                    except AttributeError:
                        header = func.__name__
                # Non-field list_display values don't get ordering capability.
                raw_template.append('<th>%s</th>' % capfirst(header))
            else:
                if isinstance(f.rel, meta.ManyToOne) and f.null:
                    raw_template.append('<th>%s</th>' % capfirst(f.verbose_name))
                else:
                    th_classes = []
                    new_order_type = 'asc'
                    if field_name == order_field:
                        th_classes.append('sorted %sending' % order_type.lower())
                        new_order_type = {'asc': 'desc', 'desc': 'asc'}[order_type.lower()]
                    raw_template.append('<th%s><a href="%s">%s</a></th>' % \
                        ((th_classes and ' class="%s"' % ' '.join(th_classes) or ''),
                        get_query_string(params, {ORDER_VAR: i, ORDER_TYPE_VAR: new_order_type}),
                        capfirst(f.verbose_name)))
        raw_template.append('</tr>\n</thead>\n')
        # Result rows.
        pk = lookup_opts.pk.name
        for i, result in enumerate(result_list):
            raw_template.append('<tr class="row%s">\n' % (i % 2 + 1))
            for j, field_name in enumerate(lookup_opts.admin.list_display):
                row_class = ''
                try:
                    f = lookup_opts.get_field(field_name)
                except meta.FieldDoesNotExist:
                    # For non-field list_display values, the value is a method
                    # name. Execute the method.
                    try:
                        result_repr = strip_tags(str(getattr(result, field_name)()))
                    except ObjectDoesNotExist:
                        result_repr = EMPTY_CHANGELIST_VALUE
                else:
                    field_val = getattr(result, f.column)
                    # Foreign-key fields are special: Use the repr of the
                    # related object.
                    if isinstance(f.rel, meta.ManyToOne):
                        if field_val is not None:
                            result_repr = getattr(result, 'get_%s' % f.name)()
                        else:
                            result_repr = EMPTY_CHANGELIST_VALUE
                    # Dates are special: They're formatted in a certain way.
                    elif isinstance(f, meta.DateField):
                        if field_val:
                            if isinstance(f, meta.DateTimeField):
                                result_repr = dateformat.format(field_val, 'N j, Y, P')
                            else:
                                result_repr = dateformat.format(field_val, 'N j, Y')
                        else:
                            result_repr = EMPTY_CHANGELIST_VALUE
                        row_class = ' class="nowrap"'
                    # Booleans are special: We use images.
                    elif isinstance(f, meta.BooleanField) or isinstance(f, meta.NullBooleanField):
                        BOOLEAN_MAPPING = {True: 'yes', False: 'no', None: 'unknown'}
                        result_repr = '<img src="%simg/admin/icon-%s.gif" alt="%s" />' % (ADMIN_MEDIA_PREFIX, BOOLEAN_MAPPING[field_val], field_val)
                    # ImageFields are special: Use a thumbnail.
                    elif isinstance(f, meta.ImageField):
                        from django.parts.media.photos import get_thumbnail_url
                        result_repr = '<img src="%s" alt="%s" title="%s" />' % (get_thumbnail_url(getattr(result, 'get_%s_url' % f.name)(), '120'), field_val, field_val)
                    # FloatFields are special: Zero-pad the decimals.
                    elif isinstance(f, meta.FloatField):
                        if field_val is not None:
                            result_repr = ('%%.%sf' % f.decimal_places) % field_val
                        else:
                            result_repr = EMPTY_CHANGELIST_VALUE
                    # Fields with choices are special: Use the representation
                    # of the choice.
                    elif f.choices:
                        result_repr = dict(f.choices).get(field_val, EMPTY_CHANGELIST_VALUE)
                    else:
                        result_repr = strip_tags(str(field_val))
                # Some browsers don't like empty "<td></td>"s.
                if result_repr == '':
                    result_repr = '&nbsp;'
                if j == 0: # First column is a special case
                    result_id = getattr(result, pk)
                    raw_template.append('<th%s><a href="%s/"%s>%s</a></th>' % \
                        (row_class, result_id, (is_popup and ' onclick="opener.dismissRelatedLookupPopup(window, %r); return false;"' % result_id or ''), result_repr))
                else:
                    raw_template.append('<td%s>%s</td>' % (row_class, result_repr))
            raw_template.append('</tr>\n')
        del result_list # to free memory
        raw_template.append('</table>\n')
    else:
        raw_template.append('<p>No %s matched your search criteria.</p>' % opts.verbose_name_plural)

    # Pagination.
    raw_template.append('<p class="paginator">')
    if (show_all and can_show_all) or not multi_page:
        pass
    else:
        raw_template.append('Page &rsaquo; ')
        ON_EACH_SIDE = 3
        ON_ENDS = 2
        DOT = '.'
        # If there are 10 or fewer pages, display links to every page.
        # Otherwise, do some fancy
        if p.pages <= 10:
            page_range = range(p.pages)
        else:
            # Insert "smart" pagination links, so that there are always ON_ENDS
            # links at either end of the list of pages, and there are always
            # ON_EACH_SIDE links at either end of the "current page" link.
            page_range = []
            if page_num > (ON_EACH_SIDE + ON_ENDS):
                page_range.extend(range(0, ON_EACH_SIDE - 1))
                page_range.append(DOT)
                page_range.extend(range(page_num - ON_EACH_SIDE, page_num + 1))
            else:
                page_range.extend(range(0, page_num + 1))
            if page_num < (p.pages - ON_EACH_SIDE - ON_ENDS - 1):
                page_range.extend(range(page_num + 1, page_num + ON_EACH_SIDE + 1))
                page_range.append(DOT)
                page_range.extend(range(p.pages - ON_ENDS, p.pages))
            else:
                page_range.extend(range(page_num + 1, p.pages))
        for i in page_range:
            if i == DOT:
                raw_template.append('... ')
            elif i == page_num:
                raw_template.append('<span class="this-page">%d</span> ' % (i+1))
            else:
                raw_template.append('<a href="%s"%s>%d</a> ' % \
                    (get_query_string(params, {PAGE_VAR: i}), (i == p.pages-1 and ' class="end"' or ''), i+1))
    raw_template.append('%s %s' % (result_count, result_count == 1 and opts.verbose_name or opts.verbose_name_plural))
    if can_show_all and not show_all and multi_page:
        raw_template.append('&nbsp;&nbsp;<a href="%s" class="showall">Show all</a>' % \
            get_query_string(params, {ALL_VAR: ''}))
    raw_template.append('</p>')

    raw_template.append('</div>\n</div>')
    raw_template.append('{% endblock %}\n')
    t = loader.get_template_from_string(''.join(raw_template))
    c = Context(request, {
        'title': (is_popup and 'Select %s' % opts.verbose_name or 'Select %s to change' % opts.verbose_name),
        'is_popup': is_popup,
    })
    return HttpResponse(t.render(c))
change_list = staff_member_required(change_list)

use_raw_id_admin = lambda field: isinstance(field.rel, (meta.ManyToOne, meta.ManyToMany)) and field.rel.raw_id_admin

def _get_submit_row_template(opts, app_label, add, change, show_delete, ordered_objects):
    t = ['<div class="submit-row">']
    if change or show_delete:
        t.append('{%% if perms.%s.%s %%}{%% if not is_popup %%}<p class="float-left"><a href="delete/" class="deletelink">Delete</a></p>{%% endif %%}{%% endif %%}' % \
            (app_label, opts.get_delete_permission()))
    if change and opts.admin.save_as:
        t.append('{%% if not is_popup %%}<input type="submit" value="Save as new" name="_saveasnew" %s/>{%% endif %%}' % \
            (ordered_objects and change and 'onclick="submitOrderForm();"' or ''))
    if not opts.admin.save_as or add:
        t.append('{%% if not is_popup %%}<input type="submit" value="Save and add another" name="_addanother" %s/>{%% endif %%}' % \
            (ordered_objects and change and 'onclick="submitOrderForm();"' or ''))
    t.append('{%% if not is_popup %%}<input type="submit" value="Save and continue editing" name="_continue" %s/>{%% endif %%}' % \
        (ordered_objects and change and 'onclick="submitOrderForm();"' or ''))
    t.append('<input type="submit" value="Save" class="default" %s/>' % \
        (ordered_objects and change and 'onclick="submitOrderForm();"' or ''))
    t.append('</div>\n')
    return t

def get_javascript_imports(opts,auto_populated_fields, ordered_objects, field_sets):
# Put in any necessary JavaScript imports.
    js = ['js/core.js', 'js/admin/RelatedObjectLookups.js']
    if auto_populated_fields:
        js.append('js/urlify.js')
    if opts.has_field_type(meta.DateTimeField) or opts.has_field_type(meta.TimeField) or opts.has_field_type(meta.DateField):
        js.extend(['js/calendar.js', 'js/admin/DateTimeShortcuts.js'])
    if ordered_objects:
        js.extend(['js/getElementsBySelector.js', 'js/dom-drag.js' , 'js/admin/ordering.js'])
    if opts.admin.js:
        js.extend(opts.admin.js)
    seen_collapse = False
    for field_set in field_sets:
        if not seen_collapse and 'collapse' in field_set.classes:
            seen_collapse = True
            js.append('js/admin/CollapsedFieldsets.js' )
        try:
            for field_line in field_set:
                for f in field_line:
                    if f.rel and isinstance(f, meta.ManyToManyField) and f.rel.filter_interface:
                        js.extend(['js/SelectBox.js' , 'js/SelectFilter2.js'])
                        raise StopIteration
        except StopIteration:
            break
    return js


class AdminBoundField(BoundField):
    def __init__(self, field, field_mapping, original):
        super(AdminBoundField, self).__init__(field,field_mapping,original) 	

        self.element_id = self.form_fields[0].get_id() 
        self.has_label_first = not isinstance(self.field, meta.BooleanField)
        self.raw_id_admin = use_raw_id_admin(field)
        self.is_date_time = isinstance(field, meta.DateTimeField)
        self.is_file_field = isinstance(field, meta.FileField)
        self.needs_add_label = field.rel and isinstance(field.rel, meta.ManyToOne) or isinstance(field.rel, meta.ManyToMany) and field.rel.to.admin
        self.not_in_table = isinstance(self.field, meta.AutoField)
        self.first = False
        
        classes = []
        if(self.raw_id_admin): 
            classes.append('nowrap')
        if max([bool(f.errors()) for f in self.form_fields]):
            classes.append('error')
        if classes:
            self.cell_class_attribute = ' class="%s" ' % ' '.join(classes)
        self._repr_filled = False
    
    def _fetch_existing_repr(self, func_name):
        class_dict = self.original.__class__.__dict__
        func = class_dict.get(func_name)
        return func(self.original)
        
    def _fill_existing_repr(self):
        if self._repr_filled: 
            return
        #HACK
        if isinstance(self.field.rel, meta.ManyToOne):
             func_name = 'get_%s' % self.field.name
             self._repr = self._fetch_existing_repr(func_name)
        elif isinstance(self.field.rel, meta.ManyToMany):
            func_name = 'get_%s_list' % self.field.name 
            self._repr =  ",".join(self._fetch_existing_repr(func_name))
        self._repr_filled = True
             
    def existing_repr(self):
        self._fill_existing_repr()
        return self._repr

    def __repr__(self):
        return repr(self.__dict__)

    def html_error_list(self):
        return " ".join([form_field.html_error_list() for form_field in self.form_fields if form_field.errors])        


class AdminBoundFieldLine(BoundFieldLine):
    def __init__(self, field_line, field_mapping, original):
        super(AdminBoundFieldLine, self).__init__(field_line, field_mapping, original, AdminBoundField)
        for bound_field in self:
            bound_field.first = True
            break

class AdminBoundFieldSet(BoundFieldSet):
    def __init__(self, field_set, field_mapping, original):
        super(AdminBoundFieldSet, self).__init__(field_set, field_mapping, original, AdminBoundFieldLine)
        
        
def render_change_form(opts, app_label, context, add=False, change=False, show_delete=False, form_url=''):
    ordered_objects = opts.get_ordered_objects()[:]
    auto_populated_fields = [f for f in opts.fields if f.prepopulate_from]
    coltype = ordered_objects and 'colMS' or 'colM'
    	
    has_absolute_url = hasattr(opts.get_model_module().Klass, 'get_absolute_url')
    form_enc_attrib = opts.has_field_type(meta.FileField) and 'enctype="multipart/form-data" ' or ''
    form = context['form']
    original = context['original']
    
    field_sets = opts.admin.get_field_sets(opts)
    bound_field_sets = [field_set.bind(form, original, AdminBoundFieldSet) 
                        for field_set in field_sets]
                        
    javascript_imports = get_javascript_imports(opts, auto_populated_fields, ordered_objects, field_sets);
    first_form_field = bound_field_sets[0].bound_field_lines[0].bound_fields[0].form_fields[0];                
    inline_related_objects = opts.get_followed_related_objects()
    ordered_object_names =   ' '.join(['object.%s' % o.pk.name for o in ordered_objects])
   
    extra_context = {
        'add': add,
        'change': change,
        'first_form_field_id': first_form_field.get_id(),
        'ordered_objects' : ordered_objects, 
        'ordered_object_names' : ordered_object_names,
        'auto_populated_fields' : auto_populated_fields,
        'javascript_imports' : javascript_imports, 
        'coltype' : coltype, 
        'has_absolute_url': has_absolute_url, 
        'form_enc_attrib': form_enc_attrib,
        'form_url' : form_url,
        'bound_field_sets' : bound_field_sets,
        'inline_related_objects': inline_related_objects,
        'content_type_id' : opts.get_content_type_id(),
        'save_on_top' : opts.admin.save_on_top,
        'verbose_name_plural': opts.verbose_name_plural,
        'verbose_name': opts.verbose_name,
        'save_as': opts.admin.save_as, 
        'app_label': app_label,
        'object_name': opts.object_name,
        'has_delete_permission' : context['perms'][app_label][opts.get_delete_permission()]
    }
    
    context.update(extra_context)
    
    return render_to_response(["admin/%s/%s/change_form" % (app_label, opts.object_name.lower() ), 
                               "admin/%s/change_form" % app_label , 
                               "admin/change_form"], 
                              context_instance=context)
   
def log_add_message(user, opts,manipulator,new_object):
    pk_value = getattr(new_object, opts.pk.column)
    log.log_action(user.id, opts.get_content_type_id(), pk_value, repr(new_object), log.ADDITION)

def add_stage(request, app_label, module_name, show_delete=False, form_url='', post_url='../', post_url_continue='../%s/', object_id_override=None):
    mod, opts = _get_mod_opts(app_label, module_name)
    if not request.user.has_perm(app_label + '.' + opts.get_add_permission()):
        raise PermissionDenied
    manipulator = mod.AddManipulator()
    if request.POST:
        new_data = request.POST.copy()
        if opts.has_field_type(meta.FileField):
            new_data.update(request.FILES)
        errors = manipulator.get_validation_errors(new_data)
        manipulator.do_html2python(new_data)
        
        if not errors and not request.POST.has_key("_preview"):
            new_object = manipulator.save(new_data)
            log_add_message(request.user, opts,manipulator,new_object)
            msg = 'The %s "%s" was added successfully.' % (opts.verbose_name, new_object)
            
            # Here, we distinguish between different save types by checking for
            # the presence of keys in request.POST.
            if request.POST.has_key("_continue"):
                request.user.add_message("%s You may edit it again below." % msg)
                if request.POST.has_key("_popup"):
                    post_url_continue += "?_popup=1"
                return HttpResponseRedirect(post_url_continue % pk_value)
            if request.POST.has_key("_popup"):
                return HttpResponse('<script type="text/javascript">opener.dismissAddAnotherPopup(window, %s, "%s");</script>' % \
                    (pk_value, repr(new_object).replace('"', '\\"')))
            elif request.POST.has_key("_addanother"):
                request.user.add_message("%s You may add another %s below." % (msg, opts.verbose_name))
                return HttpResponseRedirect(request.path)
            else:
                request.user.add_message(msg)
                return HttpResponseRedirect(post_url)
    else:
        # Add default data.
        new_data = manipulator.flatten_data()
        
        # Override the defaults with request.GET, if it exists.
        new_data.update(request.GET)
        errors = {}

    # Populate the FormWrapper.
    form = formfields.FormWrapper(manipulator, new_data, errors, edit_inline=True)
    
    c = Context(request, {
        'title': 'Add %s' % opts.verbose_name,
        'form': form,
        'is_popup': request.REQUEST.has_key('_popup'),
    })
    if object_id_override is not None:
        c['object_id'] = object_id_override
    
    return render_change_form(opts, app_label, c, add=True)
add_stage = staff_member_required(add_stage)

def log_change_message(user, opts,manipulator,new_object):
    pk_value = getattr(new_object, opts.pk.column)
    # Construct the change message.
    change_message = []
    if manipulator.fields_added:
        change_message.append('Added %s.' % get_text_list(manipulator.fields_added, 'and'))
    if manipulator.fields_changed:
        change_message.append('Changed %s.' % get_text_list(manipulator.fields_changed, 'and'))
    if manipulator.fields_deleted:
        change_message.append('Deleted %s.' % get_text_list(manipulator.fields_deleted, 'and'))
    change_message = ' '.join(change_message)
    if not change_message:
        change_message = 'No fields changed.'
    log.log_action(user.id, opts.get_content_type_id(), pk_value, repr(new_object), log.CHANGE, change_message)
    
def change_stage(request, app_label, module_name, object_id):
    mod, opts = _get_mod_opts(app_label, module_name)
    if not request.user.has_perm(app_label + '.' + opts.get_change_permission()):
        raise PermissionDenied
    if request.POST and request.POST.has_key("_saveasnew"):
        return add_stage_new(request, app_label, module_name, form_url='../add/')
    try:
        manipulator = mod.ChangeManipulator(object_id)
    except ObjectDoesNotExist:
        raise Http404

    if request.POST:
        new_data = request.POST.copy()
        if opts.has_field_type(meta.FileField):
            new_data.update(request.FILES)

        errors = manipulator.get_validation_errors(new_data)
        
        manipulator.do_html2python(new_data)
        if not errors and not request.POST.has_key("_preview"):
            new_object = manipulator.save(new_data)
            log_change_message(request.user,opts,manipulator,new_object)
            msg = 'The %s "%s" was changed successfully.' % (opts.verbose_name, new_object)
            if request.POST.has_key("_continue"):
                request.user.add_message("%s You may edit it again below." % msg)
                if request.REQUEST.has_key('_popup'):
                    return HttpResponseRedirect(request.path + "?_popup=1")
                else:
                    return HttpResponseRedirect(request.path)
            elif request.POST.has_key("_saveasnew"):
                request.user.add_message('The %s "%s" was added successfully. You may edit it again below.' % (opts.verbose_name, new_object))
                return HttpResponseRedirect("../%s/" % pk_value)
            elif request.POST.has_key("_addanother"):
                request.user.add_message("%s You may add another %s below." % (msg, opts.verbose_name))
                return HttpResponseRedirect("../add/")
            else:
                request.user.add_message(msg)
                return HttpResponseRedirect("../")
    else:
        # Populate new_data with a "flattened" version of the current data.
        new_data = manipulator.flatten_data()
       
        # TODO: do this in flatten_data... 
        # If the object has ordered objects on its admin page, get the existing
        # order and flatten it into a comma-separated list of IDs.
        
        id_order_list = []
        for rel_obj in opts.get_ordered_objects():
            id_order_list.extend(getattr(obj, 'get_%s_order' % rel_obj.object_name.lower())())
        if id_order_list:
            new_data['order_'] = ','.join(map(str, id_order_list))
        errors = {}

    # Populate the FormWrapper.
    form = formfields.FormWrapper(manipulator, new_data, errors, edit_inline = True)
    form.original = manipulator.original_object
    form.order_objects = []
    
    #TODO Should be done in flatten_data  / FormWrapper construction
    for related in opts.get_followed_related_objects():
        wrt = related.opts.order_with_respect_to
        if wrt and wrt.rel and wrt.rel.to == opts: 
            func = getattr(manipulator.original_object, 'get_%s_list' % 
                    opts.get_rel_object_method_name(rel_opts, rel_field))
            orig_list = func()
            form.order_objects.extend(orig_list)
            
    c = Context(request, {
        'title': 'Change %s' % opts.verbose_name,
        'form': form,
        'object_id': object_id,
        'original': manipulator.original_object,
        'is_popup' : request.REQUEST.has_key('_popup')
    })

    return render_change_form(opts, app_label, c, change=True)
    
    

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
    objects_seen = []
    for related in opts.get_all_related_objects():
        if related.opts in objects_seen:
            continue
        objects_seen.append(rel_opts)
        rel_opts_name = opts.get_rel_object_method_name(related.opts, related.field)
        if isinstance(related.field.rel, meta.OneToOne):
            try:
                sub_obj = getattr(obj, 'get_%s' % rel_opts_name)()
            except ObjectDoesNotExist:
                pass
            else:
                if rel_opts.admin:
                    p = '%s.%s' % (related.opts.app_label, related.opts.get_delete_permission())
                    if not user.has_perm(p):
                        perms_needed.add(related.opts.verbose_name)
                        # We don't care about populating deleted_objects now.
                        continue
                if related.field.rel.edit_inline or not related.opts.admin:
                    # Don't display link to edit, because it either has no
                    # admin or is edited inline.
                    nh(deleted_objects, current_depth, ['%s: %r' % (capfirst(related.opts.verbose_name), sub_obj), []])
                else:
                    # Display a link to the admin page.
                    nh(deleted_objects, current_depth, ['%s: <a href="../../../../%s/%s/%s/">%r</a>' % \
                        (capfirst(related.opts.verbose_name), related.opts.app_label, related.opts.module_name,
                        getattr(sub_obj, related.opts.pk.column), sub_obj), []])
                _get_deleted_objects(deleted_objects, perms_needed, user, sub_obj, related.opts, current_depth+2)
        else:
            has_related_objs = False
            for sub_obj in getattr(obj, 'get_%s_list' % rel_opts_name)():
                has_related_objs = True
                if related.field.rel.edit_inline or not related.opts.admin:
                    # Don't display link to edit, because it either has no
                    # admin or is edited inline.
                    nh(deleted_objects, current_depth, ['%s: %s' % (capfirst(related.opts.verbose_name), strip_tags(repr(sub_obj))), []])
                else:
                    # Display a link to the admin page.
                    nh(deleted_objects, current_depth, ['%s: <a href="../../../../%s/%s/%s/">%s</a>' % \
                        (capfirst(related.opts.verbose_name), related.opts.app_label, related.opts.module_name, sub_obj.id, strip_tags(repr(sub_obj))), []])
                _get_deleted_objects(deleted_objects, perms_needed, user, sub_obj, related.opts, current_depth+2)
            # If there were related objects, and the user doesn't have
            # permission to delete them, add the missing perm to perms_needed.
            if related.opts.admin and has_related_objs:
                p = '%s.%s' % (related.opts.app_label, related.opts.get_delete_permission())
                if not user.has_perm(p):
                    perms_needed.add(rel_opts.verbose_name)
    for rel_opts, rel_field in opts.get_all_related_many_to_many_objects():
        if rel_opts in objects_seen:
            continue
        objects_seen.append(rel_opts)
        rel_opts_name = opts.get_rel_object_method_name(rel_opts, rel_field)
        has_related_objs = False
        for sub_obj in getattr(obj, 'get_%s_list' % rel_opts_name)():
            has_related_objs = True
            if rel_field.rel.edit_inline or not rel_opts.admin:
                # Don't display link to edit, because it either has no
                # admin or is edited inline.
                nh(deleted_objects, current_depth, ['One or more %s in %s: %s' % \
                    (rel_field.name, rel_opts.verbose_name, strip_tags(repr(sub_obj))), []])
            else:
                # Display a link to the admin page.
                nh(deleted_objects, current_depth, ['One or more %s in %s: <a href="../../../../%s/%s/%s/">%s</a>' % \
                    (rel_field.name, rel_opts.verbose_name, rel_opts.app_label, rel_opts.module_name, sub_obj.id, strip_tags(repr(sub_obj))), []])
        # If there were related objects, and the user doesn't have
        # permission to change them, add the missing perm to perms_needed.
        if rel_opts.admin and has_related_objs:
            p = '%s.%s' % (rel_opts.app_label, rel_opts.get_change_permission())
            if not user.has_perm(p):
                perms_needed.add(rel_opts.verbose_name)

def delete_stage(request, app_label, module_name, object_id):
    import sets
    mod, opts = _get_mod_opts(app_label, module_name)
    if not request.user.has_perm(app_label + '.' + opts.get_delete_permission()):
        raise PermissionDenied
    obj = get_object_or_404(mod, pk=object_id)

    # Populate deleted_objects, a data structure of all related objects that
    # will also be deleted.
    deleted_objects = ['%s: <a href="../../%s/">%s</a>' % (capfirst(opts.verbose_name), object_id, strip_tags(repr(obj))), []]
    perms_needed = sets.Set()
    _get_deleted_objects(deleted_objects, perms_needed, request.user, obj, opts, 1)

    if request.POST: # The user has already confirmed the deletion.
        if perms_needed:
            raise PermissionDenied
        obj_repr = repr(obj)
        obj.delete()
        log.log_action(request.user.id, opts.get_content_type_id(), object_id, obj_repr, log.DELETION)
        request.user.add_message('The %s "%s" was deleted successfully.' % (opts.verbose_name, obj_repr))
        return HttpResponseRedirect("../../")
    return render_to_response('admin/delete_confirmation', {
        "title": "Are you sure?",
        "object_name": opts.verbose_name,
        "object": obj,
        "deleted_objects": deleted_objects,
        "perms_lacking": perms_needed,
    }, context_instance=Context(request))
delete_stage = staff_member_required(delete_stage)

def history(request, app_label, module_name, object_id):
    mod, opts = _get_mod_opts(app_label, module_name)
    action_list = log.get_list(object_id__exact=object_id, content_type__id__exact=opts.get_content_type_id(),
        order_by=("action_time",), select_related=True)
    # If no history was found, see whether this object even exists.
    obj = get_object_or_404(mod, pk=object_id)
    return render_to_response('admin/object_history', {
        'title': 'Change history: %r' % obj,
        'action_list': action_list,
        'module_name': capfirst(opts.verbose_name_plural),
        'object': obj,
    }, context_instance=Context(request))
history = staff_member_required(history)
