from django.contrib import admin
from django.contrib.comments.models import Comment, FreeComment


class CommentAdmin(admin.ModelAdmin):
    fieldsets = (
        (None, {'fields': ('content_type', 'object_id', 'site')}),
        ('Content', {'fields': ('user', 'headline', 'comment')}),
        ('Ratings', {'fields': ('rating1', 'rating2', 'rating3', 'rating4', 'rating5', 'rating6', 'rating7', 'rating8', 'valid_rating')}),
        ('Meta', {'fields': ('is_public', 'is_removed', 'ip_address')}),
    )
    list_display = ('user', 'submit_date', 'content_type', 'get_content_object')
    list_filter = ('submit_date',)
    date_hierarchy = 'submit_date'
    search_fields = ('comment', 'user__username')
    raw_id_fields = ('user',)

class FreeCommentAdmin(admin.ModelAdmin):
    fieldsets = (
        (None, {'fields': ('content_type', 'object_id', 'site')}),
        ('Content', {'fields': ('person_name', 'comment')}),
        ('Meta', {'fields': ('is_public', 'ip_address', 'approved')}),
    )
    list_display = ('person_name', 'submit_date', 'content_type', 'get_content_object')
    list_filter = ('submit_date',)
    date_hierarchy = 'submit_date'
    search_fields = ('comment', 'person_name')

admin.site.register(Comment, CommentAdmin)
admin.site.register(FreeComment, FreeCommentAdmin)