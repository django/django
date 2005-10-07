# Generic admin views, with admin templates created dynamically at runtime.

from django.core import formfields, meta, template_loader, template
from django.core.exceptions import Http404, ObjectDoesNotExist, PermissionDenied
from django.core.extensions import DjangoContext as Context
from django.core.extensions import get_object_or_404, render_to_response
from django.models.auth import log
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
    return render_to_response('index', {'title': 'Site administration'}, context_instance=Context(request))

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
                for k, v in (('All', None), ('Yes', 'True'), ('No', 'False')):
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

    raw_template = ['{% extends "base_site" %}\n']
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
    t = template_loader.get_template_from_string(''.join(raw_template))
    c = Context(request, {
        'title': (is_popup and 'Select %s' % opts.verbose_name or 'Select %s to change' % opts.verbose_name),
        'is_popup': is_popup,
    })
    return HttpResponse(t.render(c))

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

def get_javascript_imports(opts,auto_populated_fields, ordered_objects, admin_field_objs):
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
    for _, options in admin_field_objs:
        if not seen_collapse and 'collapse' in options.get('classes', ''):
            seen_collapse = True
            js.append('js/admin/CollapsedFieldsets.js' )
        try:
            for field_list in options['fields']:
                for f in field_list:
                    if f.rel and isinstance(f, meta.ManyToManyField) and f.rel.filter_interface:
                        js.extend(['js/SelectBox.js' , 'js/SelectFilter2.js'])
                        raise StopIteration
        except StopIteration:
            break
    return js

class BoundField(object):
    def __init__(self, field, original, rel, field_mapping):
        self.field = field
        self.form_fields = self.resolve_form_fields(field_mapping)
        self.original = original
        self.rel = rel

    def resolve_form_fields(self, field_mapping):
        return [field_mapping[name] for name in self.field.get_manipulator_field_names('')]

    def as_field_list(self):
        return [self.field]

    def original_value(self):
        return self.original.__dict__[self.field.name] 
 
class AdminBoundField(BoundField):
    def __init__(self, field, original, rel, field_mapping):
        super(AdminBoundField, self).__init__(field,original, rel, field_mapping) 	

        self.element_id = self.form_fields[0].get_id() 
        self.has_label_first = not isinstance(self.field, meta.BooleanField)
        self.raw_id_admin = use_raw_id_admin(field)
        self.is_date_time = isinstance(field, meta.DateTimeField)
        self.is_file_field = isinstance(field, meta.FileField)
        self.needs_add_label = field.rel and isinstance(field.rel, meta.ManyToOne) or isinstance(field.rel, meta.ManyToMany) and field.rel.to.admin
        self.not_in_table = isinstance(self.field, meta.AutoField)
        self.first = True
        
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


class AdminFieldSet(object):
    def __init__(self, fieldset_name, options, form, original):
         self.name = fieldset_name
	 self.options = options
         self.bound_field_sets = self.get_bound_field_sets(form, original)
         self.classes = options.get('classes', '')
     
    def __repr__(self):
     	return "Fieldset:(%s,%s)" % (self.name, self.bound_field_sets)

    def get_bound_field_sets(self, form, original):
        fields = self.options['fields']
        bound_field_sets = [ [AdminBoundField(f, original, False, form) for f in field  ] for field in fields]
        for set in bound_field_sets:
            first = True 
            for bound_field in set:
                bound_field.first = first
                first = False

        return bound_field_sets

def fill_extra_context(opts, app_label, context, add=False, change=False, show_delete=False, form_url=''):
    admin_field_objs = opts.admin.get_field_objs(opts)
    ordered_objects = opts.get_ordered_objects()[:]
    auto_populated_fields = [f for f in opts.fields if f.prepopulate_from]
 
    javascript_imports = get_javascript_imports(opts,auto_populated_fields, ordered_objects, admin_field_objs);
    
    if ordered_objects:
        coltype = 'colMS'
    else:
        coltype = 'colM'
	
    has_absolute_url = hasattr(opts.get_model_module().Klass, 'get_absolute_url')
    
    form_enc_attrib = opts.has_field_type(meta.FileField) and 'enctype="multipart/form-data" ' or ''

    form = context['form']
    original = context['original']
    admin_fieldsets = [AdminFieldSet(name, options, form, original) for name, options in admin_field_objs] 
    inline_related_objects = opts.get_inline_related_objects_wrapped()
    
    ordered_object_names =   ' '.join(['object.%s' % o.pk.name for o in ordered_objects])
   
    extra_context = {
        'add': add, 
        'change': change, 
        'admin_field_objs' : admin_field_objs, 
        'ordered_objects' : ordered_objects, 
        'auto_populated_fields' : auto_populated_fields,
        'javascript_imports' : javascript_imports, 
        'coltype' : coltype, 
        'has_absolute_url': has_absolute_url, 
        'form_enc_attrib': form_enc_attrib,
        'form_url' : form_url, 
        'admin_fieldsets' : admin_fieldsets, 
        'inline_related_objects': inline_related_objects,
        'ordered_object_names' : ordered_object_names, 
        'content_type_id' : opts.get_content_type_id(),
        'save_on_top' : opts.admin.save_on_top,
        'verbose_name_plural': opts.verbose_name_plural, 
        'save_as': opts.admin.save_as, 
        'app_label': app_label,
        'object_name': opts.object_name,
        'has_delete_permission' : context['perms'][app_label][opts.get_delete_permission()]
    }
    
    context.update(extra_context)   
   
   
