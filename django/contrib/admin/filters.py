"""
This encapsulates the logic for displaying filters in the Django admin.
Filters are specified in models with the "list_filter" option.

Each filter subclass knows how to display a filter for a field that passes a
certain test -- e.g. being a DateField or ForeignKey.
"""
import datetime

from django import forms
from django.contrib.admin.options import IncorrectLookupParameters
from django.contrib.admin.utils import (
    build_q_object_from_lookup_parameters,
    get_last_value_from_parameters,
    get_model_from_relation,
    prepare_lookup_value,
    reverse_field_path,
)
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class ListFilter:
    title = None  # Human-readable title to appear in the right sidebar.
    template = "admin/filter.html"

    def __init__(self, request, params, model, model_admin):
        self.request = request
        # This dictionary will eventually contain the request's query string
        # parameters actually used by this filter.
        self.used_parameters = {}
        if self.title is None:
            raise ImproperlyConfigured(
                "The list filter '%s' does not specify a 'title'."
                % self.__class__.__name__
            )

    def has_output(self):
        """
        Return True if some choices would be output for this filter.
        """
        raise NotImplementedError(
            "subclasses of ListFilter must provide a has_output() method"
        )

    def choices(self, changelist):
        """
        Return choices ready to be output in the template.

        `changelist` is the ChangeList to be displayed.
        """
        raise NotImplementedError(
            "subclasses of ListFilter must provide a choices() method"
        )

    def queryset(self, request, queryset):
        """
        Return the filtered queryset.
        """
        raise NotImplementedError(
            "subclasses of ListFilter must provide a queryset() method"
        )

    def expected_parameters(self):
        """
        Return the list of parameter names that are expected from the
        request's query string and that will be used by this filter.
        """
        raise NotImplementedError(
            "subclasses of ListFilter must provide an expected_parameters() method"
        )

    def clean_params(self, params):
        """
        Return True if some choices would be output for this filter.
        """
        return params


class FacetsMixin:
    def get_facet_counts(self, pk_attname, filtered_qs):
        raise NotImplementedError(
            "subclasses of FacetsMixin must provide a get_facet_counts() method."
        )

    def get_facet_queryset(self, changelist):
        filtered_qs = changelist.get_queryset(
            self.request, exclude_parameters=self.expected_parameters()
        )
        return filtered_qs.aggregate(
            **self.get_facet_counts(changelist.pk_attname, filtered_qs)
        )


class SimpleListFilter(FacetsMixin, ListFilter):
    # The parameter that should be used in the query string for that filter.
    parameter_name = None

    def __init__(self, request, params, model, model_admin):
        super().__init__(request, params, model, model_admin)
        if self.parameter_name is None:
            raise ImproperlyConfigured(
                "The list filter '%s' does not specify a 'parameter_name'."
                % self.__class__.__name__
            )
        if self.parameter_name in params:
            value = params.pop(self.parameter_name)
            self.used_parameters[self.parameter_name] = value[-1]
        lookup_choices = self.lookups(request, model_admin)
        if lookup_choices is None:
            lookup_choices = ()
        self.lookup_choices = list(lookup_choices)

    def has_output(self):
        return len(self.lookup_choices) > 0

    def value(self):
        """
        Return the value (in string format) provided in the request's
        query string for this filter, if any, or None if the value wasn't
        provided.
        """
        return self.used_parameters.get(self.parameter_name)

    def lookups(self, request, model_admin):
        """
        Must be overridden to return a list of tuples (value, verbose value)
        """
        raise NotImplementedError(
            "The SimpleListFilter.lookups() method must be overridden to "
            "return a list of tuples (value, verbose value)."
        )

    def expected_parameters(self):
        return [self.parameter_name]

    def get_facet_counts(self, pk_attname, filtered_qs):
        original_value = self.used_parameters.get(self.parameter_name)
        counts = {}
        for i, choice in enumerate(self.lookup_choices):
            self.used_parameters[self.parameter_name] = choice[0]
            lookup_qs = self.queryset(self.request, filtered_qs)
            if lookup_qs is not None:
                counts[f"{i}__c"] = models.Count(
                    pk_attname,
                    filter=lookup_qs.query.where,
                )
        self.used_parameters[self.parameter_name] = original_value
        return counts

    def choices(self, changelist):
        add_facets = changelist.add_facets
        facet_counts = self.get_facet_queryset(changelist) if add_facets else None
        yield {
            "selected": self.value() is None,
            "query_string": changelist.get_query_string(remove=[self.parameter_name]),
            "display": _("All"),
        }
        for i, (lookup, title) in enumerate(self.lookup_choices):
            if add_facets:
                if (count := facet_counts.get(f"{i}__c", -1)) != -1:
                    title = f"{title} ({count})"
                else:
                    title = f"{title} (-)"
            yield {
                "selected": self.value() == str(lookup),
                "query_string": changelist.get_query_string(
                    {self.parameter_name: lookup}
                ),
                "display": title,
            }


