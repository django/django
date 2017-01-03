from __future__ import unicode_literals

import collections
import datetime
import decimal
import functools
import math
import types
import uuid
from importlib import import_module

from django.db import models
from django.db.migrations.operations.base import Operation
from django.db.migrations.utils import COMPILED_REGEX_TYPE, RegexObject
from django.utils import datetime_safe, six
from django.utils.encoding import force_text
from django.utils.functional import LazyObject, Promise
from django.utils.timezone import utc
from django.utils.version import get_docs_version

try:
    import enum
except ImportError:
    # No support on Python 2 if enum34 isn't installed.
    enum = None


class BaseSerializer(object):
    def __init__(self, value):
        self.value = value

    def serialize(self):
        raise NotImplementedError('Subclasses of BaseSerializer must implement the serialize() method.')


class BaseSequenceSerializer(BaseSerializer):
    def _format(self):
        raise NotImplementedError('Subclasses of BaseSequenceSerializer must implement the _format() method.')

    def serialize(self):
        imports = set()
        strings = []
        for item in self.value:
            item_string, item_imports = serializer_factory(item).serialize()
            imports.update(item_imports)
            strings.append(item_string)
        value = self._format()
        return value % (", ".join(strings)), imports


class BaseSimpleSerializer(BaseSerializer):
    def serialize(self):
        return repr(self.value), set()


class ByteTypeSerializer(BaseSerializer):
    def serialize(self):
        value_repr = repr(self.value)
        if six.PY2:
            # Prepend the `b` prefix since we're importing unicode_literals
            value_repr = 'b' + value_repr
        return value_repr, set()


class DatetimeSerializer(BaseSerializer):
    def serialize(self):
        if self.value.tzinfo is not None and self.value.tzinfo != utc:
            self.value = self.value.astimezone(utc)
        value_repr = repr(self.value).replace("<UTC>", "utc")
        if isinstance(self.value, datetime_safe.datetime):
            value_repr = "datetime.%s" % value_repr
        imports = ["import datetime"]
        if self.value.tzinfo is not None:
            imports.append("from django.utils.timezone import utc")
        return value_repr, set(imports)


class DateSerializer(BaseSerializer):
    def serialize(self):
        value_repr = repr(self.value)
        if isinstance(self.value, datetime_safe.date):
            value_repr = "datetime.%s" % value_repr
        return value_repr, {"import datetime"}


class DecimalSerializer(BaseSerializer):
    def serialize(self):
        return repr(self.value), {"from decimal import Decimal"}


class DeconstructableSerializer(BaseSerializer):
    @staticmethod
    def serialize_deconstructed(path, args, kwargs):
        name, imports = DeconstructableSerializer._serialize_path(path)
        strings = []
        for arg in args:
            arg_string, arg_imports = serializer_factory(arg).serialize()
            strings.append(arg_string)
            imports.update(arg_imports)
        for kw, arg in sorted(kwargs.items()):
            arg_string, arg_imports = serializer_factory(arg).serialize()
            imports.update(arg_imports)
            strings.append("%s=%s" % (kw, arg_string))
        return "%s(%s)" % (name, ", ".join(strings)), imports

    @staticmethod
    def _serialize_path(path):
        module, name = path.rsplit(".", 1)
        if module == "django.db.models":
            imports = {"from django.db import models"}
            name = "models.%s" % name
        else:
            imports = {"import %s" % module}
            name = path
        return name, imports

    def serialize(self):
        return self.serialize_deconstructed(*self.value.deconstruct())


class DictionarySerializer(BaseSerializer):
    def serialize(self):
        imports = set()
        strings = []
        for k, v in sorted(self.value.items()):
            k_string, k_imports = serializer_factory(k).serialize()
            v_string, v_imports = serializer_factory(v).serialize()
            imports.update(k_imports)
            imports.update(v_imports)
            strings.append((k_string, v_string))
        return "{%s}" % (", ".join("%s: %s" % (k, v) for k, v in strings)), imports


class EnumSerializer(BaseSerializer):
    def serialize(self):
        enum_class = self.value.__class__
        module = enum_class.__module__
        imports = {"import %s" % module}
        v_string, v_imports = serializer_factory(self.value.value).serialize()
        imports.update(v_imports)
        return "%s.%s(%s)" % (module, enum_class.__name__, v_string), imports


class FloatSerializer(BaseSimpleSerializer):
    def serialize(self):
        if math.isnan(self.value) or math.isinf(self.value):
            return 'float("{}")'.format(self.value), set()
        return super(FloatSerializer, self).serialize()


