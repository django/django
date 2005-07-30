from django.core import meta
from django.models import auth, core

class Comment(meta.Model):
    db_table = 'comments'
    fields = (
        meta.ForeignKey(auth.User, raw_id_admin=True),
        meta.ForeignKey(core.ContentType, name='content_type_id', rel_name='content_type'),
        meta.IntegerField('object_id', 'object ID'),
        meta.CharField('headline', 'headline', maxlength=255, blank=True),
        meta.TextField('comment', 'comment', maxlength=3000),
        meta.PositiveSmallIntegerField('rating1', 'rating #1', blank=True, null=True),
        meta.PositiveSmallIntegerField('rating2', 'rating #2', blank=True, null=True),
        meta.PositiveSmallIntegerField('rating3', 'rating #3', blank=True, null=True),
        meta.PositiveSmallIntegerField('rating4', 'rating #4', blank=True, null=True),
        meta.PositiveSmallIntegerField('rating5', 'rating #5', blank=True, null=True),
        meta.PositiveSmallIntegerField('rating6', 'rating #6', blank=True, null=True),
        meta.PositiveSmallIntegerField('rating7', 'rating #7', blank=True, null=True),
        meta.PositiveSmallIntegerField('rating8', 'rating #8', blank=True, null=True),
        # This field designates whether to use this row's ratings in
        # aggregate functions (summaries). We need this because people are
        # allowed to post multiple review on the same thing, but the system
        # will only use the latest one (with valid_rating=True) in tallying
        # the reviews.
        meta.BooleanField('valid_rating', 'is valid rating'),
        meta.DateTimeField('submit_date', 'date/time submitted', auto_now_add=True),
        meta.BooleanField('is_public', 'is public'),
        meta.IPAddressField('ip_address', 'IP address', blank=True, null=True),
        meta.BooleanField('is_removed', 'is removed',
            help_text='Check this box if the comment is inappropriate. A "This comment has been removed" message will be displayed instead.'),
        meta.ForeignKey(core.Site),
    )
    module_constants = {
        # min. and max. allowed dimensions for photo resizing (in pixels)
        'MIN_PHOTO_DIMENSION': 5,
        'MAX_PHOTO_DIMENSION': 1000,

        # option codes for comment-form hidden fields
        'PHOTOS_REQUIRED': 'pr',
        'PHOTOS_OPTIONAL': 'pa',
        'RATINGS_REQUIRED': 'rr',
        'RATINGS_OPTIONAL': 'ra',
        'IS_PUBLIC': 'ip',
    }
    ordering = ('-submit_date',)
    admin = meta.Admin(
        fields = (
            (None, {'fields': ('content_type_id', 'object_id', 'site_id')}),
            ('Content', {'fields': ('user_id', 'headline', 'comment')}),
            ('Ratings', {'fields': ('rating1', 'rating2', 'rating3', 'rating4', 'rating5', 'rating6', 'rating7', 'rating8', 'valid_rating')}),
            ('Meta', {'fields': ('is_public', 'is_removed', 'ip_address')}),
        ),
        list_display = ('user_id', 'submit_date', 'content_type_id', 'get_content_object'),
        list_filter = ('submit_date',),
        date_hierarchy = 'submit_date',
        search_fields = ('comment', 'user__username'),
    )

    def __repr__(self):
        return "%s: %s..." % (self.get_user().username, self.comment[:100])

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
            return self.get_content_type().get_object_for_this_type(pk=self.object_id)
        except ObjectDoesNotExist:
            return None

    get_content_object.short_description = 'Content object'

    def _fill_karma_cache(self):
        "Helper function that populates good/bad karma caches"
        good, bad = 0, 0
        for k in self.get_karmascore_list():
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
        return 'Posted by %s at %s\n\n%s\n\nhttp://%s%s' % \
            (self.get_user().username, self.submit_date,
            self.comment, self.get_site().domain, self.get_absolute_url())

    def _module_get_security_hash(options, photo_options, rating_options, target):
        """
        Returns the MD5 hash of the given options (a comma-separated string such as
        'pa,ra') and target (something like 'lcom.eventtimes:5157'). Used to
        validate that submitted form options have not been tampered-with.
        """
        from django.conf.settings import SECRET_KEY
        import md5
        return md5.new(options + photo_options + rating_options + target + SECRET_KEY).hexdigest()

    def _module_get_rating_options(rating_string):
        """
        Given a rating_string, this returns a tuple of (rating_range, options).
        >>> s = "scale:1-10|First_category|Second_category"
        >>> get_rating_options(s)
        ([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], ['First category', 'Second category'])
        """
        rating_range, options = rating_string.split('|', 1)
        rating_range = range(int(rating_range[6:].split('-')[0]), int(rating_range[6:].split('-')[1])+1)
        choices = [c.replace('_', ' ') for c in options.split('|')]
        return rating_range, choices

    def _module_get_list_with_karma(**kwargs):
        """
        Returns a list of Comment objects matching the given lookup terms, with
        _karma_total_good and _karma_total_bad filled.
        """
        kwargs.setdefault('select', {})
        kwargs['select']['_karma_total_good'] = 'SELECT COUNT(*) FROM comments_karma WHERE comments_karma.comment_id=comments.id AND score=1'
        kwargs['select']['_karma_total_bad'] = 'SELECT COUNT(*) FROM comments_karma WHERE comments_karma.comment_id=comments.id AND score=-1'
        return get_list(**kwargs)

    def _module_user_is_moderator(user):
        from django.conf.settings import COMMENTS_MODERATORS_GROUP
        if user.is_superuser:
            return True
        for g in user.get_group_list():
            if g.id == COMMENTS_MODERATORS_GROUP:
                return True
        return False

