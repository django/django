from django.db import models


class Classification(models.Model):
    code = models.CharField(max_length=10)


class Employee(models.Model):
    name = models.CharField(max_length=40, blank=False, null=False)
    salary = models.PositiveIntegerField()
    department = models.CharField(max_length=40, blank=False, null=False)
    hire_date = models.DateField(blank=False, null=False)
    age = models.IntegerField(blank=False, null=False)
    classification = models.ForeignKey('Classification', on_delete=models.CASCADE, null=True)
    bonus = models.DecimalField(decimal_places=2, max_digits=15, null=True)


class Detail(models.Model):
    value = models.JSONField()

    class Meta:
        required_db_features = {'supports_json_field'}