def add_stage_new(request, app_label, module_name, show_delete=False, form_url='', post_url='../', post_url_continue='../%s/', object_id_override=None):
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
            for f in opts.many_to_many:
                if f.rel.raw_id_admin:
                    new_data.setlist(f.name, new_data[f.name].split(","))
            new_object = manipulator.save(new_data)
            pk_value = getattr(new_object, opts.pk.column)
            log.log_action(request.user.id, opts.get_content_type_id(), pk_value, repr(new_object), log.ADDITION)
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
       # if request.POST.has_key("_preview"):   # Always happens anyway. 
       #     manipulator.do_html2python(new_data)
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
    
    
    fill_extra_context(opts, app_label, c, change=True)
   
    return render_to_response("admin_change_form", context_instance=c) 



def change_stage_new(request, app_label, module_name, object_id):
    mod, opts = _get_mod_opts(app_label, module_name)
    if not request.user.has_perm(app_label + '.' + opts.get_change_permission()):
        raise PermissionDenied
    if request.POST and request.POST.has_key("_saveasnew"):
        return add_stage_new(request, app_label, module_name, form_url='../add/')
    try:
        manipulator = mod.ChangeManipulator(object_id)
    except ObjectDoesNotExist:
        raise Http404

    inline_related_objects = opts.get_inline_related_objects()
    if request.POST:
        new_data = request.POST.copy()
        if opts.has_field_type(meta.FileField):
            new_data.update(request.FILES)

        errors = manipulator.get_validation_errors(new_data)
        
        manipulator.do_html2python(new_data)
        if not errors and not request.POST.has_key("_preview"):
        # Now done in commaseparatedint
        #    for f in opts.many_to_many: 
        #        if f.rel.raw_id_admin:
        #            new_data.setlist(f.name, new_data[f.name].split(","))
            new_object = manipulator.save(new_data)
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

            log.log_action(request.user.id, opts.get_content_type_id(), pk_value, repr(new_object), log.CHANGE, change_message)
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
       # if request.POST.has_key("_preview"):  # always happens
       #     manipulator.do_html2python(new_data)
    else:
        # Populate new_data with a "flattened" version of the current data.
        new_data = manipulator.flatten_data()
       
 
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
    
    for rel_opts, rel_field in inline_related_objects:
        if rel_opts.order_with_respect_to and rel_opts.order_with_respect_to.rel and rel_opts.order_with_respect_to.rel.to == opts:
            form.order_objects.extend(orig_list)

    c = Context(request, {
        'title': 'Change %s' % opts.verbose_name,
        'form': form,
        'object_id': object_id,
        'original': manipulator.original_object,
        'is_popup' : request.REQUEST.has_key('_popup')
    })

    fill_extra_context(opts, app_label, c, change=True)
    
    #t = template_loader.get_template_from_string(raw_template)
    
    return render_to_response('admin_change_form', context_instance=c);


