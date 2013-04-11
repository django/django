from __future__ import unicode_literals
import re
import sys

from django.conf import settings
from django.template import (Node, Variable, TemplateSyntaxError,
    TokenParser, Library, TOKEN_TEXT, TOKEN_VAR)
from django.template.base import render_value_in_context
from django.template.defaulttags import token_kwargs
from django.utils import six
from django.utils import translation


register = Library()


class GetAvailableLanguagesNode(Node):
    def __init__(self, variable):
        self.variable = variable

    def render(self, context):
        context[self.variable] = [(k, translation.ugettext(v)) for k, v in settings.LANGUAGES]
        return ''


class GetLanguageInfoNode(Node):
    def __init__(self, lang_code, variable):
        self.lang_code = lang_code
        self.variable = variable

    def render(self, context):
        lang_code = self.lang_code.resolve(context)
        context[self.variable] = translation.get_language_info(lang_code)
        return ''


class GetLanguageInfoListNode(Node):
    def __init__(self, languages, variable):
        self.languages = languages
        self.variable = variable

    def get_language_info(self, language):
        # ``language`` is either a language code string or a sequence
        # with the language code as its first item
        if len(language[0]) > 1:
            return translation.get_language_info(language[0])
        else:
            return translation.get_language_info(str(language))

    def render(self, context):
        langs = self.languages.resolve(context)
        context[self.variable] = [self.get_language_info(lang) for lang in langs]
        return ''


class GetCurrentLanguageNode(Node):
    def __init__(self, variable):
        self.variable = variable

    def render(self, context):
        context[self.variable] = translation.get_language()
        return ''


class GetCurrentLanguageBidiNode(Node):
    def __init__(self, variable):
        self.variable = variable

    def render(self, context):
        context[self.variable] = translation.get_language_bidi()
        return ''


class TranslateNode(Node):
    def __init__(self, filter_expression, noop, asvar=None,
                 message_context=None):
        self.noop = noop
        self.asvar = asvar
        self.message_context = message_context
        self.filter_expression = filter_expression
        if isinstance(self.filter_expression.var, six.string_types):
            self.filter_expression.var = Variable("'%s'" %
                                                  self.filter_expression.var)

    def render(self, context):
        self.filter_expression.var.translate = not self.noop
        if self.message_context:
            self.filter_expression.var.message_context = (
                self.message_context.resolve(context))
        output = self.filter_expression.resolve(context)
        value = render_value_in_context(output, context)
        if self.asvar:
            context[self.asvar] = value
            return ''
        else:
            return value


class BlockTranslateNode(Node):
    def __init__(self, extra_context, singular, plural=None, countervar=None,
            counter=None, message_context=None):
        self.extra_context = extra_context
        self.singular = singular
        self.plural = plural
        self.countervar = countervar
        self.counter = counter
        self.message_context = message_context

    def render_token_list(self, tokens):
        result = []
        vars = []
        for token in tokens:
            if token.token_type == TOKEN_TEXT:
                result.append(token.contents.replace('%', '%%'))
            elif token.token_type == TOKEN_VAR:
                result.append('%%(%s)s' % token.contents)
                vars.append(token.contents)
        return ''.join(result), vars

    def render(self, context, nested=False):
        if self.message_context:
            message_context = self.message_context.resolve(context)
        else:
            message_context = None
        tmp_context = {}
        for var, val in self.extra_context.items():
            tmp_context[var] = val.resolve(context)
        # Update() works like a push(), so corresponding context.pop() is at
        # the end of function
        context.update(tmp_context)
        singular, vars = self.render_token_list(self.singular)
        if self.plural and self.countervar and self.counter:
            count = self.counter.resolve(context)
            context[self.countervar] = count
            plural, plural_vars = self.render_token_list(self.plural)
            if message_context:
                result = translation.npgettext(message_context, singular,
                                               plural, count)
            else:
                result = translation.ungettext(singular, plural, count)
            vars.extend(plural_vars)
        else:
            if message_context:
                result = translation.pgettext(message_context, singular)
            else:
                result = translation.ugettext(singular)
        default_value = settings.TEMPLATE_STRING_IF_INVALID
        render_value = lambda v: render_value_in_context(
            context.get(v, default_value), context)
        data = dict([(v, render_value(v)) for v in vars])
        context.pop()
        try:
            result = result % data
        except (KeyError, ValueError):
            if nested:
                # Either string is malformed, or it's a bug
                raise TemplateSyntaxError("'blocktrans' is unable to format "
                    "string returned by gettext: %r using %r" % (result, data))
            with translation.override(None):
                result = self.render(context, nested=True)
        return result


class LanguageNode(Node):
    def __init__(self, nodelist, language):
        self.nodelist = nodelist
        self.language = language

    def render(self, context):
        with translation.override(self.language.resolve(context)):
            output = self.nodelist.render(context)
        return output


