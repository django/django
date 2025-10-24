from django.db import models


class Classroom(models.Model):
    pass


class Lesson(models.Model):
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE)


class VeryLongNameModel(models.Model):
    class Meta:
        db_table = "long_db_table_that_should_be_truncated_before_checking"