def _get_template(opts, app_label, add=False, change=False, show_delete=False, form_url=''):
    admin_field_objs = opts.admin.get_field_objs(opts)
    ordered_objects = opts.get_ordered_objects()[:]
    auto_populated_fields = [f for f in opts.fields if f.prepopulate_from]
    t = ['{% extends "base_site" %}\n']
    t.append('{% block extrahead %}')

    # Put in any necessary JavaScript imports.
    javascript_imports = ['%sjs/core.js' % ADMIN_MEDIA_PREFIX, '%sjs/admin/RelatedObjectLookups.js' % ADMIN_MEDIA_PREFIX]
    if auto_populated_fields:
        javascript_imports.append('%sjs/urlify.js' % ADMIN_MEDIA_PREFIX)
    if opts.has_field_type(meta.DateTimeField) or opts.has_field_type(meta.TimeField) or opts.has_field_type(meta.DateField):
        javascript_imports.extend(['%sjs/calendar.js' % ADMIN_MEDIA_PREFIX, '%sjs/admin/DateTimeShortcuts.js' % ADMIN_MEDIA_PREFIX])
    if ordered_objects:
        javascript_imports.extend(['%sjs/getElementsBySelector.js' % ADMIN_MEDIA_PREFIX, '%sjs/dom-drag.js' % ADMIN_MEDIA_PREFIX, '%sjs/admin/ordering.js' % ADMIN_MEDIA_PREFIX])
    if opts.admin.js:
        javascript_imports.extend(opts.admin.js)
    seen_collapse = False
    for _, options in admin_field_objs:
        if not seen_collapse and 'collapse' in options.get('classes', ''):
            seen_collapse = True
            javascript_imports.append('%sjs/admin/CollapsedFieldsets.js' % ADMIN_MEDIA_PREFIX)
        try:
            for field_list in options['fields']:
                for f in field_list:
                    if f.rel and isinstance(f, meta.ManyToManyField) and f.rel.filter_interface:
                        javascript_imports.extend(['%sjs/SelectBox.js' % ADMIN_MEDIA_PREFIX, '%sjs/SelectFilter2.js' % ADMIN_MEDIA_PREFIX])
                        raise StopIteration
        except StopIteration:
            break
    for j in javascript_imports:
        t.append('<script type="text/javascript" src="%s"></script>' % j)

    t.append('{% endblock %}\n')
    if ordered_objects:
        coltype = 'colMS'
    else:
        coltype = 'colM'
    t.append('{%% block coltype %%}%s{%% endblock %%}\n' % coltype)
    t.append('{%% block bodyclass %%}%s-%s change-form{%% endblock %%}\n' % (app_label, opts.object_name.lower()))
    breadcrumb_title = add and "Add %s" % opts.verbose_name or '{{ original|striptags|truncatewords:"18" }}'
    t.append('{%% block breadcrumbs %%}{%% if not is_popup %%}<div class="breadcrumbs"><a href="../../../">Home</a> &rsaquo; <a href="../">%s</a> &rsaquo; %s</div>{%% endif %%}{%% endblock %%}\n' % \
        (capfirst(opts.verbose_name_plural), breadcrumb_title))
    t.append('{% block content %}<div id="content-main">\n')
    if change:
        t.append('{% if not is_popup %}')
        t.append('<ul class="object-tools"><li><a href="history/" class="historylink">History</a></li>')
        if hasattr(opts.get_model_module().Klass, 'get_absolute_url'):
            t.append('<li><a href="/r/%s/{{ object_id }}/" class="viewsitelink">View on site</a></li>' % opts.get_content_type_id())
        t.append('</ul>\n')
        t.append('{% endif %}')
    t.append('<form ')
    if opts.has_field_type(meta.FileField):
        t.append('enctype="multipart/form-data" ')
    t.append('action="%s" method="post">\n' % form_url)
    t.append('{% if is_popup %}<input type="hidden" name="_popup" value="1">{% endif %}')
    if opts.admin.save_on_top:
        t.extend(_get_submit_row_template(opts, app_label, add, change, show_delete, ordered_objects))
    t.append('{% if form.error_dict %}<p class="errornote">Please correct the error{{ form.error_dict.items|pluralize }} below.</p>{% endif %}\n')
    for fieldset_name, options in admin_field_objs:
        t.append('<fieldset class="module aligned %s">\n\n' % options.get('classes', ''))
        if fieldset_name:
            t.append('<h2>%s</h2>\n' % fieldset_name)
        for field_list in options['fields']:
            t.append(_get_admin_field(field_list, 'form.', False, add, change))
            for f in field_list:
                if f.rel and isinstance(f, meta.ManyToManyField) and f.rel.filter_interface:
                    t.append('<script type="text/javascript">addEvent(window, "load", function(e) { SelectFilter.init("id_%s", "%s", %s, %r); });</script>\n' % (f.name, f.verbose_name, f.rel.filter_interface-1, ADMIN_MEDIA_PREFIX))
        t.append('</fieldset>\n')
    if ordered_objects and change:
        t.append('<fieldset class="module"><h2>Ordering</h2>')
        t.append('<div class="form-row{% if form.order_.errors %} error{% endif %} ">\n')
        t.append('{% if form.order_.errors %}{{ form.order_.html_error_list }}{% endif %}')
        t.append('<p><label for="id_order_">Order:</label> {{ form.order_ }}</p>\n')
        t.append('</div></fieldset>\n')
    for rel_obj, rel_field in opts.get_inline_related_objects():
        var_name = rel_obj.object_name.lower()
        field_list = [f for f in rel_obj.fields + rel_obj.many_to_many if f.editable and f != rel_field]

        t.append('<fieldset class="module%s">\n' % ((rel_field.rel.edit_inline != meta.TABULAR) and ' aligned' or ''))
        view_on_site = ''
        if change and hasattr(rel_obj, 'get_absolute_url'):
            view_on_site = '{%% if %s.original %%}<a href="/r/{{ %s.content_type_id }}/{{ %s.original.id }}/">View on site</a>{%% endif %%}' % (var_name, var_name, var_name)
        if rel_field.rel.edit_inline == meta.TABULAR:
            t.append('<h2>%s</h2>\n<table>\n' % capfirst(rel_obj.verbose_name_plural))
            t.append('<thead><tr>')
            for f in field_list:
                if isinstance(f, meta.AutoField):
                    continue
                t.append('<th%s>%s</th>' % (f.blank and ' class="optional"' or '', capfirst(f.verbose_name)))
            t.append('</tr></thead>\n')
            t.append('{%% for %s in form.%s %%}\n' % (var_name, rel_obj.module_name))
            if change:
                for f in field_list:
                    if use_raw_id_admin(f):
                        t.append('{%% if %s.original %%}' % var_name)
                        t.append('<tr class="row-label {% cycle row1,row2 %}">')
                        t.append('<td colspan="%s"><strong>{{ %s.original }}</strong></td>' % (30, var_name))
                        t.append('</tr>{% endif %}\n')
                        break
            t.append('{%% if %s %%}\n' % ' or '.join(['%s.%s.errors' % (var_name, f.name) for f in field_list]))
            t.append('<tr class="errorlist"><td colspan="%s">%s</td></tr>\n{%% endif %%}\n' % \
                (len(field_list), ''.join(['{{ %s.%s.html_error_list }}' % (var_name, f.name) for f in field_list])))
            t.append('<tr class="{% cycle row1,row2 %}">\n')
            hidden_fields = []
            for f in field_list:
                form_widget = _get_admin_field_form_widget(f, var_name+'.', True, add, change)
                # Don't put AutoFields within a <td>, because they're hidden.
                if not isinstance(f, meta.AutoField):
                    # Fields with raw_id_admin=True get class="nowrap".
                    if use_raw_id_admin(f):
                        t.append('<td class="nowrap {%% if %s.%s.errors %%}error"{%% endif %%}">%s</td>\n' % (var_name, f.name, form_widget))
                    else:
                        t.append('<td{%% if %s.%s.errors %%} class="error"{%% endif %%}>%s</td>\n' % (var_name, f.name, form_widget))
                else:
                    hidden_fields.append(form_widget)
            if hasattr(rel_obj, 'get_absolute_url'):
                t.append('<td>%s</td>\n' % view_on_site)
            t.append('</tr>\n')
            t.append('{% endfor %}\n</table>\n')
            # Write out the hidden fields. We didn't write them out earlier
            # because it would've been invalid HTML.
            t.append('{%% for %s in form.%s %%}\n' % (var_name, rel_obj.module_name))
            t.extend(hidden_fields)
            t.append('{% endfor %}\n')
        else: # edit_inline == STACKED
            t.append('{%% for %s in form.%s %%}' % (var_name, rel_obj.module_name))
            t.append('<h2>%s #{{ forloop.counter }}</h2>' % capfirst(rel_obj.verbose_name))
            if view_on_site:
                t.append('<p>%s</p>' % view_on_site)
            for f in field_list:
                # Don't put AutoFields within the widget -- just use the field.
                if isinstance(f, meta.AutoField):
                    t.append(_get_admin_field_form_widget(f, var_name+'.', True, add, change))
                else:
                    t.append(_get_admin_field([f], var_name+'.', True, add, change))
            t.append('{% endfor %}\n')
        t.append('</fieldset>\n')
    t.extend(_get_submit_row_template(opts, app_label, add, change, show_delete, ordered_objects))
    if add:
        # Add focus to the first field on the form, if this is an "add" form.
        t.append('<script type="text/javascript">document.getElementById("id_%s").focus();</script>' % \
            admin_field_objs[0][1]['fields'][0][0].get_manipulator_field_names('')[0])
    if auto_populated_fields:
        t.append('<script type="text/javascript">')
        for field in auto_populated_fields:
            if change:
                t.append('document.getElementById("id_%s")._changed = true;' % field.name)
            else:
                t.append('document.getElementById("id_%s").onchange = function() { this._changed = true; };' % field.name)
            for f in field.prepopulate_from:
                t.append('document.getElementById("id_%s").onkeyup = function() { var e = document.getElementById("id_%s"); if (!e._changed) { e.value = URLify(%s, %s);}};' % \
                    (f, field.name, ' + " " + '.join(['document.getElementById("id_%s").value' % g for g in field.prepopulate_from]), field.maxlength))
        t.append('</script>\n')
    if change and ordered_objects:
        t.append('{% if form.order_objects %}<ul id="orderthese">{% for object in form.order_objects %}')
        t.append('<li id="p{%% firstof %(x)s %%}"><span id="handlep{%% firstof %(x)s %%}">{{ object|truncatewords:"5" }}</span></li>' % \
            {'x': ' '.join(['object.%s' % o.pk.name for o in ordered_objects])})
        t.append('{% endfor %}</ul>{% endif %}\n')
    t.append('</form>\n</div>\n{% endblock %}')
    return ''.join(t)

