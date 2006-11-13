from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.conf import settings
import datetime

MIN_PHOTO_DIMENSION = 5
MAX_PHOTO_DIMENSION = 1000

# option codes for comment-form hidden fields
PHOTOS_REQUIRED = 'pr'
PHOTOS_OPTIONAL = 'pa'
RATINGS_REQUIRED = 'rr'
RATINGS_OPTIONAL = 'ra'
IS_PUBLIC = 'ip'

# what users get if they don't have any karma
DEFAULT_KARMA = 5
KARMA_NEEDED_BEFORE_DISPLAYED = 3

class CommentManager(models.Manager):
    def get_security_hash(self, options, photo_options, rating_options, target):
        """
        Returns the MD5 hash of the given options (a comma-separated string such as
        'pa,ra') and target (something like 'lcom.eventtimes:5157'). Used to
        validate that submitted form options have not been tampered-with.
        """
        import md5
        return md5.new(options + photo_options + rating_options + target + settings.SECRET_KEY).hexdigest()

    def get_rating_options(self, rating_string):
        """
        Given a rating_string, this returns a tuple of (rating_range, options).
        >>> s = "scale:1-10|First_category|Second_category"
        >>> Comment.objects.get_rating_options(s)
        ([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], ['First category', 'Second category'])
        """
        rating_range, options = rating_string.split('|', 1)
        rating_range = range(int(rating_range[6:].split('-')[0]), int(rating_range[6:].split('-')[1])+1)
        choices = [c.replace('_', ' ') for c in options.split('|')]
        return rating_range, choices

    def get_list_with_karma(self, **kwargs):
        """
        Returns a list of Comment objects matching the given lookup terms, with
        _karma_total_good and _karma_total_bad filled.
        """
        extra_kwargs = {}
        extra_kwargs.setdefault('select', {})
        extra_kwargs['select']['_karma_total_good'] = 'SELECT COUNT(*) FROM comments_karmascore, comments_comment WHERE comments_karmascore.comment_id=comments_comment.id AND score=1'
        extra_kwargs['select']['_karma_total_bad'] = 'SELECT COUNT(*) FROM comments_karmascore, comments_comment WHERE comments_karmascore.comment_id=comments_comment.id AND score=-1'
        return self.filter(**kwargs).extra(**extra_kwargs)

    def user_is_moderator(self, user):
        if user.is_superuser:
            return True
        for g in user.groups.all():
            if g.id == settings.COMMENTS_MODERATORS_GROUP:
                return True
        return False