class FieldListFilter(FacetsMixin, ListFilter):
    _field_list_filters = []
    _take_priority_index = 0
    list_separator = ","

    def __init__(self, field, request, params, model, model_admin, field_path):
        self.field = field
        self.field_path = field_path
        self.title = getattr(field, "verbose_name", field_path)
        super().__init__(request, params, model, model_admin)
        for p in self.expected_parameters():
            if p in params:
                value = params.pop(p)
                self.used_parameters[p] = prepare_lookup_value(
                    p, value, self.list_separator
                )

    def has_output(self):
        return True

    def queryset(self, request, queryset):
        try:
            q_object = build_q_object_from_lookup_parameters(self.used_parameters)
            return queryset.filter(q_object)
        except (ValueError, ValidationError) as e:
            # Fields may raise a ValueError or ValidationError when converting
            # the parameters to the correct type.
            raise IncorrectLookupParameters(e)

    @classmethod
    def register(cls, test, list_filter_class, take_priority=False):
        if take_priority:
            # This is to allow overriding the default filters for certain types
            # of fields with some custom filters. The first found in the list
            # is used in priority.
            cls._field_list_filters.insert(
                cls._take_priority_index, (test, list_filter_class)
            )
            cls._take_priority_index += 1
        else:
            cls._field_list_filters.append((test, list_filter_class))

    @classmethod
    def create(cls, field, request, params, model, model_admin, field_path):
        for test, list_filter_class in cls._field_list_filters:
            if test(field):
                return list_filter_class(
                    field, request, params, model, model_admin, field_path=field_path
                )


class CleanParamsWithFormListFilterMixin:
    def clean_params(self, params):
        class _Form(forms.Form):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                for field in params:
                    if '__isnull' in field:
                        self.fields[field] = forms.NullBooleanField(required=False)
                    else:
                        self.fields[field] = forms.CharField(required=False, empty_value=None)

        form = _Form(params)
        form.is_valid()

        return form.cleaned_data


