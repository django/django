# -*- coding: utf-8 -*-
"""
Views for {{ app_name|title }} Django application.

.. seealso::
    http://docs.djangoproject.com/en/dev/ref/class-based-views/
"""
from django.shortcuts import get_object_or_404, get_list_or_404
from django.views.generic import TemplateView

from {{ app_name }} import models


# Replace the following example with your views.

class HomeView(TemplateView):
    """View for `home` page."""

    template_name = '{{ app_name }}/home.html'

    def get_context_data(self, **kwargs):
        context = super(HomeView, self).get_context_data(**kwargs)
        context['{{ app_name }}'] = get_object_or_404(models.{{ app_name|title }}, name='home')
        return context

