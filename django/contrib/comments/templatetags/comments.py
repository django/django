"Custom template tags for user comments"

from django.core import template
from django.core.exceptions import ObjectDoesNotExist
from django.models.comments import comments, freecomments
from django.models.core import contenttypes
import re

COMMENT_FORM = '''
{% load i18n %}
{% if display_form %}
<form {% if photos_optional or photos_required %}enctype="multipart/form-data" {% endif %}action="/comments/post/" method="post">

{% if user.is_anonymous %}
<p>{% trans "Username:" %} <input type="text" name="username" id="id_username" /><br />{% trans "Password:" %} <input type="password" name="password" id="id_password" /> (<a href="/accounts/password_reset/">{% trans "Forgotten your password?" %}</a>)</p>
{% else %}
<p>{% trans "Username:" %} <strong>{{ user.username }}</strong> (<a href="/accounts/logout/">{% trans "Log out" %}</a>)</p>
{% endif %}

{% if ratings_optional or ratings_required %}
<p>{% trans "Ratings" %} ({% if ratings_required %}{% trans "Required" %}{% else %}{% trans "Optional" %}{% endif %}):</p>
<table>
<tr><th>&nbsp;</th>{% for value in rating_range %}<th>{{ value }}</th>{% endfor %}</tr>
{% for rating in rating_choices %}
<tr><th>{{ rating }}</th>{% for value in rating_range %}<th><input type="radio" name="rating{{ forloop.parentloop.counter }}" value="{{ value }}" /></th>{% endfor %}</tr>
{% endfor %}
</table>
<input type="hidden" name="rating_options" value="{{ rating_options }}" />
{% endif %}

{% if photos_optional or photos_required %}
<p>{% trans "Post a photo" %} ({% if photos_required %}{% trans "Required" %}{% else %}{% trans "Optional" %}{% endif %}): <input type="file" name="photo" /></p>
<input type="hidden" name="photo_options" value="{{ photo_options }}" />
{% endif %}

<p>Comment:<br /><textarea name="comment" id="id_comment" rows="10" cols="60"></textarea></p>

<input type="hidden" name="options" value="{{ options }}" />
<input type="hidden" name="target" value="{{ target }}" />
<input type="hidden" name="gonzo" value="{{ hash }}" />
<p><input type="submit" name="preview" value="{% trans "Preview comment" %}" /></p>
</form>
{% endif %}
'''

FREE_COMMENT_FORM = '''
{% if display_form %}
<form action="/comments/postfree/" method="post">
<p>{% trans "Your name:" %} <input type="text" id="id_person_name" name="person_name" /></p>
<p>{% trans "Comment:" %}<br /><textarea name="comment" id="id_comment" rows="10" cols="60"></textarea></p>
<input type="hidden" name="options" value="{{ options }}" />
<input type="hidden" name="target" value="{{ target }}" />
<input type="hidden" name="gonzo" value="{{ hash }}" />
<p><input type="submit" name="preview" value="{% trans "Preview comment" %}" /></p>
</form>
{% endif %}
'''

class CommentFormNode(template.Node):
    def __init__(self, content_type, obj_id_lookup_var, obj_id, free,
        photos_optional=False, photos_required=False, photo_options='',
        ratings_optional=False, ratings_required=False, rating_options='',
        is_public=True):
        self.content_type = content_type
        self.obj_id_lookup_var, self.obj_id, self.free = obj_id_lookup_var, obj_id, free
        self.photos_optional, self.photos_required = photos_optional, photos_required
        self.ratings_optional, self.ratings_required = ratings_optional, ratings_required
        self.photo_options, self.rating_options = photo_options, rating_options
        self.is_public = is_public

    def render(self, context):
        from django.utils.text import normalize_newlines
        import base64
        context.push()
        if self.obj_id_lookup_var is not None:
            try:
                self.obj_id = template.resolve_variable(self.obj_id_lookup_var, context)
            except template.VariableDoesNotExist:
                return ''
            # Validate that this object ID is valid for this content-type.
            # We only have to do this validation if obj_id_lookup_var is provided,
            # because do_comment_form() validates hard-coded object IDs.
            try:
                self.content_type.get_object_for_this_type(pk=self.obj_id)
            except ObjectDoesNotExist:
                context['display_form'] = False
            else:
                context['display_form'] = True
        else:
            context['display_form'] = True
        context['target'] = '%s:%s' % (self.content_type.id, self.obj_id)
        options = []
        for var, abbr in (('photos_required', comments.PHOTOS_REQUIRED),
                          ('photos_optional', comments.PHOTOS_OPTIONAL),
                          ('ratings_required', comments.RATINGS_REQUIRED),
                          ('ratings_optional', comments.RATINGS_OPTIONAL),
                          ('is_public', comments.IS_PUBLIC)):
            context[var] = getattr(self, var)
            if getattr(self, var):
                options.append(abbr)
        context['options'] = ','.join(options)
        if self.free:
            context['hash'] = comments.get_security_hash(context['options'], '', '', context['target'])
            default_form = FREE_COMMENT_FORM
        else:
            context['photo_options'] = self.photo_options
            context['rating_options'] = normalize_newlines(base64.encodestring(self.rating_options).strip())
            if self.rating_options:
                context['rating_range'], context['rating_choices'] = comments.get_rating_options(self.rating_options)
            context['hash'] = comments.get_security_hash(context['options'], context['photo_options'], context['rating_options'], context['target'])
            default_form = COMMENT_FORM
        output = template.Template(default_form).render(context)
        context.pop()
        return output

