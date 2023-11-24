from django.core.management.templates import TemplateCommand
import os


class Command(TemplateCommand):
    help = (
        "Creates a Django app directory structure for the given app name in "
        "the current directory or optionally in the given directory."
    )
    missing_args_message = "You must provide an application name."

    def handle(self, **options):
        app_name = options.pop("name")
        target = options.pop("directory")
        super().handle("app", app_name, target, **options)

        if target is None:
            # Use current working directory if the target is not given
            target = os.getcwd()
        else:
            # Get an absolute path of a directory
            target = os.path.abspath(target)

        print(f"🎉 Fantastic! Your shiny new Django app '{app_name}' has been created! 🚀")
        print(f"📁 Explore it in your coding realm at: '{target}'")
        print("💡 Get ready to craft something extraordinary and let your creativity sparkle! ✨ Happy coding! 🌈")
