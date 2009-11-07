from django.contrib import admin
from django.contrib.comments.models import Comment
from django.utils.translation import ugettext_lazy as _, ungettext
from django.contrib.comments import get_model
from django.contrib.comments.views.moderation import perform_flag, perform_approve, perform_delete

class CommentsAdmin(admin.ModelAdmin):
    fieldsets = (
        (None,
           {'fields': ('content_type', 'object_pk', 'site')}
        ),
        (_('Content'),
           {'fields': ('user', 'user_name', 'user_email', 'user_url', 'comment')}
        ),
        (_('Metadata'),
           {'fields': ('submit_date', 'ip_address', 'is_public', 'is_removed')}
        ),
     )

    list_display = ('name', 'content_type', 'object_pk', 'ip_address', 'submit_date', 'is_public', 'is_removed')
    list_filter = ('submit_date', 'site', 'is_public', 'is_removed')
    date_hierarchy = 'submit_date'
    ordering = ('-submit_date',)
    raw_id_fields = ('user',)
    search_fields = ('comment', 'user__username', 'user_name', 'user_email', 'user_url', 'ip_address')
    actions = ["flag_comments", "approve_comments", "remove_comments"]

    def get_actions(self, request):
        actions = super(CommentsAdmin, self).get_actions(request)
        # Only superusers should be able to delete the comments from the DB.
        if not request.user.is_superuser:
            actions.pop('delete_selected')
        if not request.user.has_perm('comments.can_moderate'):
            actions.pop('approve_comments')
            actions.pop('remove_comments')
        return actions

    def flag_comments(self, request, queryset):
        self._bulk_flag(request, queryset, perform_flag, _("flagged"))
    flag_comments.short_description = _("Flag selected comments")

    def approve_comments(self, request, queryset):
        self._bulk_flag(request, queryset, perform_approve, _('approved'))
    approve_comments.short_description = _("Approve selected comments")

    def remove_comments(self, request, queryset):
        self._bulk_flag(request, queryset, perform_delete, _('removed'))
    remove_comments.short_description = _("Remove selected comments")

    def _bulk_flag(self, request, queryset, action, description):
        """
        Flag, approve, or remove some comments from an admin action. Actually
        calls the `action` argument to perform the heavy lifting.
        """
        n_comments = 0
        for comment in queryset:
            action(request, comment)
            n_comments += 1
        
        msg = ungettext(u'1 comment was successfully %(action)s.',
                        u'%(count)s comments were successfully %(action)s.',
                        n_comments)
        self.message_user(request, msg % {'count': n_comments, 'action': description})

# Only register the default admin if the model is the built-in comment model
# (this won't be true if there's a custom comment app).
if get_model() is Comment:
    admin.site.register(Comment, CommentsAdmin)
