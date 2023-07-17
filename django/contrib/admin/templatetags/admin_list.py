import datetime

from django.contrib.admin.templatetags.admin_urls import add_preserved_filters
from django.contrib.admin.utils import (
    display_for_field,
    display_for_value,
    get_fields_from_path,
    label_for_field,
    lookup_field,
)
from django.contrib.admin.views.main import (
    ALL_VAR,
    IS_FACETS_VAR,
    IS_POPUP_VAR,
    ORDER_VAR,
    PAGE_VAR,
    SEARCH_VAR,
)
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.template import Library
from django.template.loader import get_template
from django.templatetags.static import static
from django.urls import NoReverseMatch
from django.utils import formats, timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.text import capfirst
from django.utils.translation import gettext as _

from .base import InclusionAdminNode

register = Library()


@register.simple_tag
def paginator_number(cl, i):
    """
    Generate an individual page index link in a paginated list.
    """
    if i == cl.paginator.ELLIPSIS:
        return format_html("{} ", cl.paginator.ELLIPSIS)
    elif i == cl.page_num:
        return format_html('<span class="this-page">{}</span> ', i)
    else:
        return format_html(
            '<a href="{}"{}>{}</a> ',
            cl.get_query_string({PAGE_VAR: i}),
            mark_safe(' class="end"' if i == cl.paginator.num_pages else ""),
            i,
        )


def pagination(cl):
    """
    Generate the series of links to the pages in a paginated list.
    """
    pagination_required = (not cl.show_all or not cl.can_show_all) and cl.multi_page
    page_range = (
        cl.paginator.get_elided_page_range(cl.page_num) if pagination_required else []
    )
    need_show_all_link = cl.can_show_all and not cl.show_all and cl.multi_page
    return {
        "cl": cl,
        "pagination_required": pagination_required,
        "show_all_url": need_show_all_link and cl.get_query_string({ALL_VAR: ""}),
        "page_range": page_range,
        "ALL_VAR": ALL_VAR,
        "1": 1,
    }


@register.tag(name="pagination")
def pagination_tag(parser, token):
    return InclusionAdminNode(
        parser,
        token,
        func=pagination,
        template_name="pagination.html",
        takes_context=False,
    )


def result_headers(cl):
    """
    Generate the list column headers.
    """
    ordering_field_columns = cl.get_ordering_field_columns()
    for i, field_name in enumerate(cl.list_display):
        text, attr = label_for_field(
            field_name, cl.model, model_admin=cl.model_admin, return_attr=True
        )
        is_field_sortable = cl.sortable_by is None or field_name in cl.sortable_by
        if attr:
            field_name = _coerce_field_name(field_name, i)
            # Potentially not sortable

            # if the field is the action checkbox: no sorting and special class
            if field_name == "action_checkbox":
                aria_label = _("Select all objects on this page for an action")
                yield {
                    "text": mark_safe(
                        f'<input type="checkbox" id="action-toggle" '
                        f'aria-label="{aria_label}">'
                    ),
                    "class_attrib": mark_safe(' class="action-checkbox-column"'),
                    "sortable": False,
                }
                continue

            admin_order_field = getattr(attr, "admin_order_field", None)
            # Set ordering for attr that is a property, if defined.
            if isinstance(attr, property) and hasattr(attr, "fget"):
                admin_order_field = getattr(attr.fget, "admin_order_field", None)
            if not admin_order_field:
                is_field_sortable = False

        if not is_field_sortable:
            # Not sortable
            yield {
                "text": text,
                "class_attrib": format_html(' class="column-{}"', field_name),
                "sortable": False,
            }
            continue

        # OK, it is sortable if we got this far
        th_classes = ["sortable", "column-{}".format(field_name)]
        order_type = ""
        new_order_type = "asc"
        sort_priority = 0
        # Is it currently being sorted on?
        is_sorted = i in ordering_field_columns
        if is_sorted:
            order_type = ordering_field_columns.get(i).lower()
            sort_priority = list(ordering_field_columns).index(i) + 1
            th_classes.append("sorted %sending" % order_type)
            new_order_type = {"asc": "desc", "desc": "asc"}[order_type]

        # build new ordering param
        o_list_primary = []  # URL for making this field the primary sort
        o_list_remove = []  # URL for removing this field from sort
        o_list_toggle = []  # URL for toggling order type for this field

        def make_qs_param(t, n):
            return ("-" if t == "desc" else "") + str(n)

        for j, ot in ordering_field_columns.items():
            if j == i:  # Same column
                param = make_qs_param(new_order_type, j)
                # We want clicking on this header to bring the ordering to the
                # front
                o_list_primary.insert(0, param)
                o_list_toggle.append(param)
                # o_list_remove - omit
            else:
                param = make_qs_param(ot, j)
                o_list_primary.append(param)
                o_list_toggle.append(param)
                o_list_remove.append(param)

        if i not in ordering_field_columns:
            o_list_primary.insert(0, make_qs_param(new_order_type, i))

        yield {
            "text": text,
            "sortable": True,
            "sorted": is_sorted,
            "ascending": order_type == "asc",
            "sort_priority": sort_priority,
            "url_primary": cl.get_query_string({ORDER_VAR: ".".join(o_list_primary)}),
            "url_remove": cl.get_query_string({ORDER_VAR: ".".join(o_list_remove)}),
            "url_toggle": cl.get_query_string({ORDER_VAR: ".".join(o_list_toggle)}),
            "class_attrib": format_html(' class="{}"', " ".join(th_classes))
            if th_classes
            else "",
        }


