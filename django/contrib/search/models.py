from django.db import models

# Note: These aren't used yet, but they probably will be in the future.
# This is because the only thing that really needs to be remembered
# (the path to the index) is going to go in SETTINGS anyway.
# But persistent info such as outdated rows, search statistics, etc.
# could still be useful.

class Index(models.Model):
    model_name = models.CharField(maxlength=255)

class IndexedField(models.Model):
    object_path = models.CharField(maxlength=255)
    model = models.ForeignKey('Index')

class QueryLog(models.Model):
    """This is not a full log, but merely counts queries."""
    query = models.CharField(maxlength=255, unique=True)
    query_count = models.IntegerField(default=1)
    last_date = DateTimeField()
    last_source = models.CharField("Some identifier for who sent the query", maxlength=255)

class Person(models.Model):
    """This is for testing."""
    first_name = models.CharField(maxlength=30)
    last_name = models.CharField(maxlength=30)
    description = models.TextField()