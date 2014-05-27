# ACTION_CHECKBOX_NAME is unused, but should stay since its import from here
# has been referenced in documentation.
from freedom.contrib.admin.decorators import register
from freedom.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from freedom.contrib.admin.options import (HORIZONTAL, VERTICAL,
    ModelAdmin, StackedInline, TabularInline)
from freedom.contrib.admin.filters import (ListFilter, SimpleListFilter,
    FieldListFilter, BooleanFieldListFilter, RelatedFieldListFilter,
    ChoicesFieldListFilter, DateFieldListFilter, AllValuesFieldListFilter)
from freedom.contrib.admin.sites import AdminSite, site
from freedom.utils.module_loading import autodiscover_modules

__all__ = [
    "register", "ACTION_CHECKBOX_NAME", "ModelAdmin", "HORIZONTAL", "VERTICAL",
    "StackedInline", "TabularInline", "AdminSite", "site", "ListFilter",
    "SimpleListFilter", "FieldListFilter", "BooleanFieldListFilter",
    "RelatedFieldListFilter", "ChoicesFieldListFilter", "DateFieldListFilter",
    "AllValuesFieldListFilter", "autodiscover",
]


def autodiscover():
    autodiscover_modules('admin', register_to=site)


default_app_config = 'freedom.contrib.admin.apps.AdminConfig'
