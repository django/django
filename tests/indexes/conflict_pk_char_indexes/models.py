"""
Index name conflict when the primary key is a CharField and db_table is specified (postgresql).
Refs: #19750
"""
from django.db import models


class OrganizationType(models.Model):
    id = models.CharField(max_length=1, primary_key=True)

    class Meta:
        db_table = 'organization_type'


class Organization(models.Model):
    type = models.ForeignKey(OrganizationType)

    class Meta:
        db_table = 'organization'
