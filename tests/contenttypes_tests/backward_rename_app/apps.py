from django.apps import AppConfig


class BackwardRenameAppConfig(AppConfig):
    name = "contenttypes_tests.backward_rename_app"
    # Sort before "contenttypes" in the full migration plan.
    label = "app_backward_rename"
