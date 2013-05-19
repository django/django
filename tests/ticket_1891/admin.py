from django.contrib import admin

# Register your models here.
from django.contrib import admin
from models import Group, Asset, Proxy

admin.site.register(Group)
admin.site.register(Asset)
admin.site.register(Proxy)