class FrozensetSerializer(BaseSequenceSerializer):
    def _format(self):
        return "frozenset([%s])"


class FunctionTypeSerializer(BaseSerializer):
    def serialize(self):
        if getattr(self.value, "__self__", None) and isinstance(self.value.__self__, type):
            klass = self.value.__self__
            module = klass.__module__
            return "%s.%s.%s" % (module, klass.__name__, self.value.__name__), {"import %s" % module}
        # Further error checking
        if self.value.__name__ == '<lambda>':
            raise ValueError("Cannot serialize function: lambda")
        if self.value.__module__ is None:
            raise ValueError("Cannot serialize function %r: No module" % self.value)
        # Python 3 is a lot easier, and only uses this branch if it's not local.
        if getattr(self.value, "__qualname__", None) and getattr(self.value, "__module__", None):
            if "<" not in self.value.__qualname__:  # Qualname can include <locals>
                return "%s.%s" % \
                    (self.value.__module__, self.value.__qualname__), {"import %s" % self.value.__module__}
        # Python 2/fallback version
        module_name = self.value.__module__
        # Make sure it's actually there and not an unbound method
        module = import_module(module_name)
        if not hasattr(module, self.value.__name__):
            raise ValueError(
                "Could not find function %s in %s.\n"
                "Please note that due to Python 2 limitations, you cannot "
                "serialize unbound method functions (e.g. a method "
                "declared and used in the same class body). Please move "
                "the function into the main module body to use migrations.\n"
                "For more information, see "
                "https://docs.djangoproject.com/en/%s/topics/migrations/#serializing-values"
                % (self.value.__name__, module_name, get_docs_version())
            )
        # Needed on Python 2 only
        if module_name == '__builtin__':
            return self.value.__name__, set()
        return "%s.%s" % (module_name, self.value.__name__), {"import %s" % module_name}


class FunctoolsPartialSerializer(BaseSerializer):
    def serialize(self):
        imports = {'import functools'}
        # Serialize functools.partial() arguments
        func_string, func_imports = serializer_factory(self.value.func).serialize()
        args_string, args_imports = serializer_factory(self.value.args).serialize()
        keywords_string, keywords_imports = serializer_factory(self.value.keywords).serialize()
        # Add any imports needed by arguments
        imports.update(func_imports)
        imports.update(args_imports)
        imports.update(keywords_imports)
        return (
            "functools.partial(%s, *%s, **%s)" % (
                func_string, args_string, keywords_string,
            ),
            imports,
        )


class IterableSerializer(BaseSerializer):
    def serialize(self):
        imports = set()
        strings = []
        for item in self.value:
            item_string, item_imports = serializer_factory(item).serialize()
            imports.update(item_imports)
            strings.append(item_string)
        # When len(strings)==0, the empty iterable should be serialized as
        # "()", not "(,)" because (,) is invalid Python syntax.
        value = "(%s)" if len(strings) != 1 else "(%s,)"
        return value % (", ".join(strings)), imports


class ModelFieldSerializer(DeconstructableSerializer):
    def serialize(self):
        attr_name, path, args, kwargs = self.value.deconstruct()
        return self.serialize_deconstructed(path, args, kwargs)


class ModelManagerSerializer(DeconstructableSerializer):
    def serialize(self):
        as_manager, manager_path, qs_path, args, kwargs = self.value.deconstruct()
        if as_manager:
            name, imports = self._serialize_path(qs_path)
            return "%s.as_manager()" % name, imports
        else:
            return self.serialize_deconstructed(manager_path, args, kwargs)


class OperationSerializer(BaseSerializer):
    def serialize(self):
        from django.db.migrations.writer import OperationWriter
        string, imports = OperationWriter(self.value, indentation=0).serialize()
        # Nested operation, trailing comma is handled in upper OperationWriter._write()
        return string.rstrip(','), imports


class RegexSerializer(BaseSerializer):
    def serialize(self):
        imports = {"import re"}
        regex_pattern, pattern_imports = serializer_factory(self.value.pattern).serialize()
        regex_flags, flag_imports = serializer_factory(self.value.flags).serialize()
        imports.update(pattern_imports)
        imports.update(flag_imports)
        args = [regex_pattern]
        if self.value.flags:
            args.append(regex_flags)
        return "re.compile(%s)" % ', '.join(args), imports


class SequenceSerializer(BaseSequenceSerializer):
    def _format(self):
        return "[%s]"


