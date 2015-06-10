from __future__ import unicode_literals

import collections
import datetime
import decimal
import math
import os
import re
import sys
import types
from importlib import import_module

from django.apps import apps
from django.db import migrations, models
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.operations.base import Operation
from django.utils import datetime_safe, six
from django.utils._os import upath
from django.utils.encoding import force_text
from django.utils.functional import Promise
from django.utils.inspect import get_func_args
from django.utils.timezone import utc
from django.utils.version import get_docs_version

COMPILED_REGEX_TYPE = type(re.compile(''))


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


class MigrationWriter(object):
    """
    Takes a Migration instance and is able to produce the contents
    of the migration file from it.
    """

    def __init__(self, migration):
        self.migration = migration
        self.needs_manual_porting = False

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
                # No need to output bytestrings for dependencies
                dependency = tuple(force_text(s) for s in dependency)
                dependencies.append("        %s," % self.serialize(dependency)[0])
        items["dependencies"] = "\n".join(dependencies) + "\n" if dependencies else ""

        # Format imports nicely, swapping imports of functions from migration files
        # for comments
        migration_imports = set()
        for line in list(imports):
            if re.match("^import (.*)\.\d+[^\s]*$", line):
                migration_imports.add(line.split("import")[1].strip())
                imports.remove(line)
                self.needs_manual_porting = True
        imports.discard("from django.db import models")
        items["imports"] = "\n".join(imports) + "\n" if imports else ""
        if migration_imports:
            items["imports"] += (
                "\n\n# Functions from the following migrations need manual "
                "copying.\n# Move them and any dependencies into this file, "
                "then update the\n# RunPython operations to refer to the local "
                "versions:\n# %s"
            ) % "\n# ".join(migration_imports)
        # If there's a replaces, make a string for it
        if self.migration.replaces:
            items['replaces_str'] = "\n    replaces = %s\n" % self.serialize(self.migration.replaces)[0]

        return (MIGRATION_TEMPLATE % items).encode("utf8")

    @staticmethod
    def serialize_datetime(value):
        """
        Returns a serialized version of a datetime object that is valid,
        executable python code. It converts timezone-aware values to utc with
        an 'executable' utc representation of tzinfo.
        """
        if value.tzinfo is not None and value.tzinfo != utc:
            value = value.astimezone(utc)
        value_repr = repr(value).replace("<UTC>", "utc")
        if isinstance(value, datetime_safe.datetime):
            value_repr = "datetime.%s" % value_repr
        return value_repr

    @property
    def filename(self):
        return "%s.py" % self.migration.name

    @property
    def path(self):
        migrations_package_name = MigrationLoader.migrations_module(self.migration.app_label)
        # See if we can import the migrations module directly
        try:
            migrations_module = import_module(migrations_package_name)

            # Python 3 fails when the migrations directory does not have a
            # __init__.py file
            if not hasattr(migrations_module, '__file__'):
                raise ImportError

            basedir = os.path.dirname(upath(migrations_module.__file__))
        except ImportError:
            app_config = apps.get_app_config(self.migration.app_label)
            migrations_package_basename = migrations_package_name.split(".")[-1]

            # Alright, see if it's a direct submodule of the app
            if '%s.%s' % (app_config.name, migrations_package_basename) == migrations_package_name:
                basedir = os.path.join(app_config.path, migrations_package_basename)
            else:
                # In case of using MIGRATION_MODULES setting and the custom
                # package doesn't exist, create one.
                package_dirs = migrations_package_name.split(".")
                create_path = os.path.join(upath(sys.path[0]), *package_dirs)
                if not os.path.isdir(create_path):
                    os.makedirs(create_path)
                for i in range(1, len(package_dirs) + 1):
                    init_dir = os.path.join(upath(sys.path[0]), *package_dirs[:i])
                    init_path = os.path.join(init_dir, "__init__.py")
                    if not os.path.isfile(init_path):
                        open(init_path, "w").close()
                return os.path.join(create_path, self.filename)
        return os.path.join(basedir, self.filename)

    @classmethod
    def serialize_deconstructed(cls, path, args, kwargs):
        name, imports = cls._serialize_path(path)
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
    def _serialize_path(cls, path):
        module, name = path.rsplit(".", 1)
        if module == "django.db.models":
            imports = {"from django.db import models"}
            name = "models.%s" % name
        else:
            imports = {"import %s" % module}
            name = path
        return name, imports

    @classmethod
    def serialize(cls, value):
        """
        Serializes the value to a string that's parsable by Python, along
        with any needed imports to make that string work.
        More advanced than repr() as it can encode things
        like datetime.datetime.now.
        """
        # FIXME: Ideally Promise would be reconstructible, but for now we
        # use force_text on them and defer to the normal string serialization
        # process.
        if isinstance(value, Promise):
            value = force_text(value)

        # Sequences
        if isinstance(value, (list, set, tuple)):
            imports = set()
            strings = []
            for item in value:
                item_string, item_imports = cls.serialize(item)
                imports.update(item_imports)
                strings.append(item_string)
            if isinstance(value, set):
                # Don't use the literal "{%s}" as it doesn't support empty set
                format = "set([%s])"
            elif isinstance(value, tuple):
                # When len(value)==0, the empty tuple should be serialized as
                # "()", not "(,)" because (,) is invalid Python syntax.
                format = "(%s)" if len(value) != 1 else "(%s,)"
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
        elif isinstance(value, datetime.datetime):
            value_repr = cls.serialize_datetime(value)
            imports = ["import datetime"]
            if value.tzinfo is not None:
                imports.append("from django.utils.timezone import utc")
            return value_repr, set(imports)
        # Dates
        elif isinstance(value, datetime.date):
            value_repr = repr(value)
            if isinstance(value, datetime_safe.date):
                value_repr = "datetime.%s" % value_repr
            return value_repr, {"import datetime"}
        # Times
        elif isinstance(value, datetime.time):
            value_repr = repr(value)
            if isinstance(value, datetime_safe.time):
                value_repr = "datetime.%s" % value_repr
            return value_repr, {"import datetime"}
        # Timedeltas
        elif isinstance(value, datetime.timedelta):
            return repr(value), {"import datetime"}
        # Settings references
        elif isinstance(value, SettingsReference):
            return "settings.%s" % value.setting_name, {"from django.conf import settings"}
        # Simple types
        elif isinstance(value, float):
            if math.isnan(value) or math.isinf(value):
                return 'float("{}")'.format(value), set()
            return repr(value), set()
        elif isinstance(value, six.integer_types + (bool, type(None))):
            return repr(value), set()
        elif isinstance(value, six.binary_type):
            value_repr = repr(value)
            if six.PY2:
                # Prepend the `b` prefix since we're importing unicode_literals
                value_repr = 'b' + value_repr
            return value_repr, set()
        elif isinstance(value, six.text_type):
            value_repr = repr(value)
            if six.PY2:
                # Strip the `u` prefix since we're importing unicode_literals
                value_repr = value_repr[1:]
            return value_repr, set()
        # Decimal
        elif isinstance(value, decimal.Decimal):
            return repr(value), {"from decimal import Decimal"}
        # Django fields
        elif isinstance(value, models.Field):
            attr_name, path, args, kwargs = value.deconstruct()
            return cls.serialize_deconstructed(path, args, kwargs)
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
                if module == six.moves.builtins.__name__:
                    return value.__name__, set()
                else:
                    return "%s.%s" % (module, value.__name__), {"import %s" % module}
        elif isinstance(value, models.manager.BaseManager):
            as_manager, manager_path, qs_path, args, kwargs = value.deconstruct()
            if as_manager:
                name, imports = cls._serialize_path(qs_path)
                return "%s.as_manager()" % name, imports
            else:
                return cls.serialize_deconstructed(manager_path, args, kwargs)
        elif isinstance(value, Operation):
            string, imports = OperationWriter(value, indentation=0).serialize()
            # Nested operation, trailing comma is handled in upper OperationWriter._write()
            return string.rstrip(','), imports
        # Anything that knows how to deconstruct itself.
        elif hasattr(value, 'deconstruct'):
            return cls.serialize_deconstructed(*value.deconstruct())
        # Functions
        elif isinstance(value, (types.FunctionType, types.BuiltinFunctionType)):
            # @classmethod?
            if getattr(value, "__self__", None) and isinstance(value.__self__, type):
                klass = value.__self__
                module = klass.__module__
                return "%s.%s.%s" % (module, klass.__name__, value.__name__), {"import %s" % module}
            # Further error checking
            if value.__name__ == '<lambda>':
                raise ValueError("Cannot serialize function: lambda")
            if value.__module__ is None:
                raise ValueError("Cannot serialize function %r: No module" % value)
            # Python 3 is a lot easier, and only uses this branch if it's not local.
            if getattr(value, "__qualname__", None) and getattr(value, "__module__", None):
                if "<" not in value.__qualname__:  # Qualname can include <locals>
                    return "%s.%s" % (value.__module__, value.__qualname__), {"import %s" % value.__module__}
            # Python 2/fallback version
            module_name = value.__module__
            # Make sure it's actually there and not an unbound method
            module = import_module(module_name)
            if not hasattr(module, value.__name__):
                raise ValueError(
                    "Could not find function %s in %s.\n"
                    "Please note that due to Python 2 limitations, you cannot "
                    "serialize unbound method functions (e.g. a method "
                    "declared and used in the same class body). Please move "
                    "the function into the main module body to use migrations.\n"
                    "For more information, see "
                    "https://docs.djangoproject.com/en/%s/topics/migrations/#serializing-values"
                    % (value.__name__, module_name, get_docs_version()))
            return "%s.%s" % (module_name, value.__name__), {"import %s" % module_name}
        # Other iterables
        elif isinstance(value, collections.Iterable):
            imports = set()
            strings = []
            for item in value:
                item_string, item_imports = cls.serialize(item)
                imports.update(item_imports)
                strings.append(item_string)
            # When len(strings)==0, the empty iterable should be serialized as
            # "()", not "(,)" because (,) is invalid Python syntax.
            format = "(%s)" if len(strings) != 1 else "(%s,)"
            return format % (", ".join(strings)), imports
        # Compiled regex
        elif isinstance(value, COMPILED_REGEX_TYPE):
            imports = {"import re"}
            regex_pattern, pattern_imports = cls.serialize(value.pattern)
            regex_flags, flag_imports = cls.serialize(value.flags)
            imports.update(pattern_imports)
            imports.update(flag_imports)
            args = [regex_pattern]
            if value.flags:
                args.append(regex_flags)
            return "re.compile(%s)" % ', '.join(args), imports
        # Uh oh.
        else:
            raise ValueError(
                "Cannot serialize: %r\nThere are some values Django cannot serialize into "
                "migration files.\nFor more, see https://docs.djangoproject.com/en/%s/"
                "topics/migrations/#migration-serializing" % (value, get_docs_version())
            )


MIGRATION_TEMPLATE = """\
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
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
