from __future__ import unicode_literals

from django.contrib import admin

from .models import Pizza, Topping

site = admin.AdminSite(name='admin')


class PizzaAdmin(admin.ModelAdmin):
    filter_horizontal = ('toppings',)

site.register(Pizza, PizzaAdmin)

site.register(Topping)
