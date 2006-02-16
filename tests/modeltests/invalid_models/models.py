"""
26. A test to check that the model validator works can correctly identify errors in a model. 
"""

from django.db import models

class FieldErrors(models.Model):
    charfield = models.CharField()
    floatfield = models.FloatField()
    filefield = models.FileField()
    prepopulate = models.CharField(maxlength=10, prepopulate_from='bad')
    choices = models.CharField(maxlength=10, choices='bad')
    choices2 = models.CharField(maxlength=10, choices=[(1,2,3),(1,2,3)])
    index = models.CharField(maxlength=10, db_index='bad')    


error_log = """invalid_models.fielderrors: "charfield" field: CharFields require a "maxlength" attribute.
invalid_models.fielderrors: "floatfield" field: FloatFields require a "decimal_places" attribute.
invalid_models.fielderrors: "floatfield" field: FloatFields require a "max_digits" attribute.
invalid_models.fielderrors: "filefield" field: FileFields require an "upload_to" attribute.
invalid_models.fielderrors: "prepopulate" field: prepopulate_from should be a list or tuple.
invalid_models.fielderrors: "choices" field: "choices" should be either a tuple or list.
invalid_models.fielderrors: "choices2" field: "choices" should be a sequence of two-tuples.
invalid_models.fielderrors: "choices2" field: "choices" should be a sequence of two-tuples.
invalid_models.fielderrors: "index" field: "db_index" should be either None, True or False.
"""
