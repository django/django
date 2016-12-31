import unittest

from django.forms import modelformset_factory

from .forms import ProcessForm
from .models import (
    AuditLog, CustomSaveModel, Document, ExplicitAlterDataModel, GenericModel,
    Host, Process,
)


class AltersDataTestCase(unittest.TestCase):
    def assert_alters_data_true(self, obj, method):
        """
        test if object's method has alters_data set to True
        """
        meth = getattr(obj, method)
        self.assertTrue(hasattr(meth, 'alters_data'))
        self.assertTrue(meth.alters_data)

    def assert_alters_data_false(self, obj, method):
        """
        test if object's method has alters_data set to False
        """
        meth = getattr(obj, method)
        self.assertTrue(hasattr(meth, 'alters_data'))
        self.assertFalse(meth.alters_data)

    def test_legacy_alters_data(self):
        """
        test all the methods on which alters_data is manually set
        before AltersDataMixin is introduced.
        """


class TestModelAltersData(AltersDataTestCase):
    def test_legacy_alters_data(self):
        self.assert_alters_data_true(GenericModel, 'save')
        self.assert_alters_data_true(GenericModel, 'save_base')
        self.assert_alters_data_true(GenericModel, 'delete')

    def test_dynamic_alters_data(self):
        self.assert_alters_data_true(GenericModel, 'save')

    def test_subclass_alters_data(self):
        self.assert_alters_data_true(CustomSaveModel, 'save')

    def test_explicit_alters_data(self):
        self.assert_alters_data_false(ExplicitAlterDataModel, 'save')


class TestQuerySetAltersData(AltersDataTestCase):
    def test_legacy_alters_data(self):
        qs = GenericModel.objects.all()
        self.assert_alters_data_true(qs, 'delete')
        self.assert_alters_data_true(qs, '_raw_delete')
        self.assert_alters_data_true(qs, 'update')
        self.assert_alters_data_true(qs, '_update')
        self.assert_alters_data_true(qs, '_insert')


class TestFieldFileAltersData(AltersDataTestCase):
    def test_legacy_alters_data(self):
        document = Document.objects.create(file_path='random/doc')
        doc = document.file_path
        self.assert_alters_data_true(doc, 'open')
        self.assert_alters_data_true(doc, 'save')
        self.assert_alters_data_true(doc, 'delete')


class TestReverseManyToOneDescriptorAltersData(AltersDataTestCase):
    def test_legacy_alters_data(self):
        self._test_not_null_descriptor()
        self._test_null_descriptor()

    def _test_not_null_descriptor(self):
        host = Host.objects.create(name='production')
        reverse_descriptor = host.logs
        self.assert_alters_data_true(reverse_descriptor, 'add')
        self.assert_alters_data_true(reverse_descriptor, 'create')
        self.assert_alters_data_true(reverse_descriptor, 'get_or_create')
        self.assert_alters_data_true(reverse_descriptor, 'update_or_create')
        self.assert_alters_data_true(reverse_descriptor, 'set')

    def _test_null_descriptor(self):
        document = Document.objects.create(file_path='random/doc')
        reverse_descriptor = document.audits
        self.assert_alters_data_true(reverse_descriptor, 'add')
        self.assert_alters_data_true(reverse_descriptor, 'create')
        self.assert_alters_data_true(reverse_descriptor, 'get_or_create')
        self.assert_alters_data_true(reverse_descriptor, 'update_or_create')
        self.assert_alters_data_true(reverse_descriptor, 'set')
        self.assert_alters_data_true(reverse_descriptor, 'remove')
        self.assert_alters_data_true(reverse_descriptor, 'clear')
        self.assert_alters_data_true(reverse_descriptor, '_clear')


class TestManyToManyDescriptorAltersData(AltersDataTestCase):
    def test_legacy_alters_data(self):
        host = Host.objects.create(name='production')
        document = Document.objects.create(file_path='random/doc')
        log = AuditLog.objects.create(host=host, log_file=document)
        m2m_descriptor = log.processes
        self.assert_alters_data_true(m2m_descriptor, 'add')
        self.assert_alters_data_true(m2m_descriptor, 'remove')
        self.assert_alters_data_true(m2m_descriptor, 'clear')
        self.assert_alters_data_true(m2m_descriptor, 'set')
        self.assert_alters_data_true(m2m_descriptor, 'create')
        self.assert_alters_data_true(m2m_descriptor, 'get_or_create')
        self.assert_alters_data_true(m2m_descriptor, 'update_or_create')


class TestReverseGenericManyToOneDescriptorAltersData(AltersDataTestCase):
    def test_legacy_alters_data(self):
        process = Process.objects.create(name='django')
        generic_descriptor = process.tags
        self.assert_alters_data_true(generic_descriptor, 'add')
        self.assert_alters_data_true(generic_descriptor, 'remove')
        self.assert_alters_data_true(generic_descriptor, 'clear')
        self.assert_alters_data_true(generic_descriptor, '_clear')
        self.assert_alters_data_true(generic_descriptor, 'set')
        self.assert_alters_data_true(generic_descriptor, 'create')
        self.assert_alters_data_true(generic_descriptor, 'get_or_create')
        self.assert_alters_data_true(generic_descriptor, 'update_or_create')


class TestModelFormAltersData(AltersDataTestCase):
    def test_legacy_alters_data(self):
        self.assert_alters_data_true(ProcessForm, 'save')


class TestModelFormSetAltersData(AltersDataTestCase):
    def test_legacy_alters_data(self):
        formset = modelformset_factory(Process, form=ProcessForm)
        self.assert_alters_data_true(formset, 'save')
