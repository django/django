import os
import re
from importlib import import_module

from django import get_version
from django.apps import apps
from django.db import migrations
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.serializer import serializer_factory
from django.utils.encoding import force_text
from django.utils.inspect import get_func_args
from django.utils.module_loading import module_dir
from django.utils.timezone import now


class SettingsReference(str):
    """
    Special subclass of string which actually references a current settings
    value. It's treated as the value in memory, but serializes out to a
    settings.NAME attribute reference.
    """

    def __new__(self, value, setting_name):
        return str.__new__(self, value)

    def __init__(self, value, setting_name):
        self.setting_name = setting_name


class OperationWriter:
    def __init__(self, operation, indentation=2):
        self.operation = operation
        self.buff = []
        self.indentation = indentation

    def serialize(self):

        def _write(_arg_name, _arg_value):
            if (_arg_name in self.operation.serialization_expand_args and
                    isinstance(_arg_value, (list, tuple, dict))):
                if isinstance(_arg_value, dict):
                    self.feed('%s={' % _arg_name)
                    self.indent()
                    for key, value in _arg_value.items():
                        key_string, key_imports = MigrationWriter.serialize(key)
                        arg_string, arg_imports = MigrationWriter.serialize(value)
                        args = arg_string.splitlines()
                        if len(args) > 1:
                            self.feed('%s: %s' % (key_string, args[0]))
                            for arg in args[1:-1]:
                                self.feed(arg)
                            self.feed('%s,' % args[-1])
                        else:
                            self.feed('%s: %s,' % (key_string, arg_string))
                        imports.update(key_imports)
                        imports.update(arg_imports)
                    self.unindent()
                    self.feed('},')
                else:
                    self.feed('%s=[' % _arg_name)
                    self.indent()
                    for item in _arg_value:
                        arg_string, arg_imports = MigrationWriter.serialize(item)
                        args = arg_string.splitlines()
                        if len(args) > 1:
                            for arg in args[:-1]:
                                self.feed(arg)
                            self.feed('%s,' % args[-1])
                        else:
                            self.feed('%s,' % arg_string)
                        imports.update(arg_imports)
                    self.unindent()
                    self.feed('],')
            else:
                arg_string, arg_imports = MigrationWriter.serialize(_arg_value)
                args = arg_string.splitlines()
                if len(args) > 1:
                    self.feed('%s=%s' % (_arg_name, args[0]))
                    for arg in args[1:-1]:
                        self.feed(arg)
                    self.feed('%s,' % args[-1])
                else:
                    self.feed('%s=%s,' % (_arg_name, arg_string))
                imports.update(arg_imports)

        imports = set()
        name, args, kwargs = self.operation.deconstruct()
        operation_args = get_func_args(self.operation.__init__)

        # See if this operation is in django.db.migrations. If it is,
        # We can just use the fact we already have that imported,
        # otherwise, we need to add an import for the operation class.
        if getattr(migrations, name, None) == self.operation.__class__:
            self.feed('migrations.%s(' % name)
        else:
            imports.add('import %s' % (self.operation.__class__.__module__))
            self.feed('%s.%s(' % (self.operation.__class__.__module__, name))

        self.indent()

        for i, arg in enumerate(args):
            arg_value = arg
            arg_name = operation_args[i]
            _write(arg_name, arg_value)

        i = len(args)
        # Only iterate over remaining arguments
        for arg_name in operation_args[i:]:
            if arg_name in kwargs:  # Don't sort to maintain signature order
                arg_value = kwargs[arg_name]
                _write(arg_name, arg_value)

        self.unindent()
        self.feed('),')
        return self.render(), imports

    def indent(self):
        self.indentation += 1

    def unindent(self):
        self.indentation -= 1

    def feed(self, line):
        self.buff.append(' ' * (self.indentation * 4) + line)

    def render(self):
        return '\n'.join(self.buff)


