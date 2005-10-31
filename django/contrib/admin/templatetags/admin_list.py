from django.core.template.decorators import simple_tag, inclusion_tag

from django.contrib.admin.views.main import MAX_SHOW_ALL_ALLOWED, DEFAULT_RESULTS_PER_PAGE, ALL_VAR, \
 ORDER_VAR, ORDER_TYPE_VAR, PAGE_VAR , SEARCH_VAR , IS_POPUP_VAR, EMPTY_CHANGELIST_VALUE

from django.core import meta
from django.utils.text import capfirst
from django.utils.html import strip_tags, escape
from django.core.exceptions import ObjectDoesNotExist
from django.conf.settings import ADMIN_MEDIA_PREFIX
from django.core import template
from django.utils import dateformat
DOT = '.'

class QueryStringNode(template.Node):
    def __init__(self, cl_var, override_vars, remove_vars):
        self.cl_var, self.override_vars, self.remove_vars = cl_var, override_vars, remove_vars
        
    def render(self, context):
        def res(var):
            return template.resolve_variable(var, context)
        
        cl = res(self.cl_var)
        overrides = dict([ (res(k), res(v)) for k,v in self.override_vars ])
        remove = [res(v) for v in self.remove_vars]
        return cl.get_query_string(overrides, remove)

def do_query_string(parser, token):
    bits = token.contents.split()[1:]
    in_override = False
    in_remove = False
    override_vars = []
    remove_vars = []
    cl_var = bits.pop(0)
    
    for word in bits:
        if in_override:
            if word == 'remove':
                in_remove = True
                in_override = False
            else:
                override_vars.append(word.split(':'))
        elif in_remove:
            remove_vars.append(word)
        else:
            if word == 'override':
                in_override = True
            elif word == 'remove':
                remove = True
    
    return QueryStringNode(cl_var, override_vars, remove_vars)

template.register_tag('query_string', do_query_string)          


#@simple_tag
def paginator_number(cl,i):
    if i == DOT:
       return '... '
    elif i == cl.page_num:
       return '<span class="this-page">%d</span> ' % (i+1) 
    else:
       return '<a href="%s"%s>%d</a> ' % (cl.get_query_string( {PAGE_VAR: i}), (i == paginator.pages-1 and ' class="end"' or ''), i+1) 
paginator_number = simple_tag(paginator_number)

#@inclusion_tag('admin/pagination')
def pagination(cl):
    paginator, page_num = cl.paginator, cl.page_num 
    
    pagination_required = (not cl.show_all or not cl.can_show_all) and cl.multi_page
    if not pagination_required:
        page_range = []
    else:
        ON_EACH_SIDE = 3
        ON_ENDS = 2
        
        # If there are 10 or fewer pages, display links to every page.
        # Otherwise, do some fancy
        if paginator.pages <= 10:
            page_range = range(paginator.pages)
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
            if page_num < (paginator.pages - ON_EACH_SIDE - ON_ENDS - 1):
                page_range.extend(range(page_num + 1, page_num + ON_EACH_SIDE + 1))
                page_range.append(DOT)
                page_range.extend(range(paginator.pages - ON_ENDS, paginator.pages))
            else:
                page_range.extend(range(page_num + 1, paginator.pages))

    return {'cl': cl,
             'pagination_required': pagination_required,
             'need_show_all_link': cl.can_show_all and not cl.show_all and cl.multi_page,
             'page_range': page_range, 
             'ALL_VAR': ALL_VAR,
             '1': 1
            }
pagination = inclusion_tag('admin/pagination')(pagination)

#@simple_tag
def result_list(cl):
    result_list, lookup_opts, mod, order_field, order_type, params, is_popup, opts = \
     cl.result_list, cl.lookup_opts, cl.mod, cl.order_field, cl.order_type, cl.params, cl.is_popup, cl.opts
    
    raw_template = []
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
                        cl.get_query_string( {ORDER_VAR: i, ORDER_TYPE_VAR: new_order_type}),
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
    return ''.join(raw_template)
result_list = simple_tag(result_list)

#@simple_tag
def date_hierarchy(cl):
    lookup_opts, params, lookup_params, lookup_mod = \
      cl.lookup_opts, cl.params, cl.lookup_params, cl.lookup_mod
    
    raw_template = []
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
                (cl.get_query_string( {year_field: year_lookup, month_field: month_lookup}, [field_generic]), MONTHS[int(month_lookup)], year_lookup))
            raw_template.append('<li>%s %s</li>' % (MONTHS[int(month_lookup)], day_lookup))
        elif year_lookup and month_lookup:
            raw_template.append('<li class="date-back"><a href="%s">&lsaquo; %s</a></li>' % \
                (cl.get_query_string( {year_field: year_lookup}, [field_generic]), year_lookup))
            date_lookup_params = lookup_params.copy()
            date_lookup_params.update({year_field: year_lookup, month_field: month_lookup})
            for day in getattr(lookup_mod, 'get_%s_list' % field_name)('day', **date_lookup_params):
                raw_template.append('<li><a href="%s">%s</a></li>' % \
                    (cl.get_query_string({year_field: year_lookup, month_field: month_lookup, day_field: day.day}, [field_generic]), day.strftime('%B %d')))
        elif year_lookup:
            raw_template.append('<li class="date-back"><a href="%s">&lsaquo; All dates</a></li>' % \
                cl.get_query_string( {}, [year_field]))
            date_lookup_params = lookup_params.copy()
            date_lookup_params.update({year_field: year_lookup})
            for month in getattr(lookup_mod, 'get_%s_list' % field_name)('month', **date_lookup_params):
                raw_template.append('<li><a href="%s">%s %s</a></li>' % \
                    (cl.get_query_string( {year_field: year_lookup, month_field: month.month}, [field_generic]), month.strftime('%B'), month.year))
        else:
            for year in getattr(lookup_mod, 'get_%s_list' % field_name)('year', **lookup_params):
                raw_template.append('<li><a href="%s">%s</a></li>\n' % \
                    (cl.get_query_string( {year_field: year.year}, [field_generic]), year.year))
        raw_template.append('</ul><br class="clear" />\n</div>\n')
    return ''.join(raw_template)
date_hierarchy = simple_tag(date_hierarchy)

#@inclusion_tag('admin/search_form')
def search_form(cl):
    return { 'cl': cl,
             'show_result_count': cl.result_count != cl.full_result_count and not cl.opts.one_to_one_field, 
             'search_var': SEARCH_VAR }
search_form = inclusion_tag('admin/search_form')(search_form)

#@simple_tag
def output_filter_spec(cl, spec):
    return spec.output(cl)
output_filter_spec = simple_tag(output_filter_spec)

#@inclusion_tag('admin/filters')
def filters(cl):
    return {'cl': cl}
filters = inclusion_tag('admin/filters')(filters)