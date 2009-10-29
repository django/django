from django.db import models
from datetime import datetime

def expensive_calculation():
    expensive_calculation.num_runs += 1
    return datetime.now()

class Poll(models.Model):
    question = models.CharField(max_length=200)
    answer = models.CharField(max_length=200)
    pub_date = models.DateTimeField('date published', default=expensive_calculation)
