from django.core.management.templates import TemplateCommand


class Command(TemplateCommand):
    help = (
        "Creates a Django app directory structure for the given app name in "
        "the current directory or optionally in the given directory."
    )
    missing_args_message = "You must provide an application name."

    def handle(self, **options):
        app_name = options.pop("name")
        target = options.pop("directory")
        import re
        import os
        settings_file = os.environ['DJANGO_SETTINGS_MODULE'].replace(".", "/") + ".py"
        with open(settings_file, 'r+') as f:
            s = f.read()
            app_list = re.search(r"INSTALLED_APPS.*?]", s, re.DOTALL)[0]
            app_new_list = app_list.replace('\n]', '') + '\n    "' + app_name + '",\n]'
            f.truncate(0)
            f.seek(0)
            settings_content = s.replace(app_list, app_new_list)
            f.write(settings_content)
        super().handle("app", app_name, target, **options)
