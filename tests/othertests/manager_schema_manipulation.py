"""
# Django uses a model's default manager to perform schema manipulations such as
# creating or dropping the model's table.

>>> from django.db import models
    
# default connection
>>> class DA(models.Model):
...     name = models.CharField(maxlength=20)
...     
...     def __str__(self):
...         return self.name
    
# connection django_test_db_a
>>> class PA(models.Model):
...     name = models.CharField(maxlength=20)
...     # This creates a cycle in the dependency graph
...     c = models.ForeignKey('PC', null=True)
...     
...     def __str__(self):
...         return self.name
...     
...     class Meta:
...         db_connection = 'django_test_db_a'

>>> class PB(models.Model):
...     name = models.CharField(maxlength=20)
...     a = models.ForeignKey(PA)
...     
...     def __str__(self):
...         return self.name
...     
...     class Meta:
...         db_connection = 'django_test_db_a'

>>> class PC(models.Model):
...     name = models.CharField(maxlength=20)
...     b = models.ForeignKey(PB)
...     
...     def __str__(self):
...         return self.name
...     
...     class Meta:
...         db_connection = 'django_test_db_a'
    
# connection django_test_db_b
>>> class QA(models.Model):
...     name = models.CharField(maxlength=20)
...     
...     def __str__(self):
...         return self.name
...     
...     class Meta:
...         db_connection = 'django_test_db_b'

>>> class QB(models.Model):
...     name = models.CharField(maxlength=20)
...     a = models.ForeignKey(QA)
...     
...     def __str__(self):
...         return self.name
...     
...     class Meta:
...         db_connection = 'django_test_db_b'

# many-many
>>> class QC(models.Model):
...     name = models.CharField(maxlength=20)
...     
...     def __str__(self):
...         return self.name
...     
...     class Meta:
...         db_connection = 'django_test_db_b'

>>> class QD(models.Model):
...     name = models.CharField(maxlength=20)
...     qcs = models.ManyToManyField(QC)
...     
...     def __str__(self):
...         return self.name
...     
...     class Meta:
...         db_connection = 'django_test_db_b'

# Using the manager, models can be installed individually, whether they
# use the default connection or a named connection.

>>> DA.objects.install()
{}
>>> QA.objects.install()
{}
>>> QB.objects.install()
{}
>>> DA.objects.all()
[]
>>> list(QA.objects.all())
[]
>>> list(QB.objects.all())
[]
>>> QA(name="something").save()
>>> QA.objects.all()
[<QA: something>]

# The `install()` method returns a tuple, the first element of which is a
# list of statements that were executed, and the second, pending
# statements that could not be executed because (for instance) they are
# meant to establish foreign key relationships to tables that don't
# exist. These are bound to the model's connection and should
# be executed after all models in the app have been installed. The pending
# statments are returned as a dict keyed by the model which must be installed
# before the pending statements can be installed.

# NOTE: pretend db supports constraints for this test
>>> real_cnst = PA._meta.connection_info.backend.supports_constraints
>>> PA._meta.connection_info.backend.supports_constraints = True
>>> result = PA.objects.install()
>>> result
{<class 'othertests.manager_schema_manipulation.PC'>: [BoundStatement('ALTER TABLE "othertests_pa" ADD CONSTRAINT "c_id_referencing_othertests_pc_id" FOREIGN KEY ("c_id") REFERENCES "othertests_pc" ("id");')]}

# NOTE: restore real constraint flag
>>> PA._meta.connection_info.backend.supports_constraints = real_cnst

# Models with many-many relationships may also have pending statement
# lists. Like other pending statements, these should be executed after
# all models in the app have been installed. If the related table's model
# has already been created, then there will be no pending list.

>>> QC.objects.install()
{}
>>> QD.objects.install()
{}

"""