def _get_admin_field(field_list, name_prefix, rel, add, change):
    "Returns the template code for editing the given list of fields in the admin template."
    field_names = []
    for f in field_list:
        field_names.extend(f.get_manipulator_field_names(name_prefix))
    div_class_names = ['form-row', '{%% if %s %%} error{%% endif %%}' % ' or '.join(['%s.errors' % n for n in field_names])]
    # Assumes BooleanFields won't be stacked next to each other!
    if isinstance(field_list[0], meta.BooleanField):
        div_class_names.append('checkbox-row')
    t = []
    t.append('<div class="%s">\n' % ' '.join(div_class_names))
    for n in field_names:
        t.append('{%% if %s.errors %%}{{ %s.html_error_list }}{%% endif %%}\n' % (n, n))
    for i, field in enumerate(field_list):
        label_name = 'id_%s%s' % ((rel and "%s{{ forloop.counter0 }}." % name_prefix or ""), field.get_manipulator_field_names('')[0])
        # BooleanFields are a special case, because the checkbox widget appears to
        # the *left* of the label.
        if isinstance(field, meta.BooleanField):
            t.append(_get_admin_field_form_widget(field, name_prefix, rel, add, change))
            t.append(' <label for="%s" class="vCheckboxLabel">%s</label>' % (label_name, capfirst(field.verbose_name)))
        else:
            class_names = []
            if not field.blank:
                class_names.append('required')
            if i > 0:
                class_names.append('inline')
            t.append('<label for="%s"%s>%s:</label> ' % (label_name, class_names and ' class="%s"' % ' '.join(class_names) or '', capfirst(field.verbose_name)))
            t.append(_get_admin_field_form_widget(field, name_prefix, rel, add, change))
        if change and field.primary_key:
            t.append('{{ %soriginal.%s }}' % ((rel and name_prefix or ''), field.name))
        if change and use_raw_id_admin(field):
            if isinstance(field.rel, meta.ManyToOne):
                if_bit = '%soriginal.get_%s' % (rel and name_prefix or '', field.name)
                obj_repr = if_bit + '|truncatewords:"14"'
            elif isinstance(field.rel, meta.ManyToMany):
                if_bit = '%soriginal.get_%s_list' % (rel and name_prefix or '', field.name)
                obj_repr = if_bit + '|join:", "|truncatewords:"14"'
            t.append('{%% if %s %%}&nbsp;<strong>{{ %s }}</strong>{%% endif %%}' % (if_bit, obj_repr))
        if field.help_text:
            t.append('<p class="help">%s</p>\n' % field.help_text)
    t.append('</div>\n\n')
    return ''.join(t)

