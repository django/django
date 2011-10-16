"""
This encapsulates the logic for displaying filters in the Django admin.
Filters are specified in models with the "list_filter" option.

Each filter subclass knows how to display a filter for a field that passes a
certain test -- e.g. being a DateField or ForeignKey.
"""
import datetime

from django.db import models
from django.core.exceptions import ImproperlyConfigured
from django.utils.encoding import smart_unicode
from django.utils.translation import ugettext_lazy as _

from django.contrib.admin.util import (get_model_from_relation,
    reverse_field_path, get_limit_choices_to_from_path)

class ListFilter(object):
    title = None  # Human-readable title to appear in the right sidebar.

    def __init__(self, request, params, model, model_admin):
        self.params = params
        if self.title is None:
            raise ImproperlyConfigured(
                "The list filter '%s' does not specify "
                "a 'title'." % self.__class__.__name__)

    def has_output(self):
        """
        Returns True if some choices would be output for the filter.
        """
        raise NotImplementedError

    def choices(self, cl):
        """
        Returns choices ready to be output in the template.
        """
        raise NotImplementedError

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset.
        """
        raise NotImplementedError

    def used_params(self):
        """
        Return a list of parameters to consume from the change list
        querystring.
        """
        raise NotImplementedError



class SimpleListFilter(ListFilter):
    # The parameter that should be used in the query string for that filter.
    parameter_name = None

    def __init__(self, request, params, model, model_admin):
        super(SimpleListFilter, self).__init__(
            request, params, model, model_admin)
        if self.parameter_name is None:
            raise ImproperlyConfigured(
                "The list filter '%s' does not specify "
                "a 'parameter_name'." % self.__class__.__name__)
        lookup_choices = self.lookups(request, model_admin)
        if lookup_choices is None:
            lookup_choices = ()
        self.lookup_choices = list(lookup_choices)

    def has_output(self):
        return len(self.lookup_choices) > 0

    def value(self):
        """
        Returns the value given in the query string for this filter,
        if any. Returns None otherwise.
        """
        return self.params.get(self.parameter_name, None)

    def lookups(self, request, model_admin):
        """
        Must be overriden to return a list of tuples (value, verbose value)
        """
        raise NotImplementedError

    def used_params(self):
        return [self.parameter_name]

    def choices(self, cl):
        yield {
            'selected': self.value() is None,
            'query_string': cl.get_query_string({}, [self.parameter_name]),
            'display': _('All'),
        }
        for lookup, title in self.lookup_choices:
            yield {
                'selected': self.value() == lookup,
                'query_string': cl.get_query_string({
                    self.parameter_name: lookup,
                }, []),
                'display': title,
            }


class FieldListFilter(ListFilter):
    _field_list_filters = []
    _take_priority_index = 0

    def __init__(self, field, request, params, model, model_admin, field_path):
        self.field = field
        self.field_path = field_path
        self.title = getattr(field, 'verbose_name', field_path)
        super(FieldListFilter, self).__init__(request, params, model, model_admin)

    def has_output(self):
        return True

    def queryset(self, request, queryset):
        for p in self.used_params():
            if p in self.params:
                return queryset.filter(**{p: self.params[p]})

    @classmethod
    def register(cls, test, list_filter_class, take_priority=False):
        if take_priority:
            # This is to allow overriding the default filters for certain types
            # of fields with some custom filters. The first found in the list
            # is used in priority.
            cls._field_list_filters.insert(
                cls._take_priority_index, (test, list_filter_class))
            cls._take_priority_index += 1
        else:
            cls._field_list_filters.append((test, list_filter_class))

    @classmethod
    def create(cls, field, request, params, model, model_admin, field_path):
        for test, list_filter_class in cls._field_list_filters:
            if not test(field):
                continue
            return list_filter_class(field, request, params,
                model, model_admin, field_path=field_path)


class RelatedFieldListFilter(FieldListFilter):
    def __init__(self, field, request, params, model, model_admin, field_path):
        super(RelatedFieldListFilter, self).__init__(
            field, request, params, model, model_admin, field_path)
        other_model = get_model_from_relation(field)
        if hasattr(field, 'verbose_name'):
            self.lookup_title = field.verbose_name
        else:
            self.lookup_title = other_model._meta.verbose_name
        rel_name = other_model._meta.pk.name
        self.lookup_kwarg = '%s__%s__exact' % (self.field_path, rel_name)
        self.lookup_kwarg_isnull = '%s__isnull' % (self.field_path)
        self.lookup_val = request.GET.get(self.lookup_kwarg, None)
        self.lookup_val_isnull = request.GET.get(
                                      self.lookup_kwarg_isnull, None)
        self.lookup_choices = field.get_choices(include_blank=False)
        self.title = self.lookup_title

    def has_output(self):
        if (isinstance(self.field, models.related.RelatedObject)
                and self.field.field.null or hasattr(self.field, 'rel')
                    and self.field.null):
            extra = 1
        else:
            extra = 0
        return len(self.lookup_choices) + extra > 1

    def used_params(self):
        return [self.lookup_kwarg, self.lookup_kwarg_isnull]

    def choices(self, cl):
        from django.contrib.admin.views.main import EMPTY_CHANGELIST_VALUE
        yield {
            'selected': self.lookup_val is None and not self.lookup_val_isnull,
            'query_string': cl.get_query_string({},
                [self.lookup_kwarg, self.lookup_kwarg_isnull]),
            'display': _('All'),
        }
        for pk_val, val in self.lookup_choices:
            yield {
                'selected': self.lookup_val == smart_unicode(pk_val),
                'query_string': cl.get_query_string({
                    self.lookup_kwarg: pk_val,
                }, [self.lookup_kwarg_isnull]),
                'display': val,
            }
        if (isinstance(self.field, models.related.RelatedObject)
                and self.field.field.null or hasattr(self.field, 'rel')
                    and self.field.null):
            yield {
                'selected': bool(self.lookup_val_isnull),
                'query_string': cl.get_query_string({
                    self.lookup_kwarg_isnull: 'True',
                }, [self.lookup_kwarg]),
                'display': EMPTY_CHANGELIST_VALUE,
            }

FieldListFilter.register(lambda f: (
        hasattr(f, 'rel') and bool(f.rel) or
        isinstance(f, models.related.RelatedObject)), RelatedFieldListFilter)


class BooleanFieldListFilter(FieldListFilter):
    def __init__(self, field, request, params, model, model_admin, field_path):
        super(BooleanFieldListFilter, self).__init__(field,
            request, params, model, model_admin, field_path)
        self.lookup_kwarg = '%s__exact' % self.field_path
        self.lookup_kwarg2 = '%s__isnull' % self.field_path
        self.lookup_val = request.GET.get(self.lookup_kwarg, None)
        self.lookup_val2 = request.GET.get(self.lookup_kwarg2, None)

    def used_params(self):
        return [self.lookup_kwarg, self.lookup_kwarg2]

    def choices(self, cl):
        for lookup, title in (
                (None, _('All')),
                ('1', _('Yes')),
                ('0', _('No'))):
            yield {
                'selected': self.lookup_val == lookup and not self.lookup_val2,
                'query_string': cl.get_query_string({
                        self.lookup_kwarg: lookup,
                    }, [self.lookup_kwarg2]),
                'display': title,
            }
        if isinstance(self.field, models.NullBooleanField):
            yield {
                'selected': self.lookup_val2 == 'True',
                'query_string': cl.get_query_string({
                        self.lookup_kwarg2: 'True',
                    }, [self.lookup_kwarg]),
                'display': _('Unknown'),
            }

FieldListFilter.register(lambda f: isinstance(f,
    (models.BooleanField, models.NullBooleanField)), BooleanFieldListFilter)


class ChoicesFieldListFilter(FieldListFilter):
    def __init__(self, field, request, params, model, model_admin, field_path):
        super(ChoicesFieldListFilter, self).__init__(
            field, request, params, model, model_admin, field_path)
        self.lookup_kwarg = '%s__exact' % self.field_path
        self.lookup_val = request.GET.get(self.lookup_kwarg)

    def used_params(self):
        return [self.lookup_kwarg]

    def choices(self, cl):
        yield {
            'selected': self.lookup_val is None,
            'query_string': cl.get_query_string({}, [self.lookup_kwarg]),
            'display': _('All')
        }
        for lookup, title in self.field.flatchoices:
            yield {
                'selected': smart_unicode(lookup) == self.lookup_val,
                'query_string': cl.get_query_string({self.lookup_kwarg: lookup}),
                'display': title,
            }

FieldListFilter.register(lambda f: bool(f.choices), ChoicesFieldListFilter)


class DateFieldListFilter(FieldListFilter):
    def __init__(self, field, request, params, model, model_admin, field_path):
        super(DateFieldListFilter, self).__init__(
            field, request, params, model, model_admin, field_path)

        self.field_generic = '%s__' % self.field_path
        self.date_params = dict([(k, v) for k, v in params.items()
                                 if k.startswith(self.field_generic)])

        today = datetime.date.today()
        one_week_ago = today - datetime.timedelta(days=7)
        today_str = str(today)
        if isinstance(self.field, models.DateTimeField):
            today_str += ' 23:59:59'

        self.lookup_kwarg_year = '%s__year' % self.field_path
        self.lookup_kwarg_month = '%s__month' % self.field_path
        self.lookup_kwarg_day = '%s__day' % self.field_path
        self.lookup_kwarg_past_7_days_gte = '%s__gte' % self.field_path
        self.lookup_kwarg_past_7_days_lte = '%s__lte' % self.field_path

        self.links = (
            (_('Any date'), {}),
            (_('Today'), {
                self.lookup_kwarg_year: str(today.year),
                self.lookup_kwarg_month: str(today.month),
                self.lookup_kwarg_day: str(today.day),
            }),
            (_('Past 7 days'), {
                self.lookup_kwarg_past_7_days_gte: str(one_week_ago),
                self.lookup_kwarg_past_7_days_lte: today_str,
            }),
            (_('This month'), {
                self.lookup_kwarg_year: str(today.year),
                self.lookup_kwarg_month: str(today.month),
            }),
            (_('This year'), {
                self.lookup_kwarg_year: str(today.year),
            }),
        )

    def used_params(self):
        return [
            self.lookup_kwarg_year, self.lookup_kwarg_month, self.lookup_kwarg_day,
            self.lookup_kwarg_past_7_days_gte, self.lookup_kwarg_past_7_days_lte
        ]

    def queryset(self, request, queryset):
        """
        Override the default behaviour since there can be multiple query
        string parameters used for the same date filter (e.g. year + month).
        """
        query_dict = {}
        for p in self.used_params():
            if p in self.params:
                query_dict[p] = self.params[p]
        if len(query_dict):
            return queryset.filter(**query_dict)

    def choices(self, cl):
        for title, param_dict in self.links:
            yield {
                'selected': self.date_params == param_dict,
                'query_string': cl.get_query_string(
                    param_dict, [self.field_generic]),
                'display': title,
            }

FieldListFilter.register(
    lambda f: isinstance(f, models.DateField), DateFieldListFilter)


# This should be registered last, because it's a last resort. For example,
# if a field is eligible to use the BooleanFieldListFilter, that'd be much
# more appropriate, and the AllValuesFieldListFilter won't get used for it.
class AllValuesFieldListFilter(FieldListFilter):
    def __init__(self, field, request, params, model, model_admin, field_path):
        super(AllValuesFieldListFilter, self).__init__(
            field, request, params, model, model_admin, field_path)
        self.lookup_kwarg = self.field_path
        self.lookup_kwarg_isnull = '%s__isnull' % self.field_path
        self.lookup_val = request.GET.get(self.lookup_kwarg, None)
        self.lookup_val_isnull = request.GET.get(self.lookup_kwarg_isnull, None)
        parent_model, reverse_path = reverse_field_path(model, self.field_path)
        queryset = parent_model._default_manager.all()
        # optional feature: limit choices base on existing relationships
        # queryset = queryset.complex_filter(
        #    {'%s__isnull' % reverse_path: False})
        limit_choices_to = get_limit_choices_to_from_path(model, field_path)
        queryset = queryset.filter(limit_choices_to)

        self.lookup_choices = queryset.distinct(
            ).order_by(field.name).values_list(field.name, flat=True)

    def used_params(self):
        return [self.lookup_kwarg, self.lookup_kwarg_isnull]

    def choices(self, cl):
        from django.contrib.admin.views.main import EMPTY_CHANGELIST_VALUE
        yield {
            'selected': (self.lookup_val is None
                and self.lookup_val_isnull is None),
            'query_string': cl.get_query_string({},
                [self.lookup_kwarg, self.lookup_kwarg_isnull]),
            'display': _('All'),
        }
        include_none = False
        for val in self.lookup_choices:
            if val is None:
                include_none = True
                continue
            val = smart_unicode(val)
            yield {
                'selected': self.lookup_val == val,
                'query_string': cl.get_query_string({
                    self.lookup_kwarg: val,
                }, [self.lookup_kwarg_isnull]),
                'display': val,
            }
        if include_none:
            yield {
                'selected': bool(self.lookup_val_isnull),
                'query_string': cl.get_query_string({
                    self.lookup_kwarg_isnull: 'True',
                }, [self.lookup_kwarg]),
                'display': EMPTY_CHANGELIST_VALUE,
            }

FieldListFilter.register(lambda f: True, AllValuesFieldListFilter)
