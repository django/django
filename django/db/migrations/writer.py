from __future__ import unicode_literals

import datetime
from importlib import import_module
import os
import types

from django.apps import apps
from django.db import models
from django.db.migrations.loader import MigrationLoader
from django.utils.encoding import force_text
from django.utils.functional import Promise
from django.utils import six


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
            "dependencies": repr(self.migration.dependencies),
            "replaces_str": "",
        }
        imports = set()
        # Deconstruct operations
        operation_strings = []
        for operation in self.migration.operations:
            name, args, kwargs = operation.deconstruct()
            arg_strings = []
            for arg in args:
                arg_string, arg_imports = self.serialize(arg)
                arg_strings.append(arg_string)
                imports.update(arg_imports)
            for kw, arg in kwargs.items():
                arg_string, arg_imports = self.serialize(arg)
                imports.update(arg_imports)
                arg_strings.append("%s = %s" % (kw, arg_string))
            operation_strings.append("migrations.%s(%s\n        )" % (name, "".join("\n            %s," % arg for arg in arg_strings)))
        items["operations"] = "[%s\n    ]" % "".join("\n        %s," % s for s in operation_strings)
        # Format imports nicely
        imports.discard("from django.db import models")
        if not imports:
            items["imports"] = ""
        else:
            items["imports"] = "\n".join(imports) + "\n"
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
        arg_strings = []
        for arg in args:
            arg_string, arg_imports = cls.serialize(arg)
            arg_strings.append(arg_string)
            imports.update(arg_imports)
        for kw, arg in kwargs.items():
            arg_string, arg_imports = cls.serialize(arg)
            imports.update(arg_imports)
            arg_strings.append("%s=%s" % (kw, arg_string))
        return "%s(%s)" % (name, ", ".join(arg_strings)), imports

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
                format = "(%s,)"
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
        # Simple types
        elif isinstance(value, six.integer_types + (float, six.binary_type, six.text_type, bool, type(None))):
            return repr(value), set()
        # Promise
        elif isinstance(value, Promise):
            return repr(force_text(value)), set()
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
        # Uh oh.
        else:
            raise ValueError("Cannot serialize: %r" % value)


MIGRATION_TEMPLATE = """# encoding: utf8
from django.db import models, migrations
%(imports)s

class Migration(migrations.Migration):
    %(replaces_str)s
    dependencies = %(dependencies)s

    operations = %(operations)s
"""