def _get_admin_field_form_widget(field, name_prefix, rel, add, change):
    "Returns JUST the formfield widget for the field's admin interface."
    field_names = field.get_manipulator_field_names(name_prefix)
    if isinstance(field, meta.DateTimeField):
        return '<p class="datetime">Date: {{ %s }}<br />Time: {{ %s }}</p>' % tuple(field_names)
    t = ['{{ %s }}' % n for n in field_names]
    if change and isinstance(field, meta.FileField):
        return '{%% if %soriginal.%s %%}Currently: <a href="{{ %soriginal.get_%s_url }}">{{ %soriginal.%s }}</a><br />Change: %s{%% else %%}%s{%% endif %%}' % \
            (name_prefix, field.name, name_prefix, field.name, name_prefix, field.name, ''.join(t), ''.join(t))
    field_id = 'id_%s%s' % ((rel and "%s{{ forloop.counter0 }}." % name_prefix or ""), field.get_manipulator_field_names('')[0])
    # raw_id_admin fields get the little lookup link next to them
    if use_raw_id_admin(field):
        t.append(' <a href="../../../%s/%s/" class="related-lookup" id="lookup_%s" onclick="return showRelatedObjectLookupPopup(this);">' % \
                    (field.rel.to.app_label, field.rel.to.module_name, field_id))
        t.append('<img src="%simg/admin/selector-search.gif" width="16" height="16" alt="Lookup" /></a>' % ADMIN_MEDIA_PREFIX)
    # fields with relationships to editable objects get an "add another" link,
    # but only if the field doesn't have raw_admin ('cause in that case they get
    # the "add" button in the popup)
    elif field.rel and (isinstance(field.rel, meta.ManyToOne) or isinstance(field.rel, meta.ManyToMany)) and field.rel.to.admin:
        t.append('{%% if perms.%s.%s %%}' % (field.rel.to.app_label, field.rel.to.get_add_permission()))
        t.append(' <a href="../../../%s/%s/add/" class="add-another" id="add_%s" onclick="return showAddAnotherPopup(this);">' % \
                    (field.rel.to.app_label, field.rel.to.module_name, field_id))
        t.append('<img src="%simg/admin/icon_addlink.gif" width="10" height="10" alt="Add Another" /></a>' % ADMIN_MEDIA_PREFIX)
        t.append('{% endif %}')
    return ''.join(t)

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
        if not errors and not request.POST.has_key("_preview"):
            for f in opts.many_to_many:
                if f.rel.raw_id_admin:
                    new_data.setlist(f.name, new_data[f.name].split(","))
            manipulator.do_html2python(new_data)
            new_object = manipulator.save(new_data)
            pk_value = getattr(new_object, opts.pk.column)
            log.log_action(request.user.id, opts.get_content_type_id(), pk_value, repr(new_object), log.ADDITION)
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
        if request.POST.has_key("_preview"):
            manipulator.do_html2python(new_data)
    else:
        new_data = {}
        # Add default data.
        for f in opts.fields:
            if f.has_default():
                new_data.update( f.flatten_data() )
            # In required many-to-one fields with only one available choice,
            # select that one available choice. Note: We have to check that
            # the length of choices is *2*, not 1, because SelectFields always
            # have an initial "blank" value.
            elif not f.blank and ((isinstance(f.rel, meta.ManyToOne) and not f.rel.raw_id_admin) or f.choices) and len(manipulator[f.name].choices) == 2:
                new_data[f.name] = manipulator[f.name].choices[1][0]
        # In required many-to-many fields with only one available choice,
        # select that one available choice.
        for f in opts.many_to_many:
            if not f.blank and not f.rel.edit_inline and not f.rel.raw_id_admin and len(manipulator[f.name].choices) == 1:
                new_data[f.name] = [manipulator[f.name].choices[0][0]]
        # Add default data for related objects.
        for rel_opts, rel_field in opts.get_inline_related_objects():
            var_name = rel_opts.object_name.lower()
            for i in range(rel_field.rel.num_in_admin):
                for f in rel_opts.fields + rel_opts.many_to_many:
                    if f.has_default():
                        for field_name in f.get_manipulator_field_names(''):
                            new_data['%s.%d.%s' % (var_name, i, field_name)] = f.get_default()
        # Override the defaults with request.GET, if it exists.
        new_data.update(request.GET)
        errors = {}

    # Populate the FormWrapper.
    form = formfields.FormWrapper(manipulator, new_data, errors)
    for rel_opts, rel_field in opts.get_inline_related_objects():
        var_name = rel_opts.object_name.lower()
        wrapper = []
        for i in range(rel_field.rel.num_in_admin):
            collection = {}
            for f in rel_opts.fields + rel_opts.many_to_many:
                if f.editable and f != rel_field and not isinstance(f, meta.AutoField):
                    for field_name in f.get_manipulator_field_names(''):
                        full_field_name = '%s.%d.%s' % (var_name, i, field_name)
			field = manipulator[full_field_name]
			data = field.extract_data(new_data)
                        collection[field_name] = formfields.FormFieldWrapper(field, data, errors.get(full_field_name, []))
            wrapper.append(formfields.FormFieldCollection(collection))
        setattr(form, rel_opts.module_name, wrapper)

    c = Context(request, {
        'title': 'Add %s' % opts.verbose_name,
        "form": form,
        "is_popup": request.REQUEST.has_key("_popup"),
    })
    if object_id_override is not None:
        c['object_id'] = object_id_override
    raw_template = _get_template(opts, app_label, add=True, show_delete=show_delete, form_url=form_url)
    t = template_loader.get_template_from_string(raw_template)
    return HttpResponse(t.render(c))