def _boolean_icon(field_val):
    icon_url = static(
        "admin/img/icon-%s.svg" % {True: "yes", False: "no", None: "unknown"}[field_val]
    )
    return format_html('<img src="{}" alt="{}">', icon_url, field_val)


def _coerce_field_name(field_name, field_index):
    """
    Coerce a field_name (which may be a callable) to a string.
    """
    if callable(field_name):
        if field_name.__name__ == "<lambda>":
            return "lambda" + str(field_index)
        else:
            return field_name.__name__
    return field_name


def items_for_result(cl, result, form):
    """
    Generate the actual list of data.
    """

    def link_in_col(is_first, field_name, cl):
        if cl.list_display_links is None:
            return False
        if is_first and not cl.list_display_links:
            return True
        return field_name in cl.list_display_links

    first = True
    pk = cl.lookup_opts.pk.attname
    for field_index, field_name in enumerate(cl.list_display):
        empty_value_display = cl.model_admin.get_empty_value_display()
        row_classes = ["field-%s" % _coerce_field_name(field_name, field_index)]
        try:
            f, attr, value = lookup_field(field_name, result, cl.model_admin)
        except ObjectDoesNotExist:
            result_repr = empty_value_display
        else:
            empty_value_display = getattr(
                attr, "empty_value_display", empty_value_display
            )
            if f is None or f.auto_created:
                if field_name == "action_checkbox":
                    row_classes = ["action-checkbox"]
                boolean = getattr(attr, "boolean", False)
                result_repr = display_for_value(value, empty_value_display, boolean)
                if isinstance(value, (datetime.date, datetime.time)):
                    row_classes.append("nowrap")
            else:
                if isinstance(f.remote_field, models.ManyToOneRel):
                    field_val = getattr(result, f.name)
                    if field_val is None:
                        result_repr = empty_value_display
                    else:
                        result_repr = field_val
                else:
                    result_repr = display_for_field(value, f, empty_value_display)
                if isinstance(
                    f, (models.DateField, models.TimeField, models.ForeignKey)
                ):
                    row_classes.append("nowrap")
        row_class = mark_safe(' class="%s"' % " ".join(row_classes))
        # If list_display_links not defined, add the link tag to the first field
        if link_in_col(first, field_name, cl):
            table_tag = "th" if first else "td"
            first = False

            # Display link to the result's change_view if the url exists, else
            # display just the result's representation.
            try:
                url = cl.url_for_result(result)
            except NoReverseMatch:
                link_or_text = result_repr
            else:
                url = add_preserved_filters(
                    {"preserved_filters": cl.preserved_filters, "opts": cl.opts}, url
                )
                # Convert the pk to something that can be used in JavaScript.
                # Problem cases are non-ASCII strings.
                if cl.to_field:
                    attr = str(cl.to_field)
                else:
                    attr = pk
                value = result.serializable_value(attr)
                link_or_text = format_html(
                    '<a href="{}"{}>{}</a>',
                    url,
                    format_html(' data-popup-opener="{}"', value)
                    if cl.is_popup
                    else "",
                    result_repr,
                )

            yield format_html(
                "<{}{}>{}</{}>", table_tag, row_class, link_or_text, table_tag
            )
        else:
            # By default the fields come from ModelAdmin.list_editable, but if we pull
            # the fields out of the form instead of list_editable custom admins
            # can provide fields on a per request basis
            if (
                form
                and field_name in form.fields
                and not (
                    field_name == cl.model._meta.pk.name
                    and form[cl.model._meta.pk.name].is_hidden
                )
            ):
                bf = form[field_name]
                result_repr = mark_safe(str(bf.errors) + str(bf))
            yield format_html("<td{}>{}</td>", row_class, result_repr)
    if form and not form[cl.model._meta.pk.name].is_hidden:
        yield format_html("<td>{}</td>", form[cl.model._meta.pk.name])


