from __future__ import unicode_literals

import datetime
import inspect
import decimal
import collections
from importlib import import_module
import os
import types

from django.apps import apps
from django.db import models
from django.db.migrations.loader import MigrationLoader
from django.utils.encoding import force_text
from django.utils.functional import Promise
from django.utils import six


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


class OperationWriter(object):
    indentation = 2

    def __init__(self, operation):
        self.operation = operation
        self.buff = []

    def serialize(self):
        imports = set()
        name, args, kwargs = self.operation.deconstruct()
        argspec = inspect.getargspec(self.operation.__init__)
        normalized_kwargs = inspect.getcallargs(self.operation.__init__, *args, **kwargs)

        self.feed('migrations.%s(' % name)
        self.indent()
        for arg_name in argspec.args[1:]:
            arg_value = normalized_kwargs[arg_name]
            if (arg_name in self.operation.serialization_expand_args and
                    isinstance(arg_value, (list, tuple, dict))):
                if isinstance(arg_value, dict):
                    self.feed('%s={' % arg_name)
                    self.indent()
                    for key, value in arg_value.items():
                        arg_string, arg_imports = MigrationWriter.serialize(value)
                        self.feed('%s: %s,' % (repr(key), arg_string))
                        imports.update(arg_imports)
                    self.unindent()
                    self.feed('},')
                else:
                    self.feed('%s=[' % arg_name)
                    self.indent()
                    for item in arg_value:
                        arg_string, arg_imports = MigrationWriter.serialize(item)
                        self.feed('%s,' % arg_string)
                        imports.update(arg_imports)
                    self.unindent()
                    self.feed('],')
            else:
                arg_string, arg_imports = MigrationWriter.serialize(arg_value)
                self.feed('%s=%s,' % (arg_name, arg_string))
                imports.update(arg_imports)
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