class SetSerializer(BaseSequenceSerializer):
    def _format(self):
        # Don't use the literal "{%s}" as it doesn't support empty set
        return "set([%s])"


class SettingsReferenceSerializer(BaseSerializer):
    def serialize(self):
        return "settings.%s" % self.value.setting_name, {"from django.conf import settings"}


class TextTypeSerializer(BaseSerializer):
    def serialize(self):
        value_repr = repr(self.value)
        if six.PY2:
            # Strip the `u` prefix since we're importing unicode_literals
            value_repr = value_repr[1:]
        return value_repr, set()


class TimedeltaSerializer(BaseSerializer):
    def serialize(self):
        return repr(self.value), {"import datetime"}


class TimeSerializer(BaseSerializer):
    def serialize(self):
        value_repr = repr(self.value)
        if isinstance(self.value, datetime_safe.time):
            value_repr = "datetime.%s" % value_repr
        return value_repr, {"import datetime"}


class TupleSerializer(BaseSequenceSerializer):
    def _format(self):
        # When len(value)==0, the empty tuple should be serialized as "()",
        # not "(,)" because (,) is invalid Python syntax.
        return "(%s)" if len(self.value) != 1 else "(%s,)"


class TypeSerializer(BaseSerializer):
    def serialize(self):
        special_cases = [
            (models.Model, "models.Model", []),
        ]
        for case, string, imports in special_cases:
            if case is self.value:
                return string, set(imports)
        if hasattr(self.value, "__module__"):
            module = self.value.__module__
            if module == six.moves.builtins.__name__:
                return self.value.__name__, set()
            else:
                return "%s.%s" % (module, self.value.__name__), {"import %s" % module}


class UUIDSerializer(BaseSerializer):
    def serialize(self):
        return "uuid.%s" % repr(self.value), {"import uuid"}


def serializer_factory(value):
    from django.db.migrations.writer import SettingsReference
    if isinstance(value, Promise):
        value = force_text(value)
    elif isinstance(value, LazyObject):
        # The unwrapped value is returned as the first item of the arguments
        # tuple.
        value = value.__reduce__()[1][0]

    if isinstance(value, models.Field):
        return ModelFieldSerializer(value)
    if isinstance(value, models.manager.BaseManager):
        return ModelManagerSerializer(value)
    if isinstance(value, Operation):
        return OperationSerializer(value)
    if isinstance(value, type):
        return TypeSerializer(value)
    # Anything that knows how to deconstruct itself.
    if hasattr(value, 'deconstruct'):
        return DeconstructableSerializer(value)

    # Unfortunately some of these are order-dependent.
    if isinstance(value, frozenset):
        return FrozensetSerializer(value)
    if isinstance(value, list):
        return SequenceSerializer(value)
    if isinstance(value, set):
        return SetSerializer(value)
    if isinstance(value, tuple):
        return TupleSerializer(value)
    if isinstance(value, dict):
        return DictionarySerializer(value)
    if enum and isinstance(value, enum.Enum):
        return EnumSerializer(value)
    if isinstance(value, datetime.datetime):
        return DatetimeSerializer(value)
    if isinstance(value, datetime.date):
        return DateSerializer(value)
    if isinstance(value, datetime.time):
        return TimeSerializer(value)
    if isinstance(value, datetime.timedelta):
        return TimedeltaSerializer(value)
    if isinstance(value, SettingsReference):
        return SettingsReferenceSerializer(value)
    if isinstance(value, float):
        return FloatSerializer(value)
    if isinstance(value, six.integer_types + (bool, type(None))):
        return BaseSimpleSerializer(value)
    if isinstance(value, six.binary_type):
        return ByteTypeSerializer(value)
    if isinstance(value, six.text_type):
        return TextTypeSerializer(value)
    if isinstance(value, decimal.Decimal):
        return DecimalSerializer(value)
    if isinstance(value, functools.partial):
        return FunctoolsPartialSerializer(value)
    if isinstance(value, (types.FunctionType, types.BuiltinFunctionType, types.MethodType)):
        return FunctionTypeSerializer(value)
    if isinstance(value, collections.Iterable):
        return IterableSerializer(value)
    if isinstance(value, (COMPILED_REGEX_TYPE, RegexObject)):
        return RegexSerializer(value)
    if isinstance(value, uuid.UUID):
        return UUIDSerializer(value)
    raise ValueError(
        "Cannot serialize: %r\nThere are some values Django cannot serialize into "
        "migration files.\nFor more, see https://docs.djangoproject.com/en/%s/"
        "topics/migrations/#migration-serializing" % (value, get_docs_version())
    )