class CommentCountNode(template.Node):
    def __init__(self, package, module, context_var_name, obj_id, var_name, free):
        self.package, self.module = package, module
        self.context_var_name, self.obj_id = context_var_name, obj_id
        self.var_name, self.free = var_name, free

    def render(self, context):
        from django.conf.settings import SITE_ID
        get_count_function = self.free and freecomments.get_count or comments.get_count
        if self.context_var_name is not None:
            self.obj_id = template.resolve_variable(self.context_var_name, context)
        comment_count = get_count_function(object_id__exact=self.obj_id,
            content_type__package__label__exact=self.package,
            content_type__python_module_name__exact=self.module, site__id__exact=SITE_ID)
        context[self.var_name] = comment_count
        return ''

class CommentListNode(template.Node):
    def __init__(self, package, module, context_var_name, obj_id, var_name, free, ordering, extra_kwargs=None):
        self.package, self.module = package, module
        self.context_var_name, self.obj_id = context_var_name, obj_id
        self.var_name, self.free = var_name, free
        self.ordering = ordering
        self.extra_kwargs = extra_kwargs or {}

    def render(self, context):
        from django.conf.settings import COMMENTS_BANNED_USERS_GROUP, SITE_ID
        get_list_function = self.free and freecomments.get_list or comments.get_list_with_karma
        if self.context_var_name is not None:
            try:
                self.obj_id = template.resolve_variable(self.context_var_name, context)
            except template.VariableDoesNotExist:
                return ''
        kwargs = {
            'object_id__exact': self.obj_id,
            'content_type__package__label__exact': self.package,
            'content_type__python_module_name__exact': self.module,
            'site__id__exact': SITE_ID,
            'select_related': True,
            'order_by': (self.ordering + 'submit_date',),
        }
        kwargs.update(self.extra_kwargs)
        if not self.free and COMMENTS_BANNED_USERS_GROUP:
            kwargs['select'] = {'is_hidden': 'user_id IN (SELECT user_id FROM auth_users_groups WHERE group_id = %s)' % COMMENTS_BANNED_USERS_GROUP}
        comment_list = get_list_function(**kwargs)

        if not self.free:
            if context.has_key('user') and not context['user'].is_anonymous():
                user_id = context['user'].id
                context['user_can_moderate_comments'] = comments.user_is_moderator(context['user'])
            else:
                user_id = None
                context['user_can_moderate_comments'] = False
            # Only display comments by banned users to those users themselves.
            if COMMENTS_BANNED_USERS_GROUP:
                comment_list = [c for c in comment_list if not c.is_hidden or (user_id == c.user_id)]

        context[self.var_name] = comment_list
        return ''

