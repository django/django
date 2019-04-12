# ACTION_CHECKBOX_NAME is unused, but should stay since its import from here
# has been referenced in documentation.
from django.contrib.admin.decorators import register
from django.contrib.admin.filters import (
    AllValuesFieldListFilter,
    BooleanFieldListFilter,
    ChoicesFieldListFilter,
    DateFieldListFilter,
    FieldListFilter,
    ListFilter,
    RelatedFieldListFilter,
    RelatedOnlyFieldListFilter,
    SimpleListFilter,
)
from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.contrib.admin.options import (
    HORIZONTAL,
    VERTICAL,
    ModelAdmin,
    StackedInline,
    TabularInline,
)
from django.contrib.admin.sites import AdminSite, site
from django.utils.module_loading import autodiscover_modules

__all__ = [
    "register",
    "ACTION_CHECKBOX_NAME",
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
    "RelatedOnlyFieldListFilter",
    "autodiscover",
]


def autodiscover():
    autodiscover_modules("admin", register_to=site)


default_app_config = "django.contrib.admin.apps.AdminConfig"
