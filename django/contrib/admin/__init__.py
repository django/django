from thibaud.contrib.admin.decorators import action, display, register
from thibaud.contrib.admin.filters import (
    AllValuesFieldListFilter,
    BooleanFieldListFilter,
    ChoicesFieldListFilter,
    DateFieldListFilter,
    EmptyFieldListFilter,
    FieldListFilter,
    ListFilter,
    RelatedFieldListFilter,
    RelatedOnlyFieldListFilter,
    SimpleListFilter,
)
from thibaud.contrib.admin.options import (
    HORIZONTAL,
    VERTICAL,
    ModelAdmin,
    ShowFacets,
    StackedInline,
    TabularInline,
)
from thibaud.contrib.admin.sites import AdminSite, site
from thibaud.utils.module_loading import autodiscover_modules

__all__ = [
    "action",
    "display",
    "register",
    "ModelAdmin",
    "HORIZONTAL",
    "VERTICAL",
    "StackedInline",
    "TabularInline",
    "AdminSite",
    "site",
    "ListFilter",
    "SimpleListFilter",
    "FieldListFilter",
    "BooleanFieldListFilter",
    "RelatedFieldListFilter",
    "ChoicesFieldListFilter",
    "DateFieldListFilter",
    "AllValuesFieldListFilter",
    "EmptyFieldListFilter",
    "RelatedOnlyFieldListFilter",
    "ShowFacets",
    "autodiscover",
]


def autodiscover():
    autodiscover_modules("admin", register_to=site)