class DoCommentForm:
    """
    Displays a comment form for the given params.

    Syntax::

        {% comment_form for [pkg].[py_module_name] [context_var_containing_obj_id] with [list of options] %}

    Example usage::

        {% comment_form for lcom.eventtimes event.id with is_public yes photos_optional thumbs,200,400 ratings_optional scale:1-5|first_option|second_option %}

    ``[context_var_containing_obj_id]`` can be a hard-coded integer or a variable containing the ID.
    """
    def __init__(self, free):
        self.free = free

    def __call__(self, parser, token):
        tokens = token.contents.split()
        if len(tokens) < 4:
            raise template.TemplateSyntaxError, "%r tag requires at least 3 arguments" % tokens[0]
        if tokens[1] != 'for':
            raise template.TemplateSyntaxError, "Second argument in %r tag must be 'for'" % tokens[0]
        try:
            package, module = tokens[2].split('.')
        except ValueError: # unpack list of wrong size
            raise template.TemplateSyntaxError, "Third argument in %r tag must be in the format 'package.module'" % tokens[0]
        try:
            content_type = contenttypes.get_object(package__label__exact=package, python_module_name__exact=module)
        except contenttypes.ContentTypeDoesNotExist:
            raise template.TemplateSyntaxError, "%r tag has invalid content-type '%s.%s'" % (tokens[0], package, module)
        obj_id_lookup_var, obj_id = None, None
        if tokens[3].isdigit():
            obj_id = tokens[3]
            try: # ensure the object ID is valid
                content_type.get_object_for_this_type(pk=obj_id)
            except ObjectDoesNotExist:
                raise template.TemplateSyntaxError, "%r tag refers to %s object with ID %s, which doesn't exist" % (tokens[0], content_type.name, obj_id)
        else:
            obj_id_lookup_var = tokens[3]
        kwargs = {}
        if len(tokens) > 4:
            if tokens[4] != 'with':
                raise template.TemplateSyntaxError, "Fourth argument in %r tag must be 'with'" % tokens[0]
            for option, args in zip(tokens[5::2], tokens[6::2]):
                if option in ('photos_optional', 'photos_required') and not self.free:
                    # VALIDATION ##############################################
                    option_list = args.split(',')
                    if len(option_list) % 3 != 0:
                        raise template.TemplateSyntaxError, "Incorrect number of comma-separated arguments to %r tag" % tokens[0]
                    for opt in option_list[::3]:
                        if not opt.isalnum():
                            raise template.TemplateSyntaxError, "Invalid photo directory name in %r tag: '%s'" % (tokens[0], opt)
                    for opt in option_list[1::3] + option_list[2::3]:
                        if not opt.isdigit() or not (comments.MIN_PHOTO_DIMENSION <= int(opt) <= comments.MAX_PHOTO_DIMENSION):
                            raise template.TemplateSyntaxError, "Invalid photo dimension in %r tag: '%s'. Only values between %s and %s are allowed." % (tokens[0], opt, comments.MIN_PHOTO_DIMENSION, comments.MAX_PHOTO_DIMENSION)
                    # VALIDATION ENDS #########################################
                    kwargs[option] = True
                    kwargs['photo_options'] = args
                elif option in ('ratings_optional', 'ratings_required') and not self.free:
                    # VALIDATION ##############################################
                    if 2 < len(args.split('|')) > 9:
                        raise template.TemplateSyntaxError, "Incorrect number of '%s' options in %r tag. Use between 2 and 8." % (option, tokens[0])
                    if re.match('^scale:\d+\-\d+\:$', args.split('|')[0]):
                        raise template.TemplateSyntaxError, "Invalid 'scale' in %r tag's '%s' options" % (tokens[0], option)
                    # VALIDATION ENDS #########################################
                    kwargs[option] = True
                    kwargs['rating_options'] = args
                elif option in ('is_public'):
                    kwargs[option] = (args == 'true')
                else:
                    raise template.TemplateSyntaxError, "%r tag got invalid parameter '%s'" % (tokens[0], option)
        return CommentFormNode(content_type, obj_id_lookup_var, obj_id, self.free, **kwargs)

