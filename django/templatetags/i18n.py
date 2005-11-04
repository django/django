"Default tags used by the template system, available to all templates."

from django.core.template import Node, NodeList, Template, Context, resolve_variable, resolve_variable_with_filters, registered_filters
from django.core.template import TemplateSyntaxError, register_tag, TokenParser
from django.core.template import TOKEN_BLOCK, TOKEN_TEXT, TOKEN_VAR
from django.utils import translation

import sys
import re

class GetAvailableLanguagesNode(Node):

    def __init__(self, variable):
        self.variable = variable

    def render(self, context):
        from django.conf.settings import LANGUAGES
        context[self.variable] = LANGUAGES
        return ''

class GetCurrentLanguageNode(Node):

    def __init__(self, variable):
        self.variable = variable

    def render(self, context):
        context[self.variable] = translation.get_language()
        return ''

class TranslateNode(Node):

    def __init__(self, value, noop):
        self.value = value
        self.noop = noop

    def render(self, context):
        value = resolve_variable(self.value, context)
        if self.noop:
            return value
        else:
            return translation.gettext(value)

class BlockTranslateNode(Node):

    def __init__(self, extra_context, singular, plural=None, countervar=None, counter=None):
        self.extra_context = extra_context
        self.singular = singular
        self.plural = plural
        self.countervar = countervar
        self.counter = counter

    def render_token_list(self, tokens):
        result = []
        for token in tokens:
            if token.token_type == TOKEN_TEXT:
                result.append(token.contents)
            elif token.token_type == TOKEN_VAR:
                result.append('%%(%s)s' % token.contents)
        return ''.join(result)

    def render(self, context):
        context.push()
        for var,val in self.extra_context.items():
            context[var] = resolve_variable_with_filters(val, context)
        singular = self.render_token_list(self.singular) % context
        if self.plural and self.countervar and self.counter:
            count = resolve_variable_with_filters(self.counter, context)
            context[self.countervar] = count
            plural = self.render_token_list(self.plural) % context
            result = translation.ngettext(singular, plural, count) % context
        else:
            result = translation.gettext(singular) % context
        context.pop()
        return result

def do_get_available_languages(parser, token):
    """
    This will store a list of available languages
    in the context.

    Usage is as follows::

        {% get_available_languages as languages %}
        {% for language in languages %}
        ...
        {% endfor %}

    This will just pull the LANGUAGES setting from
    your setting file (or the default settings) and
    put it into the named variable.
    """

    args = token.contents.split()
    if len(args) != 3 or args[1] != 'as':
        raise TemplateSyntaxError, "'get_available_languages' requires 'as variable' (got %r)" % args
    return GetAvailableLanguagesNode(args[2])

def do_get_current_language(parser, token):
    """
    This will store the current language in
    the context.

    Usage is as follows::

        {% get_current_language as language %}

    This will fetch the currently active language and
    put it's value into the ``language`` context
    variable.
    """

    args = token.contents.split()
    if len(args) != 3 or args[1] != 'as':
        raise TemplateSyntaxError, "'get_available_languages' requires 'as variable' (got %r)" % args
    return GetCurrentLanguageNode(args[2])

def do_translate(parser, token):
    """
    This will mark a string for translation and will
    translate the string for the current language.

    Usage is like this::

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
    """

    class TranslateParser(TokenParser):

        def top(self):
            value = self.value()
            if self.more():
                if self.tag() == 'noop':
                    noop = True
                else:
                    raise TemplateSyntaxError, "only option for 'trans' is 'noop'"
            else:
                noop = False
            return (value, noop)

    (value, noop) = TranslateParser(token.contents).top()
    return TranslateNode(value, noop)

def do_block_translate(parser, token):
    """
    """
    class BlockTranslateParser(TokenParser):

        def top(self):
            countervar = None
            counter = None
            extra_context = {}
            while self.more():
                tag = self.tag()
                if tag == 'with' or tag == 'and':
                    value = self.value()
                    if self.tag() != 'as':
                        raise TemplateSyntaxError, "variable bindings in 'blocktrans' must be 'with value as variable'"
                    extra_context[self.tag()] = value
                elif tag == 'count':
                    counter = self.value()
                    if self.tag() != 'as':
                        raise TemplateSyntaxError, "counter specification in 'blocktrans' must be 'count value as variable'"
                    countervar = self.tag()
                else:
                    raise TemplateSyntaxError, "unknown subtag %s for 'blocktrans' found" % tag
            return (countervar, counter, extra_context)

    (countervar, counter, extra_context) = BlockTranslateParser(token.contents).top()

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
            raise TemplateSyntaxError, "'blocktrans' doesn't allow other block tags inside it" % tag
        while parser.tokens:
            token = parser.next_token()
            if token.token_type in (TOKEN_VAR, TOKEN_TEXT):
                plural.append(token)
            else:
                break
    if token.contents.strip() != 'endblocktrans':
        raise TemplateSyntaxError, "'blocktrans' doesn't allow other block tags (seen %r) inside it" % token.contents

    return BlockTranslateNode(extra_context, singular, plural, countervar, counter)

register_tag('get_available_languages', do_get_available_languages)
register_tag('get_current_language', do_get_current_language)
register_tag('trans', do_translate)
register_tag('blocktrans', do_block_translate)

