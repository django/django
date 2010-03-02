"""

"""
from django.contrib import admin

import models

class WidgetAdmin(admin.AdminSite):
    pass

class CarAdmin(admin.ModelAdmin):
    list_display = ['make', 'model', 'owner']
    list_editable = ['owner']

class CarTireAdmin(admin.ModelAdmin):
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "car":
            kwargs["queryset"] = models.Car.objects.filter(owner=request.user)
            return db_field.formfield(**kwargs)
        return super(CarTireAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)

class EventAdmin(admin.ModelAdmin):
    raw_id_fields = ['band']

site = WidgetAdmin(name='widget-admin')

site.register(models.User)
site.register(models.Car, CarAdmin)
site.register(models.CarTire, CarTireAdmin)
site.register(models.Event, EventAdmin)
