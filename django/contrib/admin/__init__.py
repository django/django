# ACTION_CHECKBOX_NAME is unused, but should stay since its import from here
# has been referenced in documentation.
from django.contrib.admin.checks import check_admin_app
from django.contrib.admin.decorators import register
from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.contrib.admin.options import ModelAdmin, HORIZONTAL, VERTICAL
from django.contrib.admin.options import StackedInline, TabularInline
from django.contrib.admin.filters import (ListFilter, SimpleListFilter,
    FieldListFilter, BooleanFieldListFilter, RelatedFieldListFilter,
    ChoicesFieldListFilter, DateFieldListFilter, AllValuesFieldListFilter)
from django.contrib.admin.sites import AdminSite, site
from django.core import checks
from django.utils.module_loading import autodiscover_modules

__all__ = [
    "register", "ACTION_CHECKBOX_NAME", "ModelAdmin", "HORIZONTAL", "VERTICAL",
    "StackedInline", "TabularInline", "AdminSite", "site", "ListFilter",
    "SimpleListFilter", "FieldListFilter", "BooleanFieldListFilter",
    "RelatedFieldListFilter", "ChoicesFieldListFilter", "DateFieldListFilter",
    "AllValuesFieldListFilter", "autodiscover",
]


def autodiscover():
    autodiscover_modules('admin', register_to=site)

checks.register('admin')(check_admin_app)
