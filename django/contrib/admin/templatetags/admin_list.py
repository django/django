from django.core.template.decorators import simple_tag, inclusion_tag

from django.contrib.admin.views.main import MAX_SHOW_ALL_ALLOWED, DEFAULT_RESULTS_PER_PAGE, ALL_VAR, \
 ORDER_VAR, ORDER_TYPE_VAR, PAGE_VAR , SEARCH_VAR , IS_POPUP_VAR, EMPTY_CHANGELIST_VALUE, \
 MONTHS

from django.conf.settings import DATE_FORMAT, TIME_FORMAT, DATETIME_FORMAT

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
       return '<a href="%s"%s>%d</a> ' % (cl.get_query_string( {PAGE_VAR: i}), (i == cl.paginator.pages-1 and ' class="end"' or ''), i+1) 
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


def result_headers(cl):
    lookup_opts = cl.lookup_opts
    
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
                    func = getattr(cl.mod.Klass, field_name) # Let AttributeErrors propogate.
                    try:
                        header = func.short_description
                    except AttributeError:
                        header = func.__name__
                # Non-field list_display values don't get ordering capability.
                yield {"text": header}
            else:
                if isinstance(f.rel, meta.ManyToOne) and f.null:
                    yield {"text": f.verbose_name}
                else:
                    th_classes = []
                    new_order_type = 'asc'
                    if field_name == cl.order_field:
                        th_classes.append('sorted %sending' % cl.order_type.lower())
                        new_order_type = {'asc': 'desc', 'desc': 'asc'}[cl.order_type.lower()]
                    
                    yield {"text" : f.verbose_name, 
                           "sortable": True,
                           "order" : new_order_type,
                           "class_attrib" : (th_classes and ' class="%s"' % ' '.join(th_classes) or '') }
    
def items_for_result(cl, result):
    first = True
    pk = cl.lookup_opts.pk.attname
    for field_name in cl.lookup_opts.admin.list_display:
        row_class = ''
        try:
            f = cl.lookup_opts.get_field(field_name)
        except meta.FieldDoesNotExist:
            # For non-field list_display values, the value is a method
            # name. Execute the method.
            func = getattr(result, field_name)
            try:
                result_repr = str(func())
            except ObjectDoesNotExist:
                result_repr = EMPTY_CHANGELIST_VALUE
            else:
                # Strip HTML tags in the resulting text, except if the 
                # function has an "allow_tags" attribute set to True. 
                if not getattr(func, 'allow_tags', False): 
                    result_repr = strip_tags(result_repr)
        else:
            field_val = getattr(result, f.attname)
        
            if isinstance(f.rel, meta.ManyToOne):
                if field_val is not None:
                    result_repr = getattr(result, 'get_%s' % f.name)()
                else:
                    result_repr = EMPTY_CHANGELIST_VALUE
            # Dates and times are special: They're formatted in a certain way.
            elif isinstance(f, meta.DateField) or isinstance(f, meta.TimeField):
                if field_val:
                    if isinstance(f, meta.DateTimeField):
                        result_repr = capfirst(dateformat.format(field_val, DATETIME_FORMAT))
                    elif isinstance(f, meta.TimeField):
                        result_repr = capfirst(dateformat.time_format(field_val, TIME_FORMAT))
                    else:
                        result_repr = capfirst(dateformat.format(field_val, DATE_FORMAT))
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
        if result_repr == '':
                result_repr = '&nbsp;'
        if first: # First column is a special case
            first = False
            result_id = getattr(result, pk)
            yield ('<th%s><a href="%s/"%s>%s</a></th>' % \
                (row_class, result_id, (cl.is_popup and ' onclick="opener.dismissRelatedLookupPopup(window, %r); return false;"' % result_id or ''), result_repr))
        else:
            yield ('<td%s>%s</td>' % (row_class, result_repr))
        
def results(cl):
    for res in cl.result_list:
        yield list(items_for_result(cl,res))

#@inclusion_tag("admin/change_list_results")
def result_list(cl):
    res = list(results(cl))
    return {'cl': cl, 
             'result_headers': list(result_headers(cl)), 
             'results': list(results(cl)), }
result_list = inclusion_tag("admin/change_list_results")(result_list)


#@inclusion_tag("admin/date_hierarchy")
def date_hierarchy(cl):
    lookup_opts, params, lookup_params, lookup_mod = \
      cl.lookup_opts, cl.params, cl.lookup_params, cl.lookup_mod
    
    if lookup_opts.admin.date_hierarchy:
        field_name = lookup_opts.admin.date_hierarchy
    
        year_field = '%s__year' % field_name
        month_field = '%s__month' % field_name
        day_field = '%s__day' % field_name
        field_generic = '%s__' % field_name
        year_lookup = params.get(year_field)
        month_lookup = params.get(month_field)
        day_lookup = params.get(day_field)
     
        def link(d): 
            return cl.get_query_string(d, [field_generic])
     
        def get_dates(unit, params):
            return getattr(lookup_mod, 'get_%s_list' % field_name)(unit, **params)
     
        if year_lookup and month_lookup and day_lookup:
            month_name = MONTHS[int(month_lookup)]
            return {  'show': True,
                      'back': 
                        { 'link' : link({year_field: year_lookup, month_field: month_lookup}), 
                          'title': "%s %s" % ( month_name, year_lookup),
                        },
                      'choices': [ {'title': "%s %s" % ( month_name, day_lookup)} ]
                  }
        elif year_lookup and month_lookup:
            date_lookup_params = lookup_params.copy()
            date_lookup_params.update({year_field: year_lookup, month_field: month_lookup})
            days = get_dates('day', date_lookup_params)
            return { 'show': True,
                     'back': 
                        { 'link' : link({year_field: year_lookup}), 
                          'title' : year_lookup 
                        },
                    'choices': 
                        [ { 'link' : link({year_field: year_lookup, month_field: month_lookup, day_field: day.day}), 
                            'title': day.strftime('%B %d') } for day in days ]
                    }
        elif year_lookup:
            date_lookup_params = lookup_params.copy()
            date_lookup_params.update({year_field: year_lookup})
            months = get_dates('month', date_lookup_params)
            return {  'show' : True,
                      'back':
                       { 'link' : link({}),
                         'title': _('All dates')
                       },
                      'choices':
                      [ { 'link': link( {year_field: year_lookup, month_field: month.month}), 
                          'title': "%s %s" % (month.strftime('%B') ,  month.year) } for month in months ]
                  }
        else:
            years = get_dates('year', lookup_params)
            return { 'show': True,
                     'choices':
                        [ { 'link': link( {year_field: year.year}),
                            'title': year.year  } for year in years ]
                   }
date_hierarchy = inclusion_tag('admin/date_hierarchy')(date_hierarchy)

#@inclusion_tag('admin/search_form')
def search_form(cl):
    return { 'cl': cl,
             'show_result_count': cl.result_count != cl.full_result_count and not cl.opts.one_to_one_field, 
             'search_var': SEARCH_VAR }
search_form = inclusion_tag('admin/search_form')(search_form)

#@inclusion_tag('admin/filter')
def filter(cl, spec):
    return {'title': spec.title(), 
             'choices' : list(spec.choices(cl))}
filter = inclusion_tag('admin/filter')(filter)

#@inclusion_tag('admin/filters')
def filters(cl):
    return {'cl': cl}
filters = inclusion_tag('admin/filters')(filters)