class ResultList(list):
    """
    Wrapper class used to return items in a list_editable changelist, annotated
    with the form object for error reporting purposes. Needed to maintain
    backwards compatibility with existing admin templates.
    """

    def __init__(self, form, *items):
        self.form = form
        super().__init__(*items)


def results(cl):
    if cl.formset:
        for res, form in zip(cl.result_list, cl.formset.forms):
            yield ResultList(form, items_for_result(cl, res, form))
    else:
        for res in cl.result_list:
            yield ResultList(None, items_for_result(cl, res, None))


def result_hidden_fields(cl):
    if cl.formset:
        for res, form in zip(cl.result_list, cl.formset.forms):
            if form[cl.model._meta.pk.name].is_hidden:
                yield mark_safe(form[cl.model._meta.pk.name])


def result_list(cl):
    """
    Display the headers and data list together.
    """
    headers = list(result_headers(cl))
    num_sorted_fields = 0
    for h in headers:
        if h["sortable"] and h["sorted"]:
            num_sorted_fields += 1
    return {
        "cl": cl,
        "result_hidden_fields": list(result_hidden_fields(cl)),
        "result_headers": headers,
        "num_sorted_fields": num_sorted_fields,
        "results": list(results(cl)),
    }


@register.tag(name="result_list")
def result_list_tag(parser, token):
    return InclusionAdminNode(
        parser,
        token,
        func=result_list,
        template_name="change_list_results.html",
        takes_context=False,
    )


