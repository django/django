from django.core import meta
from django.models import auth, core

class LogEntry(meta.Model):
    action_time = meta.DateTimeField(auto_now=True)
    user = meta.ForeignKey(auth.User)
    content_type = meta.ForeignKey(core.ContentType, blank=True, null=True)
    object_id = meta.TextField(blank=True, null=True)
    object_repr = meta.CharField(maxlength=200)
    action_flag = meta.PositiveSmallIntegerField()
    change_message = meta.TextField(blank=True)
    class META:
        module_name = 'log'
        verbose_name_plural = 'log entries'
        db_table = 'django_admin_log'
        ordering = ('-action_time',)
        module_constants = {
            'ADDITION': 1,
            'CHANGE': 2,
            'DELETION': 3,
        }

    def __repr__(self):
        return str(self.action_time)

    def is_addition(self):
        return self.action_flag == ADDITION

    def is_change(self):
        return self.action_flag == CHANGE

    def is_deletion(self):
        return self.action_flag == DELETION

    def get_edited_object(self):
        "Returns the edited object represented by this log entry"
        return self.get_content_type().get_object_for_this_type(pk=self.object_id)

    def get_admin_url(self):
        """
        Returns the admin URL to edit the object represented by this log entry.
        This is relative to the Django admin index page.
        """
        return "%s/%s/%s/" % (self.get_content_type().package, self.get_content_type().python_module_name, self.object_id)

    def _module_log_action(user_id, content_type_id, object_id, object_repr, action_flag, change_message=''):
        e = LogEntry(None, None, user_id, content_type_id, object_id, object_repr[:200], action_flag, change_message)
        e.save()
