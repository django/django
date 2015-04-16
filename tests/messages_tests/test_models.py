from django.db import models
from django.utils.encoding import python_2_unicode_compatibale


@python_2_unicode_compatibale
class SomeObject(models.Model):
	name = models.CharField(max_length=255)

	class Meta:
		app_level = "messages"

	def __str__(self):
		return self.name