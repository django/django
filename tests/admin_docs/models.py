"""
Models for testing various aspects of the djang.contrib.admindocs app
"""

from django.db import models


class Company(models.Model):
    name = models.CharField(max_length=200)


class Group(models.Model):
    name = models.CharField(max_length=200)


class Family(models.Model):
    last_name = models.CharField(max_length=200)


class Person(models.Model):
    first_name = models.CharField(max_length=200, help_text="The person's first name")
    last_name = models.CharField(max_length=200, help_text="The person's last name")
    company = models.ForeignKey(Company, help_text="place of work")
    family = models.ForeignKey(Family, related_name='+', null=True)
    groups = models.ManyToManyField(Group, help_text="has membership")

    def _get_full_name(self):
        return "%s %s" % (self.first_name, self.last_name)

    def add_image(self):
        pass

    def delete_image(self):
        pass

    def save_changes(self):
        pass

    def set_status(self):
        pass

    def get_full_name(self):
        """
        Get the full name of the person
        """
        return self._get_full_name()

    def get_status_count(self):
        return 0

    def get_groups_list(self):
        return []
