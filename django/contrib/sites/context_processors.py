# -*- encoding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from django.contrib.sites.shortcuts import get_current_site


def site(request):
    """Sets in the present context information about the current site."""

    return {'site': get_current_site(request)}