class Comment(models.Model):
    user = models.ForeignKey(User, raw_id_admin=True)
    content_type = models.ForeignKey(ContentType)
    object_id = models.IntegerField(_('object ID'))
    headline = models.CharField(_('headline'), maxlength=255, blank=True)
    comment = models.TextField(_('comment'), maxlength=3000)
    rating1 = models.PositiveSmallIntegerField(_('rating #1'), blank=True, null=True)
    rating2 = models.PositiveSmallIntegerField(_('rating #2'), blank=True, null=True)
    rating3 = models.PositiveSmallIntegerField(_('rating #3'), blank=True, null=True)
    rating4 = models.PositiveSmallIntegerField(_('rating #4'), blank=True, null=True)
    rating5 = models.PositiveSmallIntegerField(_('rating #5'), blank=True, null=True)
    rating6 = models.PositiveSmallIntegerField(_('rating #6'), blank=True, null=True)
    rating7 = models.PositiveSmallIntegerField(_('rating #7'), blank=True, null=True)
    rating8 = models.PositiveSmallIntegerField(_('rating #8'), blank=True, null=True)
    # This field designates whether to use this row's ratings in aggregate
    # functions (summaries). We need this because people are allowed to post
    # multiple reviews on the same thing, but the system will only use the
    # latest one (with valid_rating=True) in tallying the reviews.
    valid_rating = models.BooleanField(_('is valid rating'))
    submit_date = models.DateTimeField(_('date/time submitted'), auto_now_add=True)
    is_public = models.BooleanField(_('is public'))
    ip_address = models.IPAddressField(_('IP address'), blank=True, null=True)
    is_removed = models.BooleanField(_('is removed'), help_text=_('Check this box if the comment is inappropriate. A "This comment has been removed" message will be displayed instead.'))
    site = models.ForeignKey(Site)
    objects = CommentManager()
    class Meta:
        verbose_name = _('comment')
        verbose_name_plural = _('comments')
        ordering = ('-submit_date',)
    class Admin:
        fields = (
            (None, {'fields': ('content_type', 'object_id', 'site')}),
            ('Content', {'fields': ('user', 'headline', 'comment')}),
            ('Ratings', {'fields': ('rating1', 'rating2', 'rating3', 'rating4', 'rating5', 'rating6', 'rating7', 'rating8', 'valid_rating')}),
            ('Meta', {'fields': ('is_public', 'is_removed', 'ip_address')}),
        )
        list_display = ('user', 'submit_date', 'content_type', 'get_content_object')
        list_filter = ('submit_date',)
        date_hierarchy = 'submit_date'
        search_fields = ('comment', 'user__username')

    def __repr__(self):
        return "%s: %s..." % (self.user.username, self.comment[:100])

    def get_absolute_url(self):
        return self.get_content_object().get_absolute_url() + "#c" + str(self.id)

    def get_crossdomain_url(self):
        return "/r/%d/%d/" % (self.content_type_id, self.object_id)

    def get_flag_url(self):
        return "/comments/flag/%s/" % self.id

    def get_deletion_url(self):
        return "/comments/delete/%s/" % self.id

    def get_content_object(self):
        """
        Returns the object that this comment is a comment on. Returns None if
        the object no longer exists.
        """
        from django.core.exceptions import ObjectDoesNotExist
        try:
            return self.content_type.get_object_for_this_type(pk=self.object_id)
        except ObjectDoesNotExist:
            return None

    get_content_object.short_description = _('Content object')

    def _fill_karma_cache(self):
        "Helper function that populates good/bad karma caches"
        good, bad = 0, 0
        for k in self.karmascore_set:
            if k.score == -1:
                bad +=1
            elif k.score == 1:
                good +=1
        self._karma_total_good, self._karma_total_bad = good, bad

    def get_good_karma_total(self):
        if not hasattr(self, "_karma_total_good"):
            self._fill_karma_cache()
        return self._karma_total_good

    def get_bad_karma_total(self):
        if not hasattr(self, "_karma_total_bad"):
            self._fill_karma_cache()
        return self._karma_total_bad

    def get_karma_total(self):
        if not hasattr(self, "_karma_total_good") or not hasattr(self, "_karma_total_bad"):
            self._fill_karma_cache()
        return self._karma_total_good + self._karma_total_bad

    def get_as_text(self):
        return _('Posted by %(user)s at %(date)s\n\n%(comment)s\n\nhttp://%(domain)s%(url)s') % \
            {'user': self.user.username, 'date': self.submit_date,
            'comment': self.comment, 'domain': self.site.domain, 'url': self.get_absolute_url()}

