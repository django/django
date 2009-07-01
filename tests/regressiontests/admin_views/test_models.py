# -*- coding: utf-8 -*-
import tempfile
import os
from django.core.files.storage import FileSystemStorage
from django.db import models
from django.contrib import admin
from django.core.mail import EmailMessage

class SectionTest(models.Model):
    """
    A simple section that links to articles, to test linking to related items
    in admin views.
    """
    name = models.CharField(max_length=100)

#admin.site.register(SectionTest, save_as=True)