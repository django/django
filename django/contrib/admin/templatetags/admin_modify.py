import json

from django import template
from django.template.context import Context

from .base import InclusionAdminNode

register = template.Library()


def prepopulated_fields_js(context):
    """
    Create a list of prepopulated_fields that should render JavaScript for
    the prepopulated fields for both the admin form and inlines.
    """
    prepopulated_fields = []
    if "adminform" in context:
        prepopulated_fields.extend(context["adminform"].prepopulated_fields)
    if "inline_admin_formsets" in context:
        for inline_admin_formset in context["inline_admin_formsets"]:
            for inline_admin_form in inline_admin_formset:
                if inline_admin_form.original is None:
                    prepopulated_fields.extend(inline_admin_form.prepopulated_fields)

    prepopulated_fields_json = []
    for field in prepopulated_fields:
        prepopulated_fields_json.append(
            {
                "id": "#%s" % field["field"].auto_id,
                "name": field["field"].name,
                "dependency_ids": [
                    "#%s" % dependency.auto_id for dependency in field["dependencies"]
                ],
                "dependency_list": [
                    dependency.name for dependency in field["dependencies"]
                ],
                "maxLength": field["field"].field.max_length or 50,
                "allowUnicode": getattr(field["field"].field, "allow_unicode", False),
            }
        )

    context.update(
        {
            "prepopulated_fields": prepopulated_fields,
            "prepopulated_fields_json": json.dumps(prepopulated_fields_json),
        }
    )
    return context


@register.tag(name="prepopulated_fields_js")
def prepopulated_fields_js_tag(parser, token):
    return InclusionAdminNode(
        parser,
        token,
        func=prepopulated_fields_js,
        template_name="prepopulated_fields_js.html",
    )


def submit_row(context):
    """
    Display the row of buttons for delete and save.
    """
    add = context["add"]
    change = context["change"]
    is_popup = context["is_popup"]
    save_as = context["save_as"]
    show_save = context.get("show_save", True)
    show_save_and_add_another = context.get("show_save_and_add_another", True)
    show_save_and_continue = context.get("show_save_and_continue", True)
    has_add_permission = context["has_add_permission"]
    has_change_permission = context["has_change_permission"]
    has_view_permission = context["has_view_permission"]
    has_editable_inline_admin_formsets = context["has_editable_inline_admin_formsets"]
    can_save = (
        (has_change_permission and change)
        or (has_add_permission and add)
        or has_editable_inline_admin_formsets
    )
    can_save_and_add_another = (
        has_add_permission
        and not is_popup
        and (not save_as or add)
        and can_save
        and show_save_and_add_another
    )
    can_save_and_continue = (
        not is_popup and can_save and has_view_permission and show_save_and_continue
    )
    can_change = has_change_permission or has_editable_inline_admin_formsets
    ctx = Context(context)
    ctx.update(
        {
            "can_change": can_change,
            "show_delete_link": (
                not is_popup
                and context["has_delete_permission"]
                and change
                and context.get("show_delete", True)
            ),
            "show_save_as_new": not is_popup
            and has_add_permission
            and change
            and save_as,
            "show_save_and_add_another": can_save_and_add_another,
            "show_save_and_continue": can_save_and_continue,
            "show_save": show_save and can_save,
            "show_close": not (show_save and can_save),
        }
    )
    return ctx


@register.tag(name="submit_row")
def submit_row_tag(parser, token):
    return InclusionAdminNode(
        parser, token, func=submit_row, template_name="submit_line.html"
    )


@register.tag(name="change_form_object_tools")
def change_form_object_tools_tag(parser, token):
    """Display the row of change form object tools."""
    return InclusionAdminNode(
        parser,
        token,
        func=lambda context: context,
        template_name="change_form_object_tools.html",
    )


@register.filter
def cell_count(inline_admin_form):
    """Return the number of cells used in a tabular inline."""
    count = 1  # Hidden cell with hidden 'id' field
    for fieldset in inline_admin_form:
        # Count all visible fields.
        for line in fieldset:
            for field in line:
                try:
                    is_hidden = field.field.is_hidden
                except AttributeError:
                    is_hidden = field.field["is_hidden"]
                if not is_hidden:
                    count += 1
    if inline_admin_form.formset.can_delete:
        # Delete checkbox
        count += 1
    return count