class RelatedFieldListFilter(CleanParamsWithFormListFilterMixin, FieldListFilter):
    def __init__(self, field, request, params, model, model_admin, field_path):
        other_model = get_model_from_relation(field)
        self.lookup_kwarg = "%s__%s__exact" % (field_path, field.target_field.name)
        self.lookup_kwarg_isnull = "%s__isnull" % field_path
        cleaned_params = self.clean_params(params)
        self.lookup_val = cleaned_params.get(self.lookup_kwarg)
        self.lookup_val_isnull = get_last_value_from_parameters(
            cleaned_params, self.lookup_kwarg_isnull
        )
        super().__init__(field, request, params, model, model_admin, field_path)
        self.lookup_choices = self.field_choices(field, request, model_admin)
        if hasattr(field, "verbose_name"):
            self.lookup_title = field.verbose_name
        else:
            self.lookup_title = other_model._meta.verbose_name
        self.title = self.lookup_title
        self.empty_value_display = model_admin.get_empty_value_display()

    @property
    def include_empty_choice(self):
        """
        Return True if a "(None)" choice should be included, which filters
        out everything except empty relationships.
        """
        return self.field.null or (self.field.is_relation and self.field.many_to_many)

    def has_output(self):
        if self.include_empty_choice:
            extra = 1
        else:
            extra = 0
        return len(self.lookup_choices) + extra > 1

    def expected_parameters(self):
        return [self.lookup_kwarg, self.lookup_kwarg_isnull]

    def field_admin_ordering(self, field, request, model_admin):
        """
        Return the model admin's ordering for related field, if provided.
        """
        related_admin = model_admin.admin_site._registry.get(field.remote_field.model)
        if related_admin is not None:
            return related_admin.get_ordering(request)
        return ()

    def field_choices(self, field, request, model_admin):
        ordering = self.field_admin_ordering(field, request, model_admin)
        return field.get_choices(include_blank=False, ordering=ordering)

    def get_facet_counts(self, pk_attname, filtered_qs):
        counts = {
            f"{pk_val}__c": models.Count(
                pk_attname, filter=models.Q(**{self.lookup_kwarg: pk_val})
            )
            for pk_val, _ in self.lookup_choices
        }
        if self.include_empty_choice:
            counts["__c"] = models.Count(
                pk_attname, filter=models.Q(**{self.lookup_kwarg_isnull: True})
            )
        return counts

    def choices(self, changelist):
        add_facets = changelist.add_facets
        facet_counts = self.get_facet_queryset(changelist) if add_facets else None
        yield {
            "selected": self.lookup_val is None and not self.lookup_val_isnull,
            "query_string": changelist.get_query_string(
                remove=[self.lookup_kwarg, self.lookup_kwarg_isnull]
            ),
            "display": _("All"),
        }
        count = None
        for pk_val, val in self.lookup_choices:
            if add_facets:
                count = facet_counts[f"{pk_val}__c"]
                val = f"{val} ({count})"
            yield {
                "selected": self.lookup_val is not None
                and str(pk_val) in self.lookup_val,
                "query_string": changelist.get_query_string(
                    {self.lookup_kwarg: pk_val}, [self.lookup_kwarg_isnull]
                ),
                "display": val,
            }
        empty_title = self.empty_value_display
        if self.include_empty_choice:
            if add_facets:
                count = facet_counts["__c"]
                empty_title = f"{empty_title} ({count})"
            yield {
                "selected": bool(self.lookup_val_isnull),
                "query_string": changelist.get_query_string(
                    {self.lookup_kwarg_isnull: "True"}, [self.lookup_kwarg]
                ),
                "display": empty_title,
            }


FieldListFilter.register(lambda f: f.remote_field, RelatedFieldListFilter)


class BooleanFieldListFilter(FieldListFilter):
    def __init__(self, field, request, params, model, model_admin, field_path):
        self.lookup_kwarg = "%s__exact" % field_path
        self.lookup_kwarg2 = "%s__isnull" % field_path
        self.lookup_val = get_last_value_from_parameters(params, self.lookup_kwarg)
        self.lookup_val2 = get_last_value_from_parameters(params, self.lookup_kwarg2)
        super().__init__(field, request, params, model, model_admin, field_path)
        if (
            self.used_parameters
            and self.lookup_kwarg in self.used_parameters
            and self.used_parameters[self.lookup_kwarg] in ("1", "0")
        ):
            self.used_parameters[self.lookup_kwarg] = bool(
                int(self.used_parameters[self.lookup_kwarg])
            )

    def expected_parameters(self):
        return [self.lookup_kwarg, self.lookup_kwarg2]

    def get_facet_counts(self, pk_attname, filtered_qs):
        return {
            "true__c": models.Count(
                pk_attname, filter=models.Q(**{self.field_path: True})
            ),
            "false__c": models.Count(
                pk_attname, filter=models.Q(**{self.field_path: False})
            ),
            "null__c": models.Count(
                pk_attname, filter=models.Q(**{self.lookup_kwarg2: True})
            ),
        }

    def choices(self, changelist):
        field_choices = dict(self.field.flatchoices)
        add_facets = changelist.add_facets
        facet_counts = self.get_facet_queryset(changelist) if add_facets else None
        for lookup, title, count_field in (
            (None, _("All"), None),
            ("1", field_choices.get(True, _("Yes")), "true__c"),
            ("0", field_choices.get(False, _("No")), "false__c"),
        ):
            if add_facets:
                if count_field is not None:
                    count = facet_counts[count_field]
                    title = f"{title} ({count})"
            yield {
                "selected": self.lookup_val == lookup and not self.lookup_val2,
                "query_string": changelist.get_query_string(
                    {self.lookup_kwarg: lookup}, [self.lookup_kwarg2]
                ),
                "display": title,
            }
        if self.field.null:
            display = field_choices.get(None, _("Unknown"))
            if add_facets:
                count = facet_counts["null__c"]
                display = f"{display} ({count})"
            yield {
                "selected": self.lookup_val2 == "True",
                "query_string": changelist.get_query_string(
                    {self.lookup_kwarg2: "True"}, [self.lookup_kwarg]
                ),
                "display": display,
            }