class MigrationWriter:
    """
    Take a Migration instance and is able to produce the contents
    of the migration file from it.
    """

    def __init__(self, migration):
        self.migration = migration
        self.needs_manual_porting = False

    def as_string(self):
        """Return a string of the file contents."""
        items = {
            "replaces_str": "",
            "initial_str": "",
        }

        imports = set()

        # Deconstruct operations
        operations = []
        for operation in self.migration.operations:
            operation_string, operation_imports = OperationWriter(operation).serialize()
            imports.update(operation_imports)
            operations.append(operation_string)
        items["operations"] = "\n".join(operations) + "\n" if operations else ""

        # Format dependencies and write out swappable dependencies right
        dependencies = []
        for dependency in self.migration.dependencies:
            if dependency[0] == "__setting__":
                dependencies.append("        migrations.swappable_dependency(settings.%s)," % dependency[1])
                imports.add("from django.conf import settings")
            else:
                # No need to output bytestrings for dependencies
                dependency = tuple(force_text(s) for s in dependency)
                dependencies.append("        %s," % self.serialize(dependency)[0])
        items["dependencies"] = "\n".join(dependencies) + "\n" if dependencies else ""

        # Format imports nicely, swapping imports of functions from migration files
        # for comments
        migration_imports = set()
        for line in list(imports):
            if re.match(r"^import (.*)\.\d+[^\s]*$", line):
                migration_imports.add(line.split("import")[1].strip())
                imports.remove(line)
                self.needs_manual_porting = True

        # django.db.migrations is always used, but models import may not be.
        # If models import exists, merge it with migrations import.
        if "from django.db import models" in imports:
            imports.discard("from django.db import models")
            imports.add("from django.db import migrations, models")
        else:
            imports.add("from django.db import migrations")

        # Sort imports by the package / module to be imported (the part after
        # "from" in "from ... import ..." or after "import" in "import ...").
        sorted_imports = sorted(imports, key=lambda i: i.split()[1])
        items["imports"] = "\n".join(sorted_imports) + "\n" if imports else ""
        if migration_imports:
            items["imports"] += (
                "\n\n# Functions from the following migrations need manual "
                "copying.\n# Move them and any dependencies into this file, "
                "then update the\n# RunPython operations to refer to the local "
                "versions:\n# %s"
            ) % "\n# ".join(sorted(migration_imports))
        # If there's a replaces, make a string for it
        if self.migration.replaces:
            items['replaces_str'] = "\n    replaces = %s\n" % self.serialize(self.migration.replaces)[0]
        # Hinting that goes into comment
        items.update(
            version=get_version(),
            timestamp=now().strftime("%Y-%m-%d %H:%M"),
        )

        if self.migration.initial:
            items['initial_str'] = "\n    initial = True\n"

        return MIGRATION_TEMPLATE % items

    @property
    def basedir(self):
        migrations_package_name, _ = MigrationLoader.migrations_module(self.migration.app_label)

        if migrations_package_name is None:
            raise ValueError(
                "Django can't create migrations for app '%s' because "
                "migrations have been disabled via the MIGRATION_MODULES "
                "setting." % self.migration.app_label
            )

        # See if we can import the migrations module directly
        try:
            migrations_module = import_module(migrations_package_name)
        except ImportError:
            pass
        else:
            try:
                return module_dir(migrations_module)
            except ValueError:
                pass

        # Alright, see if it's a direct submodule of the app
        app_config = apps.get_app_config(self.migration.app_label)
        maybe_app_name, _, migrations_package_basename = migrations_package_name.rpartition(".")
        if app_config.name == maybe_app_name:
            return os.path.join(app_config.path, migrations_package_basename)

        # In case of using MIGRATION_MODULES setting and the custom package
        # doesn't exist, create one, starting from an existing package
        existing_dirs, missing_dirs = migrations_package_name.split("."), []
        while existing_dirs:
            missing_dirs.insert(0, existing_dirs.pop(-1))
            try:
                base_module = import_module(".".join(existing_dirs))
            except ImportError:
                continue
            else:
                try:
                    base_dir = module_dir(base_module)
                except ValueError:
                    continue
                else:
                    break
        else:
            raise ValueError(
                "Could not locate an appropriate location to create "
                "migrations package %s. Make sure the toplevel "
                "package exists and can be imported." %
                migrations_package_name)

        final_dir = os.path.join(base_dir, *missing_dirs)
        if not os.path.isdir(final_dir):
            os.makedirs(final_dir)
        for missing_dir in missing_dirs:
            base_dir = os.path.join(base_dir, missing_dir)
            with open(os.path.join(base_dir, "__init__.py"), "w"):
                pass

        return final_dir

    @property
    def filename(self):
        return "%s.py" % self.migration.name

    @property
    def path(self):
        return os.path.join(self.basedir, self.filename)

    @classmethod
    def serialize(cls, value):
        return serializer_factory(value).serialize()


MIGRATION_TEMPLATE = """\
# Generated by Django %(version)s on %(timestamp)s

%(imports)s

class Migration(migrations.Migration):
%(replaces_str)s%(initial_str)s
    dependencies = [
%(dependencies)s\
    ]

    operations = [
%(operations)s\
    ]
"""
