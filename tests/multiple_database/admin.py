from django.contrib import admin

from .models import Book

site = admin.AdminSite(name="admin_multiple_database")
site.register(Book)