FieldListFilter.register(
    lambda f: isinstance(f, models.BooleanField), BooleanFieldListFilter
)


class ChoicesFieldListFilter(FieldListFilter):
    def __init__(self, field, request, params, model, model_admin, field_path):
        self.lookup_kwarg = "%s__exact" % field_path
        self.lookup_kwarg_isnull = "%s__isnull" % field_path
        self.lookup_val = params.get(self.lookup_kwarg)
        self.lookup_val_isnull = get_last_value_from_parameters(
            params, self.lookup_kwarg_isnull
        )
        super().__init__(field, request, params, model, model_admin, field_path)

    def expected_parameters(self):
        return [self.lookup_kwarg, self.lookup_kwarg_isnull]

    def get_facet_counts(self, pk_attname, filtered_qs):
        return {
            f"{i}__c": models.Count(
                pk_attname,
                filter=models.Q(
                    (self.lookup_kwarg, value)
                    if value is not None
                    else (self.lookup_kwarg_isnull, True)
                ),
            )
            for i, (value, _) in enumerate(self.field.flatchoices)
        }

    def choices(self, changelist):
        add_facets = changelist.add_facets
        facet_counts = self.get_facet_queryset(changelist) if add_facets else None
        yield {
            "selected": self.lookup_val is None,
            "query_string": changelist.get_query_string(
                remove=[self.lookup_kwarg, self.lookup_kwarg_isnull]
            ),
            "display": _("All"),
        }
        none_title = ""
        for i, (lookup, title) in enumerate(self.field.flatchoices):
            if add_facets:
                count = facet_counts[f"{i}__c"]
                title = f"{title} ({count})"
            if lookup is None:
                none_title = title
                continue
            yield {
                "selected": self.lookup_val is not None
                and str(lookup) in self.lookup_val,
                "query_string": changelist.get_query_string(
                    {self.lookup_kwarg: lookup}, [self.lookup_kwarg_isnull]
                ),
                "display": title,
            }
        if none_title:
            yield {
                "selected": bool(self.lookup_val_isnull),
                "query_string": changelist.get_query_string(
                    {self.lookup_kwarg_isnull: "True"}, [self.lookup_kwarg]
                ),
                "display": none_title,
            }


FieldListFilter.register(lambda f: bool(f.choices), ChoicesFieldListFilter)


