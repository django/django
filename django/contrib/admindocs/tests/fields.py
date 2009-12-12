from django.db import models

class CustomField(models.Field):
    """A custom field type"""
    
class ManyLineDocstringField(models.Field):
    """Many-line custom field
    
    This docstring has many lines.  Lorum ipsem etc. etc.  Four score 
    and seven years ago, and so on and so forth."""

class DocstringLackingField(models.Field):
    pass
