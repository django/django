from django.apps import AppConfig

default_app_config = (
    "apps.explicit_default_config_without_apps.ExplicitDefaultConfigWithoutApps"
)


class ExplicitDefaultConfigWithoutApps(AppConfig):
    name = "apps.explicit_default_config_without_apps"
