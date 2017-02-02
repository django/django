import json

from django.conf import settings
from django.contrib.admin.utils import quote
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.urls import NoReverseMatch, reverse
from django.utils import timezone
from django.utils.encoding import force_text
from django.utils.text import get_text_list
from django.utils.translation import ugettext, ugettext_lazy as _

ADDITION = 1
CHANGE = 2
DELETION = 3


class LogEntryManager(models.Manager):
    use_in_migrations = True

    def log_action(self, user_id, content_type_id, object_id, object_repr, action_flag, change_message=''):
        if isinstance(change_message, list):
            change_message = json.dumps(change_message)
        return self.model.objects.create(
            user_id=user_id,
            content_type_id=content_type_id,
            object_id=force_text(object_id),
            object_repr=object_repr[:200],
            action_flag=action_flag,
            change_message=change_message,
        )


class LogEntry(models.Model):
    action_time = models.DateTimeField(
        _('action time'),
        default=timezone.now,
        editable=False,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        models.CASCADE,
        verbose_name=_('user'),
    )
    content_type = models.ForeignKey(
        ContentType,
        models.SET_NULL,
        verbose_name=_('content type'),
        blank=True, null=True,
    )
    object_id = models.TextField(_('object id'), blank=True, null=True)
    # Translators: 'repr' means representation (https://docs.python.org/3/library/functions.html#repr)
    object_repr = models.CharField(_('object repr'), max_length=200)
    action_flag = models.PositiveSmallIntegerField(_('action flag'))
    # change_message is either a string or a JSON structure
    change_message = models.TextField(_('change message'), blank=True)

    objects = LogEntryManager()

    class Meta:
        verbose_name = _('log entry')
        verbose_name_plural = _('log entries')
        db_table = 'django_admin_log'
        ordering = ('-action_time',)

    def __repr__(self):
        return force_text(self.action_time)

    def __str__(self):
        if self.is_addition():
            return ugettext('Added "%(object)s".') % {'object': self.object_repr}
        elif self.is_change():
            return ugettext('Changed "%(object)s" - %(changes)s') % {
                'object': self.object_repr,
                'changes': self.get_change_message(),
            }
        elif self.is_deletion():
            return ugettext('Deleted "%(object)s."') % {'object': self.object_repr}

        return ugettext('LogEntry Object')

    def is_addition(self):
        return self.action_flag == ADDITION

    def is_change(self):
        return self.action_flag == CHANGE

    def is_deletion(self):
        return self.action_flag == DELETION

    def get_change_message(self):
        """
        If self.change_message is a JSON structure, interpret it as a change
        string, properly translated.
        """
        if self.change_message and self.change_message[0] == '[':
            try:
                change_message = json.loads(self.change_message)
            except ValueError:
                return self.change_message
            messages = []
            for sub_message in change_message:
                if 'added' in sub_message:
                    if sub_message['added']:
                        sub_message['added']['name'] = ugettext(sub_message['added']['name'])
                        messages.append(ugettext('Added {name} "{object}".').format(**sub_message['added']))
                    else:
                        messages.append(ugettext('Added.'))

                elif 'changed' in sub_message:
                    sub_message['changed']['fields'] = get_text_list(
                        sub_message['changed']['fields'], ugettext('and')
                    )
                    if 'name' in sub_message['changed']:
                        sub_message['changed']['name'] = ugettext(sub_message['changed']['name'])
                        messages.append(ugettext('Changed {fields} for {name} "{object}".').format(
                            **sub_message['changed']
                        ))
                    else:
                        messages.append(ugettext('Changed {fields}.').format(**sub_message['changed']))

                elif 'deleted' in sub_message:
                    sub_message['deleted']['name'] = ugettext(sub_message['deleted']['name'])
                    messages.append(ugettext('Deleted {name} "{object}".').format(**sub_message['deleted']))

            change_message = ' '.join(msg[0].upper() + msg[1:] for msg in messages)
            return change_message or ugettext('No fields changed.')
        else:
            return self.change_message

    def get_edited_object(self):
        "Returns the edited object represented by this log entry"
        return self.content_type.get_object_for_this_type(pk=self.object_id)

    def get_admin_url(self):
        """
        Returns the admin URL to edit the object represented by this log entry.
        """
        if self.content_type and self.object_id:
            url_name = 'admin:%s_%s_change' % (self.content_type.app_label, self.content_type.model)
            try:
                return reverse(url_name, args=(quote(self.object_id),))
            except NoReverseMatch:
                pass
        return None