def change_stage(request, app_label, module_name, object_id):
    mod, opts = _get_mod_opts(app_label, module_name)
    if not request.user.has_perm(app_label + '.' + opts.get_change_permission()):
        raise PermissionDenied
    if request.POST and request.POST.has_key("_saveasnew"):
        return add_stage(request, app_label, module_name, form_url='../add/')
    try:
        manipulator = mod.ChangeManipulator(object_id)
    except ObjectDoesNotExist:
        raise Http404

    inline_related_objects = opts.get_inline_related_objects()
    if request.POST:
        new_data = request.POST.copy()
        if opts.has_field_type(meta.FileField):
            new_data.update(request.FILES)

        errors = manipulator.get_validation_errors(new_data)
        if not errors and not request.POST.has_key("_preview"):
            for f in opts.many_to_many:
                if f.rel.raw_id_admin:
                    new_data.setlist(f.name, new_data[f.name].split(","))
            manipulator.do_html2python(new_data)
            new_object = manipulator.save(new_data)
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

            log.log_action(request.user.id, opts.get_content_type_id(), pk_value, repr(new_object), log.CHANGE, change_message)
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
        if request.POST.has_key("_preview"):
            manipulator.do_html2python(new_data)
    else:
        # Populate new_data with a "flattened" version of the current data.
        new_data = {}
        obj = manipulator.original_object
        for f in opts.fields:
            new_data.update(f.flatten_data(obj))
        for f in opts.many_to_many:
            get_list_func = getattr(obj, 'get_%s_list' % f.rel.singular)
            if f.rel.raw_id_admin:
                new_data[f.name] = ",".join([str(getattr(i, f.rel.to.pk.column)) for i in get_list_func()])
            elif not f.rel.edit_inline:
                new_data[f.name] = [getattr(i, f.rel.to.pk.column) for i in get_list_func()]
        for rel_obj, rel_field in inline_related_objects:
            var_name = rel_obj.object_name.lower()
            for i, rel_instance in enumerate(getattr(obj, 'get_%s_list' % opts.get_rel_object_method_name(rel_obj, rel_field))()):
                for f in rel_obj.fields:
                    if f.editable and f != rel_field:
                        for k, v in f.flatten_data(rel_instance).items():
                            new_data['%s.%d.%s' % (var_name, i, k)] = v
                for f in rel_obj.many_to_many:
                    new_data['%s.%d.%s' % (var_name, i, f.column)] = [j.id for j in getattr(rel_instance, 'get_%s_list' % f.rel.singular)()]

        # If the object has ordered objects on its admin page, get the existing
        # order and flatten it into a comma-separated list of IDs.
        id_order_list = []
        for rel_obj in opts.get_ordered_objects():
            id_order_list.extend(getattr(obj, 'get_%s_order' % rel_obj.object_name.lower())())
        if id_order_list:
            new_data['order_'] = ','.join(map(str, id_order_list))
        errors = {}

    # Populate the FormWrapper.
    form = formfields.FormWrapper(manipulator, new_data, errors)
    form.original = manipulator.original_object
    form.order_objects = []
    for rel_opts, rel_field in inline_related_objects:
        var_name = rel_opts.object_name.lower()
        wrapper = []
        orig_list = getattr(manipulator.original_object, 'get_%s_list' % opts.get_rel_object_method_name(rel_opts, rel_field))()
        count = len(orig_list) + rel_field.rel.num_extra_on_change
        if rel_field.rel.min_num_in_admin:
            count = max(count, rel_field.rel.min_num_in_admin)
        if rel_field.rel.max_num_in_admin:
            count = min(count, rel_field.rel.max_num_in_admin)
        for i in range(count):
            collection = {'original': (i < len(orig_list) and orig_list[i] or None)}
            for f in rel_opts.fields + rel_opts.many_to_many:
                if f.editable and f != rel_field:
                    for field_name in f.get_manipulator_field_names(''):
                        full_field_name = '%s.%d.%s' % (var_name, i, field_name)
			field = manipulator[full_field_name]
			data = field.extract_data(new_data)
                        collection[field_name] = formfields.FormFieldWrapper(field, data, errors.get(full_field_name, []))
            wrapper.append(formfields.FormFieldCollection(collection))
        setattr(form, rel_opts.module_name, wrapper)
        if rel_opts.order_with_respect_to and rel_opts.order_with_respect_to.rel and rel_opts.order_with_respect_to.rel.to == opts:
            form.order_objects.extend(orig_list)

    c = Context(request, {
        'title': 'Change %s' % opts.verbose_name,
        "form": form,
        'object_id': object_id,
        'original': manipulator.original_object,
        'is_popup' : request.REQUEST.has_key('_popup'),
    })
    raw_template = _get_template(opts, app_label, change=True)
