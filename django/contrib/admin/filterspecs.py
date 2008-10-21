"""
FilterSpec encapsulates the logic for displaying filters in the Django admin.
Filters are specified in models with the "list_filter" option.

Each filter subclass knows how to display a filter for a field that passes a
certain test -- e.g. being a DateField or ForeignKey.
"""

from django.db import models
from django.utils.encoding import smart_unicode, iri_to_uri
from django.utils.translation import ugettext as _
from django.utils.html import escape
from django.utils.safestring import mark_safe
import datetime

class FilterSpec(object):
    filter_specs = []
    def __init__(self, f, request, params, model, model_admin):
        self.field = f
        self.params = params

    def register(cls, test, factory):
        cls.filter_specs.append((test, factory))
    register = classmethod(register)

    def create(cls, f, request, params, model, model_admin):
        for test, factory in cls.filter_specs:
            if test(f):
                return factory(f, request, params, model, model_admin)
    create = classmethod(create)

    def has_output(self):
        return True

    def choices(self, cl):
        raise NotImplementedError()

    def title(self):
        return self.field.verbose_name

    def output(self, cl):
        t = []
        if self.has_output():
            t.append(_(u'<h3>By %s:</h3>\n<ul>\n') % escape(self.title()))

            for choice in self.choices(cl):
                t.append(u'<li%s><a href="%s">%s</a></li>\n' % \
                    ((choice['selected'] and ' class="selected"' or ''),
                     iri_to_uri(choice['query_string']),
                     choice['display']))
            t.append('</ul>\n\n')
        return mark_safe("".join(t))

class RelatedFilterSpec(FilterSpec):
    def __init__(self, f, request, params, model, model_admin):
        super(RelatedFilterSpec, self).__init__(f, request, params, model, model_admin)
        if isinstance(f, models.ManyToManyField):
            self.lookup_title = f.rel.to._meta.verbose_name
        else:
            self.lookup_title = f.verbose_name
        self.lookup_kwarg = '%s__%s__exact' % (f.name, f.rel.to._meta.pk.name)
        self.lookup_val = request.GET.get(self.lookup_kwarg, None)
        self.lookup_choices = f.get_choices(include_blank=False)

    def has_output(self):
        return len(self.lookup_choices) > 1

    def title(self):
        return self.lookup_title

    def choices(self, cl):
        yield {'selected': self.lookup_val is None,
               'query_string': cl.get_query_string({}, [self.lookup_kwarg]),
               'display': _('All')}
        for pk_val, val in self.lookup_choices:
            yield {'selected': self.lookup_val == smart_unicode(pk_val),
                   'query_string': cl.get_query_string({self.lookup_kwarg: pk_val}),
                   'display': val}

FilterSpec.register(lambda f: bool(f.rel), RelatedFilterSpec)

class ChoicesFilterSpec(FilterSpec):
    def __init__(self, f, request, params, model, model_admin):
        super(ChoicesFilterSpec, self).__init__(f, request, params, model, model_admin)
        self.lookup_kwarg = '%s__exact' % f.name
        self.lookup_val = request.GET.get(self.lookup_kwarg, None)

    def choices(self, cl):
        yield {'selected': self.lookup_val is None,
               'query_string': cl.get_query_string({}, [self.lookup_kwarg]),
               'display': _('All')}
        for k, v in self.field.choices:
            yield {'selected': smart_unicode(k) == self.lookup_val,
                    'query_string': cl.get_query_string({self.lookup_kwarg: k}),
                    'display': v}

FilterSpec.register(lambda f: bool(f.choices), ChoicesFilterSpec)

class DateFieldFilterSpec(FilterSpec):
    def __init__(self, f, request, params, model, model_admin):
        super(DateFieldFilterSpec, self).__init__(f, request, params, model, model_admin)

        self.field_generic = '%s__' % self.field.name

        self.date_params = dict([(k, v) for k, v in params.items() if k.startswith(self.field_generic)])

        today = datetime.date.today()
        one_week_ago = today - datetime.timedelta(days=7)
        today_str = isinstance(self.field, models.DateTimeField) and today.strftime('%Y-%m-%d 23:59:59') or today.strftime('%Y-%m-%d')

        self.links = (
            (_('Any date'), {}),
            (_('Today'), {'%s__year' % self.field.name: str(today.year),
                       '%s__month' % self.field.name: str(today.month),
                       '%s__day' % self.field.name: str(today.day)}),
            (_('Past 7 days'), {'%s__gte' % self.field.name: one_week_ago.strftime('%Y-%m-%d'),
                             '%s__lte' % f.name: today_str}),
            (_('This month'), {'%s__year' % self.field.name: str(today.year),
                             '%s__month' % f.name: str(today.month)}),
            (_('This year'), {'%s__year' % self.field.name: str(today.year)})
        )

    def title(self):
        return self.field.verbose_name

    def choices(self, cl):
        for title, param_dict in self.links:
            yield {'selected': self.date_params == param_dict,
                   'query_string': cl.get_query_string(param_dict, [self.field_generic]),
                   'display': title}

FilterSpec.register(lambda f: isinstance(f, models.DateField), DateFieldFilterSpec)

class BooleanFieldFilterSpec(FilterSpec):
    def __init__(self, f, request, params, model, model_admin):
        super(BooleanFieldFilterSpec, self).__init__(f, request, params, model, model_admin)
        self.lookup_kwarg = '%s__exact' % f.name
        self.lookup_kwarg2 = '%s__isnull' % f.name
        self.lookup_val = request.GET.get(self.lookup_kwarg, None)
        self.lookup_val2 = request.GET.get(self.lookup_kwarg2, None)

    def title(self):
        return self.field.verbose_name

    def choices(self, cl):
        for k, v in ((_('All'), None), (_('Yes'), '1'), (_('No'), '0')):
            yield {'selected': self.lookup_val == v and not self.lookup_val2,
                   'query_string': cl.get_query_string({self.lookup_kwarg: v}, [self.lookup_kwarg2]),
                   'display': k}
        if isinstance(self.field, models.NullBooleanField):
            yield {'selected': self.lookup_val2 == 'True',
                   'query_string': cl.get_query_string({self.lookup_kwarg2: 'True'}, [self.lookup_kwarg]),
                   'display': _('Unknown')}

FilterSpec.register(lambda f: isinstance(f, models.BooleanField) or isinstance(f, models.NullBooleanField), BooleanFieldFilterSpec)

# This should be registered last, because it's a last resort. For example,
# if a field is eligible to use the BooleanFieldFilterSpec, that'd be much
# more appropriate, and the AllValuesFilterSpec won't get used for it.
class AllValuesFilterSpec(FilterSpec):
    def __init__(self, f, request, params, model, model_admin):
        super(AllValuesFilterSpec, self).__init__(f, request, params, model, model_admin)
        self.lookup_val = request.GET.get(f.name, None)
        self.lookup_choices = model_admin.queryset(request).distinct().order_by(f.name).values(f.name)

    def title(self):
        return self.field.verbose_name

    def choices(self, cl):
        yield {'selected': self.lookup_val is None,
               'query_string': cl.get_query_string({}, [self.field.name]),
               'display': _('All')}
        for val in self.lookup_choices:
            val = smart_unicode(val[self.field.name])
            yield {'selected': self.lookup_val == val,
                   'query_string': cl.get_query_string({self.field.name: val}),
                   'display': val}
FilterSpec.register(lambda f: True, AllValuesFilterSpec)
