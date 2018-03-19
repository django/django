import unittest

from django import forms
from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.forms import modelformset_factory
from django.http import QueryDict
from django.test.utils import isolate_apps
from django.utils.alteration import AltersDataBase


class CustomQueryDict(QueryDict, metaclass=AltersDataBase):
    data_altering_methods = ('popitem',)


@isolate_apps('utils_tests')
class AltersDataTestCaseBase(unittest.TestCase):
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


class AltersDataBaseTestCase(AltersDataTestCaseBase):

    def test_dynamic_alters_data(self):
        self.assert_alters_data_true(CustomQueryDict, 'popitem')

    def test_subclass_alters_data(self):
        class SubQueryDict(CustomQueryDict):
            pass

        self.assert_alters_data_true(SubQueryDict, 'popitem')

    def test_explicit_alters_data(self):
        class SubQueryDict(CustomQueryDict):
            def popitem(self):
                return super(SubQueryDict, self).popitem()
            popitem.alters_data = False

        self.assert_alters_data_false(SubQueryDict, 'popitem')


class TestModelAltersData(AltersDataTestCaseBase):
    def test_legacy_alters_data(self):
        class GenericModel(models.Model):
            pass

        self.assert_alters_data_true(GenericModel, 'save')
        self.assert_alters_data_true(GenericModel, 'save_base')
        self.assert_alters_data_true(GenericModel, 'delete')


class TestQuerySetAltersData(AltersDataTestCaseBase):
    def test_legacy_alters_data(self):
        class GenericModel(models.Model):
            pass

        qs = GenericModel.objects.all()
        self.assert_alters_data_true(qs, 'delete')
        self.assert_alters_data_true(qs, '_raw_delete')
        self.assert_alters_data_true(qs, 'update')
        self.assert_alters_data_true(qs, '_update')
        self.assert_alters_data_true(qs, '_insert')


class TestFieldFileAltersData(AltersDataTestCaseBase):
    def test_legacy_alters_data(self):
        class Document(models.Model):
            file_path = models.FileField()

        document = Document(file_path='random/doc')
        doc = document.file_path
        self.assert_alters_data_true(doc, 'open')
        self.assert_alters_data_true(doc, 'save')
        self.assert_alters_data_true(doc, 'delete')


class TestReverseManyToOneDescriptorAltersData(AltersDataTestCaseBase):
    def test_legacy_alters_data(self):
        class Host(models.Model):
            pass

        class Document(models.Model):
            pass

        class AuditLog(models.Model):
            host = models.ForeignKey(
                to=Host, on_delete=models.PROTECT, related_name='logs'
            )
            log_file = models.ForeignKey(
                to=Document, on_delete=models.PROTECT, related_name='audits',
                null=True
            )

        host = Host()
        # not null descriptor
        reverse_descriptor = host.logs
        self.assert_alters_data_true(reverse_descriptor, 'add')
        self.assert_alters_data_true(reverse_descriptor, 'create')
        self.assert_alters_data_true(reverse_descriptor, 'get_or_create')
        self.assert_alters_data_true(reverse_descriptor, 'update_or_create')
        self.assert_alters_data_true(reverse_descriptor, 'set')

        document = Document()
        # null descriptor
        reverse_descriptor = document.audits
        self.assert_alters_data_true(reverse_descriptor, 'add')
        self.assert_alters_data_true(reverse_descriptor, 'create')
        self.assert_alters_data_true(reverse_descriptor, 'get_or_create')
        self.assert_alters_data_true(reverse_descriptor, 'update_or_create')
        self.assert_alters_data_true(reverse_descriptor, 'set')
        self.assert_alters_data_true(reverse_descriptor, 'remove')
        self.assert_alters_data_true(reverse_descriptor, 'clear')
        self.assert_alters_data_true(reverse_descriptor, '_clear')


class TestManyToManyDescriptorAltersData(AltersDataTestCaseBase):
    def test_legacy_alters_data(self):
        class AuditLog(models.Model):
            pass

        class Process(models.Model):
            logs = models.ManyToManyField(AuditLog, related_name='processes')

        log = AuditLog(id=0)
        m2m_descriptor = log.processes
        self.assert_alters_data_true(m2m_descriptor, 'add')
        self.assert_alters_data_true(m2m_descriptor, 'remove')
        self.assert_alters_data_true(m2m_descriptor, 'clear')
        self.assert_alters_data_true(m2m_descriptor, 'set')
        self.assert_alters_data_true(m2m_descriptor, 'create')
        self.assert_alters_data_true(m2m_descriptor, 'get_or_create')
        self.assert_alters_data_true(m2m_descriptor, 'update_or_create')


class TestReverseGenericManyToOneDescriptorAltersData(AltersDataTestCaseBase):
    def test_legacy_alters_data(self):
        class GenericModel(models.Model):
            pass

        class Process(models.Model):
            tags = GenericRelation(GenericModel, related_query_name='processes')

        process = Process()
        generic_descriptor = process.tags
        self.assert_alters_data_true(generic_descriptor, 'add')
        self.assert_alters_data_true(generic_descriptor, 'remove')
        self.assert_alters_data_true(generic_descriptor, 'clear')
        self.assert_alters_data_true(generic_descriptor, '_clear')
        self.assert_alters_data_true(generic_descriptor, 'set')
        self.assert_alters_data_true(generic_descriptor, 'create')
        self.assert_alters_data_true(generic_descriptor, 'get_or_create')
        self.assert_alters_data_true(generic_descriptor, 'update_or_create')


class TestModelFormAltersData(AltersDataTestCaseBase):
    def test_legacy_alters_data(self):
        class Process(models.Model):
            pass

        class ProcessForm(forms.ModelForm):
            class Meta:
                model = Process
                fields = forms.ALL_FIELDS

        self.assert_alters_data_true(ProcessForm, 'save')


class TestModelFormSetAltersData(AltersDataTestCaseBase):
    def test_legacy_alters_data(self):
        class Process(models.Model):
            pass

        class ProcessForm(forms.ModelForm):
            class Meta:
                model = Process
                fields = forms.ALL_FIELDS

        formset = modelformset_factory(Process, form=ProcessForm)
        self.assert_alters_data_true(formset, 'save')
