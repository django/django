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
    """
    Stores information about a person, related to :model:`myapp.Company`.

    **Notes**

    Use ``save_changes()`` when saving this object.

    ``company``
        Field storing :model:`myapp.Company` where the person works.

    (DESCRIPTION)

    .. raw:: html
        :file: admin_docs/evilfile.txt

    .. include:: admin_docs/evilfile.txt
    """
    first_name = models.CharField(max_length=200, help_text="The person's first name")
    last_name = models.CharField(max_length=200, help_text="The person's last name")
    company = models.ForeignKey(Company, models.CASCADE, help_text="place of work")
    family = models.ForeignKey(Family, models.SET_NULL, related_name='+', null=True)
    groups = models.ManyToManyField(Group, help_text="has membership")

    def _get_full_name(self):
        return "%s %s" % (self.first_name, self.last_name)

    def rename_company(self, new_name):
        self.company.name = new_name
        self.company.save()
        return new_name

    def dummy_function(self, baz, rox, *some_args, **some_kwargs):
        return some_kwargs

    def suffix_company_name(self, suffix='ltd'):
        return self.company.name + suffix

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
