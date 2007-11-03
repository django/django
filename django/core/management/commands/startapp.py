import os

from django.core.management.base import copy_helper, CommandError, LabelCommand

class Command(LabelCommand):
    help = ("Creates a Django app directory structure for the given app name"
            " in the current directory.")
    args = "[appname]"
    label = 'application name'

    requires_model_validation = False
    # Can't import settings during this command, because they haven't
    # necessarily been created.
    can_import_settings = False

    def handle_label(self, app_name, directory=None, **options):
        if directory is None:
            directory = os.getcwd()
        # Determine the project_name by using the basename of directory,
        # which should be the full path of the project directory (or the
        # current directory if no directory was passed).
        project_name = os.path.basename(directory)
        if app_name == project_name:
            raise CommandError("You cannot create an app with the same name"
                               " (%r) as your project." % app_name)
        copy_helper(self.style, 'app', app_name, directory, project_name)

class ProjectCommand(Command):
    help = ("Creates a Django app directory structure for the given app name"
            " in this project's directory.")

    def __init__(self, project_directory):
        super(ProjectCommand, self).__init__()
        self.project_directory = project_directory

    def handle_label(self, app_name, **options):
        super(ProjectCommand, self).handle_label(app_name, self.project_directory, **options)
