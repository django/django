from django.core.checks.security.base import SECRET_KEY_INSECURE_PREFIX
from django.core.management.templates import TemplateCommand
import os
from ..utils import get_random_secret_key


class Command(TemplateCommand):
    help = (
        "Creates a Django project directory structure for the given project "
        "name in the current directory or optionally in the given directory."
    )
    missing_args_message = "You must provide a project name."

    def handle(self, **options):
        project_name = options.pop("name")
        target = options.pop("directory")

        # Create a random SECRET_KEY to put it in the main settings.
        options["secret_key"] = SECRET_KEY_INSECURE_PREFIX + get_random_secret_key()

        super().handle("project", project_name, target, **options)

        if target is None:
            # Use current working directory if the target is not given
            target = os.getcwd()
        else:
            # Get an absolute path of a directory
            target = os.path.abspath(target)

        print(f"🚀 Hooray! Your brand new project '{project_name}' is now ready to soar! 🌟")
        print(f"📁 Find it in your workspace at: '{target}'")
        print("💡 Get ready to bring your ideas to life and create something amazing! Happy coding! 🎉")
