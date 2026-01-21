from django import template

register = template.Library()


@register.filter
def has_field_errors(form):
    return any(field.errors for field in form)
