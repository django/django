from django.apps import AppConfig

default_app_config = (
    "apps.explicit_default_config_empty_apps.ExplicitDefaultConfigEmptyApps"
)


class ExplicitDefaultConfigEmptyApps(AppConfig):
    name = "apps.explicit_default_config_empty_apps"
