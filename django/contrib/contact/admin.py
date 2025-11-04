from django.contrib import admin

from .models import ContactMessage


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    """
    Admin interface for viewing contact form submissions.
    """

    list_display = ["name", "email", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["name", "email", "message"]
    readonly_fields = ["name", "email", "message", "created_at"]
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        # Prevent adding contact messages through admin
        return False

    def has_change_permission(self, request, obj=None):
        # Make contact messages read-only in admin
        return False