class DateFieldListFilter(FieldListFilter):
    def __init__(self, field, request, params, model, model_admin, field_path):
        self.field_generic = "%s__" % field_path
        self.date_params = {
            k: v[-1] for k, v in params.items() if k.startswith(self.field_generic)
        }

        now = timezone.now()
        # When time zone support is enabled, convert "now" to the user's time
        # zone so Django's definition of "Today" matches what the user expects.
        if timezone.is_aware(now):
            now = timezone.localtime(now)

        if isinstance(field, models.DateTimeField):
            today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        else:  # field is a models.DateField
            today = now.date()
        tomorrow = today + datetime.timedelta(days=1)
        if today.month == 12:
            next_month = today.replace(year=today.year + 1, month=1, day=1)
        else:
            next_month = today.replace(month=today.month + 1, day=1)
        next_year = today.replace(year=today.year + 1, month=1, day=1)

        self.lookup_kwarg_since = "%s__gte" % field_path
        self.lookup_kwarg_until = "%s__lt" % field_path
        self.links = (
            (_("Any date"), {}),
            (
                _("Today"),
                {
                    self.lookup_kwarg_since: today,
                    self.lookup_kwarg_until: tomorrow,
                },
            ),
            (
                _("Past 7 days"),
                {
                    self.lookup_kwarg_since: today - datetime.timedelta(days=7),
                    self.lookup_kwarg_until: tomorrow,
                },
            ),
            (
                _("This month"),
                {
                    self.lookup_kwarg_since: today.replace(day=1),
                    self.lookup_kwarg_until: next_month,
                },
            ),
            (
                _("This year"),
                {
                    self.lookup_kwarg_since: today.replace(month=1, day=1),
                    self.lookup_kwarg_until: next_year,
                },
            ),
        )
        if field.null:
            self.lookup_kwarg_isnull = "%s__isnull" % field_path
            self.links += (
                (_("No date"), {self.field_generic + "isnull": True}),
                (_("Has date"), {self.field_generic + "isnull": False}),
            )
        super().__init__(field, request, params, model, model_admin, field_path)

    def expected_parameters(self):
        params = [self.lookup_kwarg_since, self.lookup_kwarg_until]
        if self.field.null:
            params.append(self.lookup_kwarg_isnull)
        return params

    def get_facet_counts(self, pk_attname, filtered_qs):
        return {
            f"{i}__c": models.Count(pk_attname, filter=models.Q(**param_dict))
            for i, (_, param_dict) in enumerate(self.links)
        }

    def choices(self, changelist):
        add_facets = changelist.add_facets
        facet_counts = self.get_facet_queryset(changelist) if add_facets else None
        for i, (title, param_dict) in enumerate(self.links):
            param_dict_str = {key: str(value) for key, value in param_dict.items()}
            if add_facets:
                count = facet_counts[f"{i}__c"]
                title = f"{title} ({count})"
            yield {
                "selected": self.date_params == param_dict_str,
                "query_string": changelist.get_query_string(
                    param_dict_str, [self.field_generic]
                ),
                "display": title,
            }


FieldListFilter.register(lambda f: isinstance(f, models.DateField), DateFieldListFilter)


# This should be registered last, because it's a last resort. For example,
# if a field is eligible to use the BooleanFieldListFilter, that'd be much
# more appropriate, and the AllValuesFieldListFilter won't get used for it.
class AllValuesFieldListFilter(FieldListFilter):
    def __init__(self, field, request, params, model, model_admin, field_path):
        self.lookup_kwarg = field_path
        self.lookup_kwarg_isnull = "%s__isnull" % field_path
        self.lookup_val = params.get(self.lookup_kwarg)
        self.lookup_val_isnull = get_last_value_from_parameters(
            params, self.lookup_kwarg_isnull
        )
        self.empty_value_display = model_admin.get_empty_value_display()
        parent_model, reverse_path = reverse_field_path(model, field_path)
        # Obey parent ModelAdmin queryset when deciding which options to show
        if model == parent_model:
            queryset = model_admin.get_queryset(request)
        else:
            queryset = parent_model._default_manager.all()
        self.lookup_choices = (
            queryset.distinct().order_by(field.name).values_list(field.name, flat=True)
        )
        super().__init__(field, request, params, model, model_admin, field_path)

    def expected_parameters(self):
        return [self.lookup_kwarg, self.lookup_kwarg_isnull]

    def get_facet_counts(self, pk_attname, filtered_qs):
        return {
            f"{i}__c": models.Count(
                pk_attname,
                filter=models.Q(
                    (self.lookup_kwarg, value)
                    if value is not None
                    else (self.lookup_kwarg_isnull, True)
                ),
            )
            for i, value in enumerate(self.lookup_choices)
        }

    def choices(self, changelist):
        add_facets = changelist.add_facets
        facet_counts = self.get_facet_queryset(changelist) if add_facets else None
        yield {
            "selected": self.lookup_val is None and self.lookup_val_isnull is None,
            "query_string": changelist.get_query_string(
                remove=[self.lookup_kwarg, self.lookup_kwarg_isnull]
            ),
            "display": _("All"),
        }
        include_none = False
        count = None
        empty_title = self.empty_value_display
        for i, val in enumerate(self.lookup_choices):
            if add_facets:
                count = facet_counts[f"{i}__c"]
            if val is None:
                include_none = True
                empty_title = f"{empty_title} ({count})" if add_facets else empty_title
                continue
            val = str(val)
            yield {
                "selected": self.lookup_val is not None and val in self.lookup_val,
                "query_string": changelist.get_query_string(
                    {self.lookup_kwarg: val}, [self.lookup_kwarg_isnull]
                ),
                "display": f"{val} ({count})" if add_facets else val,
            }
        if include_none:
            yield {
                "selected": bool(self.lookup_val_isnull),
                "query_string": changelist.get_query_string(
                    {self.lookup_kwarg_isnull: "True"}, [self.lookup_kwarg]
                ),
                "display": empty_title,
            }


