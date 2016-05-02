from django.apps import apps
from django.db import models
from django.test import SimpleTestCase
from django.test.utils import isolate_apps


class ManyToManyFieldTests(SimpleTestCase):

    def test_abstract_model_pending_operations(self):
        """
        Many-to-many fields declared on abstract models should not add lazy
        relations to resolve relationship declared as string (#24215).
        """
        pending_ops_before = list(apps._pending_operations.items())

        class AbstractManyToManyModel(models.Model):
            fk = models.ForeignKey('missing.FK', models.CASCADE)

            class Meta:
                abstract = True

        self.assertIs(AbstractManyToManyModel._meta.apps, apps)
        self.assertEqual(
            pending_ops_before,
            list(apps._pending_operations.items()),
            'Pending lookup added for a many-to-many field on an abstract model'
        )

    @isolate_apps('model_fields', 'model_fields.tests')
    def test_abstract_model_app_relative_foreign_key(self):
        class AbstractReferent(models.Model):
            reference = models.ManyToManyField('Refered', through='Through')

            class Meta:
                app_label = 'model_fields'
                abstract = True

        def assert_app_model_resolved(label):
            class Refered(models.Model):
                class Meta:
                    app_label = label

            class Through(models.Model):
                refered = models.ForeignKey('Refered', on_delete=models.CASCADE)
                referent = models.ForeignKey('ConcreteReferent', on_delete=models.CASCADE)

                class Meta:
                    app_label = label

            class ConcreteReferent(AbstractReferent):
                class Meta:
                    app_label = label

            self.assertEqual(ConcreteReferent._meta.get_field('reference').related_model, Refered)
            self.assertEqual(ConcreteReferent.reference.through, Through)

        assert_app_model_resolved('model_fields')
        assert_app_model_resolved('tests')