class FreeComment(meta.Model):
    "A FreeComment is a comment by a non-registered user"
    db_table = 'comments_free'
    fields = (
        meta.ForeignKey(core.ContentType, name='content_type_id', rel_name='content_type'),
        meta.IntegerField('object_id', 'object ID'),
        meta.TextField('comment', 'comment', maxlength=3000),
        meta.CharField('person_name', "person's name", maxlength=50),
        meta.DateTimeField('submit_date', 'date/time submitted', auto_now_add=True),
        meta.BooleanField('is_public', 'is public'),
        meta.IPAddressField('ip_address', 'IP address'),
        # TODO: Change this to is_removed, like Comment
        meta.BooleanField('approved', 'approved by staff'),
        meta.ForeignKey(core.Site),
    )
    ordering = ('-submit_date',)
    admin = meta.Admin(
        fields = (
            (None, {'fields': ('content_type_id', 'object_id', 'site_id')}),
            ('Content', {'fields': ('person_name', 'comment')}),
            ('Meta', {'fields': ('submit_date', 'is_public', 'ip_address', 'approved')}),
        ),
        list_display = ('person_name', 'submit_date', 'content_type_id', 'get_content_object'),
        list_filter = ('submit_date',),
        date_hierarchy = 'submit_date',
        search_fields = ('comment', 'person_name'),
    )

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
            return self.get_content_type().get_object_for_this_type(pk=self.object_id)
        except ObjectDoesNotExist:
            return None

    get_content_object.short_description = 'Content object'

class KarmaScore(meta.Model):
    module_name = 'karma'
    fields = (
        meta.ForeignKey(auth.User),
        meta.ForeignKey(Comment),
        meta.SmallIntegerField('score', 'score', db_index=True),
        meta.DateTimeField('scored_date', 'date scored', auto_now=True),
    )
    unique_together = (('user_id', 'comment_id'),)
    module_constants = {
        # what users get if they don't have any karma
        'DEFAULT_KARMA': 5,
        'KARMA_NEEDED_BEFORE_DISPLAYED': 3,
    }

    def __repr__(self):
        return "%d rating by %s" % (self.score, self.get_user())

    def _module_vote(user_id, comment_id, score):
        try:
            karma = get_object(comment_id__exact=comment_id, user_id__exact=user_id)
        except KarmaScoreDoesNotExist:
            karma = KarmaScore(None, user_id, comment_id, score, datetime.datetime.now())
            karma.save()
        else:
            karma.score = score
            karma.scored_date = datetime.datetime.now()
            karma.save()

    def _module_get_pretty_score(score):
        """
        Given a score between -1 and 1 (inclusive), returns the same score on a
        scale between 1 and 10 (inclusive), as an integer.
        """
        if score is None:
            return DEFAULT_KARMA
        return int(round((4.5 * score) + 5.5))

class UserFlag(meta.Model):
    db_table = 'comments_user_flags'
    fields = (
        meta.ForeignKey(auth.User),
        meta.ForeignKey(Comment),
        meta.DateTimeField('flag_date', 'date flagged', auto_now_add=True),
    )
    unique_together = (('user_id', 'comment_id'),)

    def __repr__(self):
        return "Flag by %r" % self.get_user()

    def _module_flag(comment, user):
        """
        Flags the given comment by the given user. If the comment has already
        been flagged by the user, or it was a comment posted by the user,
        nothing happens.
        """
        if int(comment.user_id) == int(user.id):
            return # A user can't flag his own comment. Fail silently.
        try:
            f = get_object(user_id__exact=user.id, comment_id__exact=comment.id)
        except UserFlagDoesNotExist:
            from django.core.mail import mail_managers
            f = UserFlag(None, user.id, comment.id, None)
            message = 'This comment was flagged by %s:\n\n%s' % (user.username, comment.get_as_text())
            mail_managers('Comment flagged', message, fail_silently=True)
            f.save()

class ModeratorDeletion(meta.Model):
    db_table = 'comments_moderator_deletions'
    fields = (
        meta.ForeignKey(auth.User, verbose_name='moderator'),
        meta.ForeignKey(Comment),
        meta.DateTimeField('deletion_date', 'date deleted', auto_now_add=True),
    )
    unique_together = (('user_id', 'comment_id'),)

    def __repr__(self):
        return "Moderator deletion by %r" % self.get_user()
