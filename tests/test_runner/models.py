from django.db import models


class Person(models.Model):
    first_name = models.CharField(max_length=20)
    last_name = models.CharField(max_length=20)
    friends = models.ManyToManyField("self")

    system_check_run_count = 0

    @classmethod
    def check(cls, *args, **kwargs):
        cls.system_check_run_count += 1
        return super().check(**kwargs)


# A set of models that use a non-abstract inherited 'through' model.
class ThroughBase(models.Model):
    person = models.ForeignKey(Person, models.CASCADE)
    b = models.ForeignKey("B", models.CASCADE)


class Through(ThroughBase):
    extra = models.CharField(max_length=20)


class B(models.Model):
    people = models.ManyToManyField(Person, through=Through)