def date_hierarchy(cl):
    """
    Display the date hierarchy for date drill-down functionality.
    """
    if cl.date_hierarchy:
        field_name = cl.date_hierarchy
        field = get_fields_from_path(cl.model, field_name)[-1]
        if isinstance(field, models.DateTimeField):
            dates_or_datetimes = "datetimes"
        else:
            dates_or_datetimes = "dates"
        year_field = "%s__year" % field_name
        month_field = "%s__month" % field_name
        day_field = "%s__day" % field_name
        field_generic = "%s__" % field_name
        year_lookup = cl.params.get(year_field)
        month_lookup = cl.params.get(month_field)
        day_lookup = cl.params.get(day_field)

        def link(filters):
            return cl.get_query_string(filters, [field_generic])

        if not (year_lookup or month_lookup or day_lookup):
            # select appropriate start level
            date_range = cl.queryset.aggregate(
                first=models.Min(field_name), last=models.Max(field_name)
            )
            if date_range["first"] and date_range["last"]:
                if dates_or_datetimes == "datetimes":
                    date_range = {
                        k: timezone.localtime(v) if timezone.is_aware(v) else v
                        for k, v in date_range.items()
                    }
                if date_range["first"].year == date_range["last"].year:
                    year_lookup = date_range["first"].year
                    if date_range["first"].month == date_range["last"].month:
                        month_lookup = date_range["first"].month

        if year_lookup and month_lookup and day_lookup:
            day = datetime.date(int(year_lookup), int(month_lookup), int(day_lookup))
            return {
                "show": True,
                "back": {
                    "link": link({year_field: year_lookup, month_field: month_lookup}),
                    "title": capfirst(formats.date_format(day, "YEAR_MONTH_FORMAT")),
                },
                "choices": [
                    {"title": capfirst(formats.date_format(day, "MONTH_DAY_FORMAT"))}
                ],
            }
        elif year_lookup and month_lookup:
            days = getattr(cl.queryset, dates_or_datetimes)(field_name, "day")
            return {
                "show": True,
                "back": {
                    "link": link({year_field: year_lookup}),
                    "title": str(year_lookup),
                },
                "choices": [
                    {
                        "link": link(
                            {
                                year_field: year_lookup,
                                month_field: month_lookup,
                                day_field: day.day,
                            }
                        ),
                        "title": capfirst(formats.date_format(day, "MONTH_DAY_FORMAT")),
                    }
                    for day in days
                ],
            }
        elif year_lookup:
            months = getattr(cl.queryset, dates_or_datetimes)(field_name, "month")
            return {
                "show": True,
                "back": {"link": link({}), "title": _("All dates")},
                "choices": [
                    {
                        "link": link(
                            {year_field: year_lookup, month_field: month.month}
                        ),
                        "title": capfirst(
                            formats.date_format(month, "YEAR_MONTH_FORMAT")
                        ),
                    }
                    for month in months
                ],
            }
        else:
            years = getattr(cl.queryset, dates_or_datetimes)(field_name, "year")
            return {
                "show": True,
                "back": None,
                "choices": [
                    {
                        "link": link({year_field: str(year.year)}),
                        "title": str(year.year),
                    }
                    for year in years
                ],
            }


@register.tag(name="date_hierarchy")
def date_hierarchy_tag(parser, token):
    return InclusionAdminNode(
        parser,
        token,
        func=date_hierarchy,
        template_name="date_hierarchy.html",
        takes_context=False,
    )


def search_form(cl):
    """
    Display a search form for searching the list.
    """
    return {
        "cl": cl,
        "show_result_count": cl.result_count != cl.full_result_count,
        "search_var": SEARCH_VAR,
        "is_popup_var": IS_POPUP_VAR,
        "is_facets_var": IS_FACETS_VAR,
    }


@register.tag(name="search_form")
def search_form_tag(parser, token):
    return InclusionAdminNode(
        parser,
        token,
        func=search_form,
        template_name="search_form.html",
        takes_context=False,
    )


@register.simple_tag
def admin_list_filter(cl, spec):
    tpl = get_template(spec.template)
    return tpl.render(
        {
            "title": spec.title,
            "choices": list(spec.choices(cl)),
            "spec": spec,
            "details_collapsed": spec.details_collapsed,
        }
    )


def admin_actions(context):
    """
    Track the number of times the action field has been rendered on the page,
    so we know which value to use.
    """
    context["action_index"] = context.get("action_index", -1) + 1
    return context


@register.tag(name="admin_actions")
def admin_actions_tag(parser, token):
    return InclusionAdminNode(
        parser, token, func=admin_actions, template_name="actions.html"
    )


@register.tag(name="change_list_object_tools")
def change_list_object_tools_tag(parser, token):
    """Display the row of change list object tools."""
    return InclusionAdminNode(
        parser,
        token,
        func=lambda context: context,
        template_name="change_list_object_tools.html",
    )
