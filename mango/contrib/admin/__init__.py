from mango.contrib.admin.decorators import action, display, register
from mango.contrib.admin.filters import (
    AllValuesFieldListFilter, BooleanFieldListFilter, ChoicesFieldListFilter,
    DateFieldListFilter, EmptyFieldListFilter, FieldListFilter, ListFilter,
    RelatedFieldListFilter, RelatedOnlyFieldListFilter, SimpleListFilter,
)
from mango.contrib.admin.options import (
    HORIZONTAL, VERTICAL, ModelAdmin, StackedInline, TabularInline,
)
from mango.contrib.admin.sites import AdminSite, site
from mango.utils.module_loading import autodiscover_modules

__all__ = [
    "action", "display", "register", "ModelAdmin", "HORIZONTAL", "VERTICAL",
    "StackedInline", "TabularInline", "AdminSite", "site", "ListFilter",
    "SimpleListFilter", "FieldListFilter", "BooleanFieldListFilter",
    "RelatedFieldListFilter", "ChoicesFieldListFilter", "DateFieldListFilter",
    "AllValuesFieldListFilter", "EmptyFieldListFilter",
    "RelatedOnlyFieldListFilter", "autodiscover",
]


def autodiscover():
    autodiscover_modules('admin', register_to=site)
