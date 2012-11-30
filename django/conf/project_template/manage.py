#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Administrative command-line utility for {{ project_name|title }} Django project.

.. seealso::
    http://docs.djangoproject.com/en/dev/ref/django-admin/
"""
import os
import sys

if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', '{{ project_name }}.settings')

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