@register.tag("get_available_languages")
def do_get_available_languages(parser, token):
    """
    This will store a list of available languages
    in the context.

    Usage::

        {% get_available_languages as languages %}
        {% for language in languages %}
        ...
        {% endfor %}

    This will just pull the LANGUAGES setting from
    your setting file (or the default settings) and
    put it into the named variable.
    """
    # token.split_contents() isn't useful here because this tag doesn't accept variable as arguments
    args = token.contents.split()
    if len(args) != 3 or args[1] != 'as':
        raise TemplateSyntaxError("'get_available_languages' requires 'as variable' (got %r)" % args)
    return GetAvailableLanguagesNode(args[2])

@register.tag("get_language_info")
def do_get_language_info(parser, token):
    """
    This will store the language information dictionary for the given language
    code in a context variable.

    Usage::

        {% get_language_info for LANGUAGE_CODE as l %}
        {{ l.code }}
        {{ l.name }}
        {{ l.name_local }}
        {{ l.bidi|yesno:"bi-directional,uni-directional" }}
    """
    args = token.split_contents()
    if len(args) != 5 or args[1] != 'for' or args[3] != 'as':
        raise TemplateSyntaxError("'%s' requires 'for string as variable' (got %r)" % (args[0], args[1:]))
    return GetLanguageInfoNode(parser.compile_filter(args[2]), args[4])

@register.tag("get_language_info_list")
def do_get_language_info_list(parser, token):
    """
    This will store a list of language information dictionaries for the given
    language codes in a context variable. The language codes can be specified
    either as a list of strings or a settings.LANGUAGES style tuple (or any
    sequence of sequences whose first items are language codes).

    Usage::

        {% get_language_info_list for LANGUAGES as langs %}
        {% for l in langs %}
          {{ l.code }}
          {{ l.name }}
          {{ l.name_local }}
          {{ l.bidi|yesno:"bi-directional,uni-directional" }}
        {% endfor %}
    """
    args = token.split_contents()
    if len(args) != 5 or args[1] != 'for' or args[3] != 'as':
        raise TemplateSyntaxError("'%s' requires 'for sequence as variable' (got %r)" % (args[0], args[1:]))
    return GetLanguageInfoListNode(parser.compile_filter(args[2]), args[4])

@register.filter
def language_name(lang_code):
    return translation.get_language_info(lang_code)['name']

@register.filter
def language_name_local(lang_code):
    return translation.get_language_info(lang_code)['name_local']

@register.filter
def language_bidi(lang_code):
    return translation.get_language_info(lang_code)['bidi']

@register.tag("get_current_language")
def do_get_current_language(parser, token):
    """
    This will store the current language in the context.

    Usage::

        {% get_current_language as language %}

    This will fetch the currently active language and
    put it's value into the ``language`` context
    variable.
    """
    # token.split_contents() isn't useful here because this tag doesn't accept variable as arguments
    args = token.contents.split()
    if len(args) != 3 or args[1] != 'as':
        raise TemplateSyntaxError("'get_current_language' requires 'as variable' (got %r)" % args)
    return GetCurrentLanguageNode(args[2])

@register.tag("get_current_language_bidi")
def do_get_current_language_bidi(parser, token):
    """
    This will store the current language layout in the context.

    Usage::

        {% get_current_language_bidi as bidi %}

    This will fetch the currently active language's layout and
    put it's value into the ``bidi`` context variable.
    True indicates right-to-left layout, otherwise left-to-right
    """
    # token.split_contents() isn't useful here because this tag doesn't accept variable as arguments
    args = token.contents.split()
    if len(args) != 3 or args[1] != 'as':
        raise TemplateSyntaxError("'get_current_language_bidi' requires 'as variable' (got %r)" % args)
    return GetCurrentLanguageBidiNode(args[2])

