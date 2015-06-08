from django.apps import apps


def auto_import_consumers():
    """
    Auto-import consumers modules in apps
    """
    for app_config in apps.get_app_configs():
        consumer_module_name = "%s.consumers" % (app_config.name,)
        try:
            __import__(consumer_module_name)
        except ImportError as e:
            if "no module named consumers" not in str(e).lower():
                raise
