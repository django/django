from __future__ import unicode_literals

from django.db import models
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.admin.utils import quote
from django.core.urlresolvers import reverse, NoReverseMatch
from django.utils.translation import ugettext, ugettext_lazy as _
from django.utils.text import get_text_list
from django.utils.encoding import smart_text
from django.utils.encoding import python_2_unicode_compatible
import re

ADDITION = 1
CHANGE = 2
DELETION = 3


class LogEntryManager(models.Manager):
    use_in_migrations = True

    def log_action(self, user_id, content_type_id, object_id, object_repr, action_flag, change_message=''):
        e = self.model(
            None, None, user_id, content_type_id, smart_text(object_id),
            object_repr[:200], action_flag, change_message
        )
        e.save()


@python_2_unicode_compatible
class LogEntry(models.Model):
    action_time = models.DateTimeField(_('action time'), auto_now=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL)
    content_type = models.ForeignKey(ContentType, blank=True, null=True)
    object_id = models.TextField(_('object id'), blank=True, null=True)
    object_repr = models.CharField(_('object repr'), max_length=200)
    action_flag = models.PositiveSmallIntegerField(_('action flag'))
    change_message = models.TextField(_('change message'), blank=True)

    objects = LogEntryManager()

    class Meta:
        verbose_name = _('log entry')
        verbose_name_plural = _('log entries')
        db_table = 'django_admin_log'
        ordering = ('-action_time',)

    def __repr__(self):
        return smart_text(self.action_time)

    def __str__(self):
        if self.action_flag == ADDITION:
            return ugettext('Added "%(object)s".') % {'object': self.object_repr}
        elif self.action_flag == CHANGE:
            return ugettext('Changed "%(object)s" - %(changes)s') % {
                'object': self.object_repr,
                'changes': self.change_message,
            }
        elif self.action_flag == DELETION:
            return ugettext('Deleted "%(object)s."') % {'object': self.object_repr}

        return ugettext('LogEntry Object')

    def get_change_message(self):

        obj = self.get_edited_object()

        # helper that format-ifies the argument
        formatify = lambda x: '%(' + x + ')s'
        tokens = []

        # Try to match the sentence to a change thing we can take apart
        if self.change_message == '':
            return self.change_message

        # this only creates a nice message of the form
        #    "Changed last_name, is_staff and is_superuser."
        # and turns it into
        #    "Changed last name, staff status and superuser status.
        # except in the user's chosen language.
        if re.match('Changed ((\w|\s|,|_)+)\.', self.change_message):
            group = re.findall('Changed (.+)\.', self.change_message)[0]
            for token in re.split(', | | and ', group):
                if token != 'and':
                    tokens.append(token)

            format_tokens = map(formatify, tokens)
            format_msg = ugettext('Changed %s.') % get_text_list(format_tokens, _('and'))

            verbose_names = {}
            for token in tokens:
                # in case we don't find a better name
                verbose_names[token] = ugettext(token)

                if token in obj._meta.get_all_field_names():
                    field = obj._meta.get_field_by_name(token)[0]

                    if hasattr(field, 'verbose_name'):
                        if hasattr(field.verbose_name, 'title'):
                            verbose_names[token] = field.verbose_name.title().lower()
                        else:
                            verbose_names[token] = field.verbose_name

            return format_msg % verbose_names
        else:
            return ugettext(self.change_message) 

    def is_addition(self):
        return self.action_flag == ADDITION

    def is_change(self):
        return self.action_flag == CHANGE

    def is_deletion(self):
        return self.action_flag == DELETION

    def get_edited_object(self):
        "Returns the edited object represented by this log entry"
        return self.content_type.get_object_for_this_type(pk=self.object_id)

    def get_admin_url(self):
        """
        Returns the admin URL to edit the object represented by this log entry.
        This is relative to the Django admin index page.
        """
        if self.content_type and self.object_id:
            url_name = 'admin:%s_%s_change' % (self.content_type.app_label, self.content_type.model)
            try:
                return reverse(url_name, args=(quote(self.object_id),))
            except NoReverseMatch:
                pass
        return None