FieldListFilter.register(lambda f: True, AllValuesFieldListFilter)


class RelatedOnlyFieldListFilter(RelatedFieldListFilter):
    def field_choices(self, field, request, model_admin):
        pk_qs = (
            model_admin.get_queryset(request)
            .distinct()
            .values_list("%s__pk" % self.field_path, flat=True)
        )
        ordering = self.field_admin_ordering(field, request, model_admin)
        return field.get_choices(
            include_blank=False, limit_choices_to={"pk__in": pk_qs}, ordering=ordering
        )


class EmptyFieldListFilter(FieldListFilter):
    def __init__(self, field, request, params, model, model_admin, field_path):
        if not field.empty_strings_allowed and not field.null:
            raise ImproperlyConfigured(
                "The list filter '%s' cannot be used with field '%s' which "
                "doesn't allow empty strings and nulls."
                % (
                    self.__class__.__name__,
                    field.name,
                )
            )
        self.lookup_kwarg = "%s__isempty" % field_path
        self.lookup_val = get_last_value_from_parameters(params, self.lookup_kwarg)
        super().__init__(field, request, params, model, model_admin, field_path)

    def get_lookup_condition(self):
        lookup_conditions = []
        if self.field.empty_strings_allowed:
            lookup_conditions.append((self.field_path, ""))
        if self.field.null:
            lookup_conditions.append((f"{self.field_path}__isnull", True))
        return models.Q.create(lookup_conditions, connector=models.Q.OR)

    def queryset(self, request, queryset):
        if self.lookup_kwarg not in self.used_parameters:
            return queryset
        if self.lookup_val not in ("0", "1"):
            raise IncorrectLookupParameters

        lookup_condition = self.get_lookup_condition()
        if self.lookup_val == "1":
            return queryset.filter(lookup_condition)
        return queryset.exclude(lookup_condition)

    def expected_parameters(self):
        return [self.lookup_kwarg]

    def get_facet_counts(self, pk_attname, filtered_qs):
        lookup_condition = self.get_lookup_condition()
        return {
            "empty__c": models.Count(pk_attname, filter=lookup_condition),
            "not_empty__c": models.Count(pk_attname, filter=~lookup_condition),
        }

    def choices(self, changelist):
        add_facets = changelist.add_facets
        facet_counts = self.get_facet_queryset(changelist) if add_facets else None
        for lookup, title, count_field in (
            (None, _("All"), None),
            ("1", _("Empty"), "empty__c"),
            ("0", _("Not empty"), "not_empty__c"),
        ):
            if add_facets:
                if count_field is not None:
                    count = facet_counts[count_field]
                    title = f"{title} ({count})"
            yield {
                "selected": self.lookup_val == lookup,
                "query_string": changelist.get_query_string(
                    {self.lookup_kwarg: lookup}
                ),
                "display": title,
            }
