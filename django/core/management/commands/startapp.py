from django.core.management.base import CopyFilesCommand, CommandError
import os

class Command(CopyFilesCommand):
    help = "Creates a Django app directory structure for the given app name in the current directory."
    args = "[appname]"

    requires_model_validation = False
    # Can't import settings during this command, because they haven't
    # necessarily been created.
    can_import_settings = False

    def handle(self, app_name, directory=None, **options):
        if directory is None:
            directory = os.getcwd()
        # Determine the project_name a bit naively -- by looking at the name of
        # the parent directory.
        project_dir = os.path.normpath(os.path.join(directory, '..'))
        parent_dir = os.path.basename(project_dir)
        project_name = os.path.basename(directory)
        if app_name == project_name:
            raise CommandError("You cannot create an app with the same name (%r) as your project." % app_name)
        self.copy_helper('app', app_name, directory, parent_dir)

class ProjectCommand(Command):
    help = "Creates a Django app directory structure for the given app name in this project's directory."

    def __init__(self, project_directory):
        super(ProjectCommand, self).__init__()
        self.project_directory = project_directory

    def handle(self, app_name):
        super(ProjectCommand, self).handle(app_name, self.project_directory)
