import importlib
import unittest
from io import StringIO

from django.core import management, serializers
from django.core.serializers.base import DeserializationError
from django.test import SimpleTestCase, TestCase, TransactionTestCase

from .models import Author
from .tests import SerializersTestBase, SerializersTransactionTestBase

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

YAML_IMPORT_ERROR_MESSAGE = r'No module named yaml'


class YamlImportModuleMock:
    """Provides a wrapped import_module function to simulate yaml ImportError

    In order to run tests that verify the behavior of the YAML serializer
    when run on a system that has yaml installed (like the django CI server),
    mock import_module, so that it raises an ImportError when the yaml
    serializer is being imported.  The importlib.import_module() call is
    being made in the serializers.register_serializer().

    Refs: #12756
    """
    def __init__(self):
        self._import_module = importlib.import_module

    def import_module(self, module_path):
        if module_path == serializers.BUILTIN_SERIALIZERS['yaml']:
            raise ImportError(YAML_IMPORT_ERROR_MESSAGE)

        return self._import_module(module_path)


class NoYamlSerializerTestCase(SimpleTestCase):
    """Not having pyyaml installed provides a misleading error

    Refs: #12756
    """
    @classmethod
    def setUpClass(cls):
        """Removes imported yaml and stubs importlib.import_module"""
        super().setUpClass()

        cls._import_module_mock = YamlImportModuleMock()
        importlib.import_module = cls._import_module_mock.import_module

        # clear out cached serializers to emulate yaml missing
        serializers._serializers = {}

    @classmethod
    def tearDownClass(cls):
        """Puts yaml back if necessary"""
        super().tearDownClass()

        importlib.import_module = cls._import_module_mock._import_module

        # clear out cached serializers to clean out BadSerializer instances
        serializers._serializers = {}

    def test_serializer_pyyaml_error_message(self):
        """Using yaml serializer without pyyaml raises ImportError"""
        jane = Author(name="Jane")
        with self.assertRaises(ImportError):
            serializers.serialize("yaml", [jane])

    def test_deserializer_pyyaml_error_message(self):
        """Using yaml deserializer without pyyaml raises ImportError"""
        with self.assertRaises(ImportError):
            serializers.deserialize("yaml", "")

    def test_dumpdata_pyyaml_error_message(self):
        """Calling dumpdata produces an error when yaml package missing"""
        with self.assertRaisesMessage(management.CommandError, YAML_IMPORT_ERROR_MESSAGE):
            management.call_command('dumpdata', format='yaml')


@unittest.skipUnless(HAS_YAML, "No yaml library detected")
class YamlSerializerTestCase(SerializersTestBase, TestCase):
    serializer_name = "yaml"
    fwd_ref_str = """- fields:
    headline: Forward references pose no problem
    pub_date: 2006-06-16 15:00:00
    categories: [1]
    author: 1
  pk: 1
  model: serializers.article
- fields:
    name: Reference
  pk: 1
  model: serializers.category
- fields:
    name: Agnes
  pk: 1
  model: serializers.author"""

    pkless_str = """- fields:
    name: Reference
  pk: null
  model: serializers.category
- fields:
    name: Non-fiction
  model: serializers.category"""

    mapping_ordering_str = """- model: serializers.article
  pk: %(article_pk)s
  fields:
    author: %(author_pk)s
    headline: Poker has no place on ESPN
    pub_date: 2006-06-16 11:00:00
    categories: [%(first_category_pk)s, %(second_category_pk)s]
    meta_data: []
"""

    @staticmethod
    def _validate_output(serial_str):
        try:
            yaml.safe_load(StringIO(serial_str))
        except Exception:
            return False
        else:
            return True

    @staticmethod
    def _get_pk_values(serial_str):
        ret_list = []
        stream = StringIO(serial_str)
        for obj_dict in yaml.safe_load(stream):
            ret_list.append(obj_dict["pk"])
        return ret_list

    @staticmethod
    def _get_field_values(serial_str, field_name):
        ret_list = []
        stream = StringIO(serial_str)
        for obj_dict in yaml.safe_load(stream):
            if "fields" in obj_dict and field_name in obj_dict["fields"]:
                field_value = obj_dict["fields"][field_name]
                # yaml.safe_load will return non-string objects for some
                # of the fields we are interested in, this ensures that
                # everything comes back as a string
                if isinstance(field_value, str):
                    ret_list.append(field_value)
                else:
                    ret_list.append(str(field_value))
        return ret_list

    def test_yaml_deserializer_exception(self):
        with self.assertRaises(DeserializationError):
            for obj in serializers.deserialize("yaml", "{"):
                pass


@unittest.skipUnless(HAS_YAML, "No yaml library detected")
class YamlSerializerTransactionTestCase(SerializersTransactionTestBase, TransactionTestCase):
    serializer_name = "yaml"
    fwd_ref_str = """- fields:
    headline: Forward references pose no problem
    pub_date: 2006-06-16 15:00:00
    categories: [1]
    author: 1
  pk: 1
  model: serializers.article
- fields:
    name: Reference
  pk: 1
  model: serializers.category
- fields:
    name: Agnes
  pk: 1
  model: serializers.author"""