class DoCommentCount:
    """
    Gets comment count for the given params and populates the template context
    with a variable containing that value, whose name is defined by the 'as'
    clause.

    Syntax::

        {% get_comment_count for [pkg].[py_module_name] [context_var_containing_obj_id] as [varname]  %}

    Example usage::

        {% get_comment_count for lcom.eventtimes event.id as comment_count %}

    Note: ``[context_var_containing_obj_id]`` can also be a hard-coded integer, like this::

        {% get_comment_count for lcom.eventtimes 23 as comment_count %}
    """
    def __init__(self, free):
        self.free = free

    def __call__(self, parser, token):
        tokens = token.contents.split()
        # Now tokens is a list like this:
        # ['get_comment_list', 'for', 'lcom.eventtimes', 'event.id', 'as', 'comment_list']
        if len(tokens) != 6:
            raise template.TemplateSyntaxError, "%r tag requires 5 arguments" % tokens[0]
        if tokens[1] != 'for':
            raise template.TemplateSyntaxError, "Second argument in %r tag must be 'for'" % tokens[0]
        try:
            package, module = tokens[2].split('.')
        except ValueError: # unpack list of wrong size
            raise template.TemplateSyntaxError, "Third argument in %r tag must be in the format 'package.module'" % tokens[0]
        try:
            content_type = contenttypes.get_object(package__label__exact=package, python_module_name__exact=module)
        except contenttypes.ContentTypeDoesNotExist:
            raise template.TemplateSyntaxError, "%r tag has invalid content-type '%s.%s'" % (tokens[0], package, module)
        var_name, obj_id = None, None
        if tokens[3].isdigit():
            obj_id = tokens[3]
            try: # ensure the object ID is valid
                content_type.get_object_for_this_type(pk=obj_id)
            except ObjectDoesNotExist:
                raise template.TemplateSyntaxError, "%r tag refers to %s object with ID %s, which doesn't exist" % (tokens[0], content_type.name, obj_id)
        else:
            var_name = tokens[3]
        if tokens[4] != 'as':
            raise template.TemplateSyntaxError, "Fourth argument in %r must be 'as'" % tokens[0]
        return CommentCountNode(package, module, var_name, obj_id, tokens[5], self.free)

class DoGetCommentList:
    """
    Gets comments for the given params and populates the template context with a
    special comment_package variable, whose name is defined by the ``as``
    clause.

    Syntax::

        {% get_comment_list for [pkg].[py_module_name] [context_var_containing_obj_id] as [varname] (reversed) %}

    Example usage::

        {% get_comment_list for lcom.eventtimes event.id as comment_list %}

    Note: ``[context_var_containing_obj_id]`` can also be a hard-coded integer, like this::

        {% get_comment_list for lcom.eventtimes 23 as comment_list %}

    To get a list of comments in reverse order -- that is, most recent first --
    pass ``reversed`` as the last param::

        {% get_comment_list for lcom.eventtimes event.id as comment_list reversed %}
    """
    def __init__(self, free):
        self.free = free

    def __call__(self, parser, token):
        tokens = token.contents.split()
        # Now tokens is a list like this:
        # ['get_comment_list', 'for', 'lcom.eventtimes', 'event.id', 'as', 'comment_list']
        if not len(tokens) in (6, 7):
            raise template.TemplateSyntaxError, "%r tag requires 5 or 6 arguments" % tokens[0]
        if tokens[1] != 'for':
            raise template.TemplateSyntaxError, "Second argument in %r tag must be 'for'" % tokens[0]
        try:
            package, module = tokens[2].split('.')
        except ValueError: # unpack list of wrong size
            raise template.TemplateSyntaxError, "Third argument in %r tag must be in the format 'package.module'" % tokens[0]
        try:
            content_type = contenttypes.get_object(package__label__exact=package, python_module_name__exact=module)
        except contenttypes.ContentTypeDoesNotExist:
            raise template.TemplateSyntaxError, "%r tag has invalid content-type '%s.%s'" % (tokens[0], package, module)
        var_name, obj_id = None, None
        if tokens[3].isdigit():
            obj_id = tokens[3]
            try: # ensure the object ID is valid
                content_type.get_object_for_this_type(pk=obj_id)
            except ObjectDoesNotExist:
                raise template.TemplateSyntaxError, "%r tag refers to %s object with ID %s, which doesn't exist" % (tokens[0], content_type.name, obj_id)
        else:
            var_name = tokens[3]
        if tokens[4] != 'as':
            raise template.TemplateSyntaxError, "Fourth argument in %r must be 'as'" % tokens[0]
        if len(tokens) == 7:
            if tokens[6] != 'reversed':
                raise template.TemplateSyntaxError, "Final argument in %r must be 'reversed' if given" % tokens[0]
            ordering = "-"
        else:
            ordering = ""
        return CommentListNode(package, module, var_name, obj_id, tokens[5], self.free, ordering)

# registration comments
template.register_tag('get_comment_list', DoGetCommentList(False))
template.register_tag('comment_form', DoCommentForm(False))
template.register_tag('get_comment_count', DoCommentCount(False))
# free comments
template.register_tag('get_free_comment_list', DoGetCommentList(True))
template.register_tag('free_comment_form', DoCommentForm(True))
template.register_tag('get_free_comment_count', DoCommentCount(True))