class FreeComment(models.Model):
    # A FreeComment is a comment by a non-registered user.
    content_type = models.ForeignKey(ContentType)
    object_id = models.IntegerField(_('object ID'))
    comment = models.TextField(_('comment'), maxlength=3000)
    person_name = models.CharField(_("person's name"), maxlength=50)
    submit_date = models.DateTimeField(_('date/time submitted'), auto_now_add=True)
    is_public = models.BooleanField(_('is public'))
    ip_address = models.IPAddressField(_('ip address'))
    # TODO: Change this to is_removed, like Comment
    approved = models.BooleanField(_('approved by staff'))
    site = models.ForeignKey(Site)
    class Meta:
        verbose_name = _('free comment')
        verbose_name_plural = _('free comments')
        ordering = ('-submit_date',)
    class Admin:
        fields = (
            (None, {'fields': ('content_type', 'object_id', 'site')}),
            ('Content', {'fields': ('person_name', 'comment')}),
            ('Meta', {'fields': ('submit_date', 'is_public', 'ip_address', 'approved')}),
        )
        list_display = ('person_name', 'submit_date', 'content_type', 'get_content_object')
        list_filter = ('submit_date',)
        date_hierarchy = 'submit_date'
        search_fields = ('comment', 'person_name')

    def __repr__(self):
        return "%s: %s..." % (self.person_name, self.comment[:100])

    def get_absolute_url(self):
        return self.get_content_object().get_absolute_url() + "#c" + str(self.id)

    def get_content_object(self):
        """
        Returns the object that this comment is a comment on. Returns None if
        the object no longer exists.
        """
        from django.core.exceptions import ObjectDoesNotExist
        try:
            return self.content_type.get_object_for_this_type(pk=self.object_id)
        except ObjectDoesNotExist:
            return None

    get_content_object.short_description = _('Content object')

class KarmaScoreManager(models.Manager):
    def vote(self, user_id, comment_id, score):
        try:
            karma = self.objects.get(comment__pk=comment_id, user__pk=user_id)
        except self.model.DoesNotExist:
            karma = self.model(None, user_id=user_id, comment_id=comment_id, score=score, scored_date=datetime.datetime.now())
            karma.save()
        else:
            karma.score = score
            karma.scored_date = datetime.datetime.now()
            karma.save()

    def get_pretty_score(self, score):
        """
        Given a score between -1 and 1 (inclusive), returns the same score on a
        scale between 1 and 10 (inclusive), as an integer.
        """
        if score is None:
            return DEFAULT_KARMA
        return int(round((4.5 * score) + 5.5))

class KarmaScore(models.Model):
    user = models.ForeignKey(User)
    comment = models.ForeignKey(Comment)
    score = models.SmallIntegerField(_('score'), db_index=True)
    scored_date = models.DateTimeField(_('score date'), auto_now=True)
    objects = KarmaScoreManager()
    class Meta:
        verbose_name = _('karma score')
        verbose_name_plural = _('karma scores')
        unique_together = (('user', 'comment'),)

    def __repr__(self):
        return _("%(score)d rating by %(user)s") % {'score': self.score, 'user': self.user}

class UserFlagManager(models.Manager):
    def flag(self, comment, user):
        """
        Flags the given comment by the given user. If the comment has already
        been flagged by the user, or it was a comment posted by the user,
        nothing happens.
        """
        if int(comment.user_id) == int(user.id):
            return # A user can't flag his own comment. Fail silently.
        try:
            f = self.objects.get(user__pk=user.id, comment__pk=comment.id)
        except self.model.DoesNotExist:
            from django.core.mail import mail_managers
            f = self.model(None, user.id, comment.id, None)
            message = _('This comment was flagged by %(user)s:\n\n%(text)s') % {'user': user.username, 'text': comment.get_as_text()}
            mail_managers('Comment flagged', message, fail_silently=True)
            f.save()

class UserFlag(models.Model):
    user = models.ForeignKey(User)
    comment = models.ForeignKey(Comment)
    flag_date = models.DateTimeField(_('flag date'), auto_now_add=True)
    objects = UserFlagManager()
    class Meta:
        verbose_name = _('user flag')
        verbose_name_plural = _('user flags')
        unique_together = (('user', 'comment'),)

    def __repr__(self):
        return _("Flag by %r") % self.user

class ModeratorDeletion(models.Model):
    user = models.ForeignKey(User, verbose_name='moderator')
    comment = models.ForeignKey(Comment)
    deletion_date = models.DateTimeField(_('deletion date'), auto_now_add=True)
    class Meta:
        verbose_name = _('moderator deletion')
        verbose_name_plural = _('moderator deletions')
        unique_together = (('user', 'comment'),)

    def __repr__(self):
        return _("Moderator deletion by %r") % self.user
