from django.apps import AppConfig


class TwoConfig(AppConfig):
    default = True
    name = "apps.two_default_configs_app"


class TwoConfigBis(AppConfig):
    default = True
    name = "apps.two_default_configs_app"
