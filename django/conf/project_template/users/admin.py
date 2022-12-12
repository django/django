from django.contrib import admin

from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    """
    Django admin settings for the users app.
    """

    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "is_active",
        "date_joined",
        "is_staff",
        "is_superuser",
    )
    list_filter = (
        "is_active",
        "is_staff",
        "is_superuser",
    )
