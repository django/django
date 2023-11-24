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
        
        target = os.path.join(target, project_name)

        def print_file_structure(base_path, indent='    '*2):
            for item in os.listdir(base_path):
                if item == '__pycache__':
                    continue

                item_path = os.path.join(base_path, item)

                if os.path.isfile(item_path):
                    print(f'{indent}{item}')
                elif os.path.isdir(item_path):
                    print(f'{indent}{item}/')
                    print_file_structure(item_path, indent + '    ')

        print(f'Success! Created {project_name} at {target}')

        print('\nProject structure:')
        print(f'    {os.path.basename(target)}/')
        print_file_structure(target)

        print('\nNext Steps:')
        print(f'    cd {project_name}/')
        print('    python manage.py runserver')

        print('\nHappy coding!')