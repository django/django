from django.contrib import admin


class CustomAdminSiteWithCustomTemplateEngine(admin.AdminSite):
    template_engine = "custom_template_engine"
