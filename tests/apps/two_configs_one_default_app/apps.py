from django.apps import AppConfig


class TwoConfig(AppConfig):
    default = True
    name = 'apps.two_configs_one_default_app'


class TwoConfigAlt(AppConfig):
    name = 'apps.two_configs_one_default_app'