#     return HttpResponse(raw_template, mimetype='text/plain')
    t = template_loader.get_template_from_string(raw_template)
    return HttpResponse(t.render(c))

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
    for rel_opts, rel_field in opts.get_all_related_objects():
        if rel_opts in objects_seen:
            continue
        objects_seen.append(rel_opts)
        rel_opts_name = opts.get_rel_object_method_name(rel_opts, rel_field)
        if isinstance(rel_field.rel, meta.OneToOne):
            try:
                sub_obj = getattr(obj, 'get_%s' % rel_opts_name)()
            except ObjectDoesNotExist:
                pass
            else:
                if rel_opts.admin:
                    p = '%s.%s' % (rel_opts.app_label, rel_opts.get_delete_permission())
                    if not user.has_perm(p):
                        perms_needed.add(rel_opts.verbose_name)
                        # We don't care about populating deleted_objects now.
                        continue
                if rel_field.rel.edit_inline or not rel_opts.admin:
                    # Don't display link to edit, because it either has no
                    # admin or is edited inline.
                    nh(deleted_objects, current_depth, ['%s: %r' % (capfirst(rel_opts.verbose_name), sub_obj), []])
                else:
                    # Display a link to the admin page.
                    nh(deleted_objects, current_depth, ['%s: <a href="../../../../%s/%s/%s/">%r</a>' % \
                        (capfirst(rel_opts.verbose_name), rel_opts.app_label, rel_opts.module_name,
                        getattr(sub_obj, rel_opts.pk.column), sub_obj), []])
                _get_deleted_objects(deleted_objects, perms_needed, user, sub_obj, rel_opts, current_depth+2)
        else:
            has_related_objs = False
            for sub_obj in getattr(obj, 'get_%s_list' % rel_opts_name)():
                has_related_objs = True
                if rel_field.rel.edit_inline or not rel_opts.admin:
                    # Don't display link to edit, because it either has no
                    # admin or is edited inline.
                    nh(deleted_objects, current_depth, ['%s: %s' % (capfirst(rel_opts.verbose_name), strip_tags(repr(sub_obj))), []])
                else:
                    # Display a link to the admin page.
                    nh(deleted_objects, current_depth, ['%s: <a href="../../../../%s/%s/%s/">%s</a>' % \
                        (capfirst(rel_opts.verbose_name), rel_opts.app_label, rel_opts.module_name, sub_obj.id, strip_tags(repr(sub_obj))), []])
                _get_deleted_objects(deleted_objects, perms_needed, user, sub_obj, rel_opts, current_depth+2)
            # If there were related objects, and the user doesn't have
            # permission to delete them, add the missing perm to perms_needed.
            if rel_opts.admin and has_related_objs:
                p = '%s.%s' % (rel_opts.app_label, rel_opts.get_delete_permission())
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
    return render_to_response('delete_confirmation_generic', {
        "title": "Are you sure?",
        "object_name": opts.verbose_name,
        "object": obj,
        "deleted_objects": deleted_objects,
        "perms_lacking": perms_needed,
    }, context_instance=Context(request))

def history(request, app_label, module_name, object_id):
    mod, opts = _get_mod_opts(app_label, module_name)
    action_list = log.get_list(object_id__exact=object_id, content_type__id__exact=opts.get_content_type_id(),
        order_by=("action_time",), select_related=True)
    # If no history was found, see whether this object even exists.
    obj = get_object_or_404(mod, pk=object_id)
    return render_to_response('admin_object_history', {
        'title': 'Change history: %r' % obj,
        'action_list': action_list,
        'module_name': capfirst(opts.verbose_name_plural),
        'object': obj,
    }, context_instance=Context(request))