@register.tag("trans")
def do_translate(parser, token):
    """
    This will mark a string for translation and will
    translate the string for the current language.

    Usage::

        {% trans "this is a test" %}

    This will mark the string for translation so it will
    be pulled out by mark-messages.py into the .po files
    and will run the string through the translation engine.

    There is a second form::

        {% trans "this is a test" noop %}

    This will only mark for translation, but will return
    the string unchanged. Use it when you need to store
    values into forms that should be translated later on.

    You can use variables instead of constant strings
    to translate stuff you marked somewhere else::

        {% trans variable %}

    This will just try to translate the contents of
    the variable ``variable``. Make sure that the string
    in there is something that is in the .po file.

    It is possible to store the translated string into a variable::

        {% trans "this is a test" as var %}
        {{ var }}

    Contextual translations are also supported::

        {% trans "this is a test" context "greeting" %}

    This is equivalent to calling pgettext instead of (u)gettext.
    """
    class TranslateParser(TokenParser):
        def top(self):
            value = self.value()

            # Backwards Compatiblity fix:
            # FilterExpression does not support single-quoted strings,
            # so we make a cheap localized fix in order to maintain
            # backwards compatibility with existing uses of ``trans``
            # where single quote use is supported.
            if value[0] == "'":
                m = re.match("^'([^']+)'(\|.*$)", value)
                if m:
                    value = '"%s"%s' % (m.group(1).replace('"','\\"'), m.group(2))
                elif value[-1] == "'":
                    value = '"%s"' % value[1:-1].replace('"','\\"')

            noop = False
            asvar = None
            message_context = None

            while self.more():
                tag = self.tag()
                if tag == 'noop':
                    noop = True
                elif tag == 'context':
                    message_context = parser.compile_filter(self.value())
                elif tag == 'as':
                    asvar = self.tag()
                else:
                    raise TemplateSyntaxError(
                        "Only options for 'trans' are 'noop', " \
                        "'context \"xxx\"', and 'as VAR'.")
            return value, noop, asvar, message_context
    value, noop, asvar, message_context = TranslateParser(token.contents).top()
    return TranslateNode(parser.compile_filter(value), noop, asvar,
                         message_context)

@register.tag("blocktrans")
def do_block_translate(parser, token):
    """
    This will translate a block of text with parameters.

    Usage::

        {% blocktrans with bar=foo|filter boo=baz|filter %}
        This is {{ bar }} and {{ boo }}.
        {% endblocktrans %}

    Additionally, this supports pluralization::

        {% blocktrans count count=var|length %}
        There is {{ count }} object.
        {% plural %}
        There are {{ count }} objects.
        {% endblocktrans %}

    This is much like ngettext, only in template syntax.

    The "var as value" legacy format is still supported::

        {% blocktrans with foo|filter as bar and baz|filter as boo %}
        {% blocktrans count var|length as count %}

    Contextual translations are supported::

        {% blocktrans with bar=foo|filter context "greeting" %}
            This is {{ bar }}.
        {% endblocktrans %}

    This is equivalent to calling pgettext/npgettext instead of
    (u)gettext/(u)ngettext.
    """
    bits = token.split_contents()

    options = {}
    remaining_bits = bits[1:]
    while remaining_bits:
        option = remaining_bits.pop(0)
        if option in options:
            raise TemplateSyntaxError('The %r option was specified more '
                                      'than once.' % option)
        if option == 'with':
            value = token_kwargs(remaining_bits, parser, support_legacy=True)
            if not value:
                raise TemplateSyntaxError('"with" in %r tag needs at least '
                                          'one keyword argument.' % bits[0])
        elif option == 'count':
            value = token_kwargs(remaining_bits, parser, support_legacy=True)
            if len(value) != 1:
                raise TemplateSyntaxError('"count" in %r tag expected exactly '
                                          'one keyword argument.' % bits[0])
        elif option == "context":
            try:
                value = remaining_bits.pop(0)
                value = parser.compile_filter(value)
            except Exception:
                msg = (
                    '"context" in %r tag expected '
                    'exactly one argument.') % bits[0]
                six.reraise(TemplateSyntaxError, TemplateSyntaxError(msg), sys.exc_info()[2])
        else:
            raise TemplateSyntaxError('Unknown argument for %r tag: %r.' %
                                      (bits[0], option))
        options[option] = value

    if 'count' in options:
        countervar, counter = list(six.iteritems(options['count']))[0]
    else:
        countervar, counter = None, None
    if 'context' in options:
        message_context = options['context']
    else:
        message_context = None
    extra_context = options.get('with', {})

    singular = []
    plural = []
    while parser.tokens:
        token = parser.next_token()
        if token.token_type in (TOKEN_VAR, TOKEN_TEXT):
            singular.append(token)
        else:
            break
    if countervar and counter:
        if token.contents.strip() != 'plural':
            raise TemplateSyntaxError("'blocktrans' doesn't allow other block tags inside it")
        while parser.tokens:
            token = parser.next_token()
            if token.token_type in (TOKEN_VAR, TOKEN_TEXT):
                plural.append(token)
            else:
                break
    if token.contents.strip() != 'endblocktrans':
        raise TemplateSyntaxError("'blocktrans' doesn't allow other block tags (seen %r) inside it" % token.contents)

    return BlockTranslateNode(extra_context, singular, plural, countervar,
            counter, message_context)

@register.tag
def language(parser, token):
    """
    This will enable the given language just for this block.

    Usage::

        {% language "de" %}
            This is {{ bar }} and {{ boo }}.
        {% endlanguage %}

    """
    bits = token.split_contents()
    if len(bits) != 2:
        raise TemplateSyntaxError("'%s' takes one argument (language)" % bits[0])
    language = parser.compile_filter(bits[1])
    nodelist = parser.parse(('endlanguage',))
    parser.delete_first_token()
    return LanguageNode(nodelist, language)