class MigrationWriter(object):
    """
    Takes a Migration instance and is able to produce the contents
    of the migration file from it.
    """

    def __init__(self, migration):
        self.migration = migration

    def as_string(self):
        """
        Returns a string of the file contents.
        """
        items = {
            "replaces_str": "",
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
                dependencies.append("        %s," % repr(dependency))
        items["dependencies"] = "\n".join(dependencies) + "\n" if dependencies else ""

        # Format imports nicely
        imports.discard("from django.db import models")
        items["imports"] = "\n".join(imports) + "\n" if imports else ""

        # If there's a replaces, make a string for it
        if self.migration.replaces:
            items['replaces_str'] = "\n    replaces = %s\n" % repr(self.migration.replaces)

        return (MIGRATION_TEMPLATE % items).encode("utf8")

    @property
    def filename(self):
        return "%s.py" % self.migration.name

    @property
    def path(self):
        migrations_package_name = MigrationLoader.migrations_module(self.migration.app_label)
        # See if we can import the migrations module directly
        try:
            migrations_module = import_module(migrations_package_name)
            basedir = os.path.dirname(migrations_module.__file__)
        except ImportError:
            app_config = apps.get_app_config(self.migration.app_label)
            migrations_package_basename = migrations_package_name.split(".")[-1]

            # Alright, see if it's a direct submodule of the app
            if '%s.%s' % (app_config.name, migrations_package_basename) == migrations_package_name:
                basedir = os.path.join(app_config.path, migrations_package_basename)
            else:
                raise ImportError("Cannot open migrations module %s for app %s" % (migrations_package_name, self.migration.app_label))
        return os.path.join(basedir, self.filename)

    @classmethod
    def serialize_deconstructed(cls, path, args, kwargs):
        module, name = path.rsplit(".", 1)
        if module == "django.db.models":
            imports = set(["from django.db import models"])
            name = "models.%s" % name
        else:
            imports = set(["import %s" % module])
            name = path
        strings = []
        for arg in args:
            arg_string, arg_imports = cls.serialize(arg)
            strings.append(arg_string)
            imports.update(arg_imports)
        for kw, arg in kwargs.items():
            arg_string, arg_imports = cls.serialize(arg)
            imports.update(arg_imports)
            strings.append("%s=%s" % (kw, arg_string))
        return "%s(%s)" % (name, ", ".join(strings)), imports

    @classmethod
    def serialize(cls, value):
        """
        Serializes the value to a string that's parsable by Python, along
        with any needed imports to make that string work.
        More advanced than repr() as it can encode things
        like datetime.datetime.now.
        """
        # Sequences
        if isinstance(value, (list, set, tuple)):
            imports = set()
            strings = []
            for item in value:
                item_string, item_imports = cls.serialize(item)
                imports.update(item_imports)
                strings.append(item_string)
            if isinstance(value, set):
                format = "set([%s])"
            elif isinstance(value, tuple):
                format = "(%s)" if len(value) > 1 else "(%s,)"
            else:
                format = "[%s]"
            return format % (", ".join(strings)), imports
        # Dictionaries
        elif isinstance(value, dict):
            imports = set()
            strings = []
            for k, v in value.items():
                k_string, k_imports = cls.serialize(k)
                v_string, v_imports = cls.serialize(v)
                imports.update(k_imports)
                imports.update(v_imports)
                strings.append((k_string, v_string))
            return "{%s}" % (", ".join("%s: %s" % (k, v) for k, v in strings)), imports
        # Datetimes
        elif isinstance(value, (datetime.datetime, datetime.date)):
            return repr(value), set(["import datetime"])
        # Settings references
        elif isinstance(value, SettingsReference):
            return "settings.%s" % value.setting_name, set(["from django.conf import settings"])
        # Simple types
        elif isinstance(value, six.integer_types + (float, six.binary_type, six.text_type, bool, type(None))):
            return repr(value), set()
        # Promise
        elif isinstance(value, Promise):
            return repr(force_text(value)), set()
        # Decimal
        elif isinstance(value, decimal.Decimal):
            return repr(value), set(["from decimal import Decimal"])
        # Django fields
        elif isinstance(value, models.Field):
            attr_name, path, args, kwargs = value.deconstruct()
            return cls.serialize_deconstructed(path, args, kwargs)
        # Anything that knows how to deconstruct itself.
        elif hasattr(value, 'deconstruct'):
            return cls.serialize_deconstructed(*value.deconstruct())
        # Functions
        elif isinstance(value, (types.FunctionType, types.BuiltinFunctionType)):
            # @classmethod?
            if getattr(value, "__self__", None) and isinstance(value.__self__, type):
                klass = value.__self__
                module = klass.__module__
                return "%s.%s.%s" % (module, klass.__name__, value.__name__), set(["import %s" % module])
            elif value.__name__ == '<lambda>':
                raise ValueError("Cannot serialize function: lambda")
            elif value.__module__ is None:
                raise ValueError("Cannot serialize function %r: No module" % value)
            else:
                module = value.__module__
                return "%s.%s" % (module, value.__name__), set(["import %s" % module])
        # Classes
        elif isinstance(value, type):
            special_cases = [
                (models.Model, "models.Model", []),
            ]
            for case, string, imports in special_cases:
                if case is value:
                    return string, set(imports)
            if hasattr(value, "__module__"):
                module = value.__module__
                return "%s.%s" % (module, value.__name__), set(["import %s" % module])
        # Other iterables
        elif isinstance(value, collections.Iterable):
            imports = set()
            strings = []
            for item in value:
                item_string, item_imports = cls.serialize(item)
                imports.update(item_imports)
                strings.append(item_string)
            format = "(%s)" if len(strings) > 1 else "(%s,)"
            return format % (", ".join(strings)), imports
        # Uh oh.
        else:
            raise ValueError("Cannot serialize: %r\nThere are some values Django cannot serialize into migration files.\nFor more, see https://docs.djangoproject.com/en/dev/topics/migrations/#migration-serializing" % value)


MIGRATION_TEMPLATE = """\
# encoding: utf8
from django.db import models, migrations
%(imports)s

class Migration(migrations.Migration):
%(replaces_str)s
    dependencies = [
%(dependencies)s\
    ]

    operations = [
%(operations)s\
    ]
"""
