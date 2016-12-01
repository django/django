import re
import warnings

from django.template.base import (
    TOKEN_BLOCK, TOKEN_COMMENT, TOKEN_TEXT, TOKEN_VAR, TRANSLATOR_COMMENT_MARK,
    Lexer,
)
from django.utils.encoding import force_text
from django.utils.six import StringIO

from . import TranslatorCommentWarning, trim_whitespace

dot_re = re.compile(r'\S')


def blankout(src, char):
    """
    Change every non-whitespace character to the given char.
    Used in the templatize function.
    """
    return dot_re.sub(char, src)


context_re = re.compile(r"""^\s+.*context\s+((?:"[^"]*?")|(?:'[^']*?'))\s*""")
inline_re = re.compile(
    # Match the trans 'some text' part
    r"""^\s*trans\s+((?:"[^"]*?")|(?:'[^']*?'))"""
    # Match and ignore optional filters
    r"""(?:\s*\|\s*[^\s:]+(?::(?:[^\s'":]+|(?:"[^"]*?")|(?:'[^']*?')))?)*"""
    # Match the optional context part
    r"""(\s+.*context\s+((?:"[^"]*?")|(?:'[^']*?')))?\s*"""
)
block_re = re.compile(r"""^\s*blocktrans(\s+.*context\s+((?:"[^"]*?")|(?:'[^']*?')))?(?:\s+|$)""")
endblock_re = re.compile(r"""^\s*endblocktrans$""")
plural_re = re.compile(r"""^\s*plural$""")
constant_re = re.compile(r"""_\(((?:".*?")|(?:'.*?'))\)""")


def templatize(src, origin=None, charset='utf-8'):
    """
    Turn a Django template into something that is understood by xgettext. It
    does so by translating the Django translation tags into standard gettext
    function invocations.
    """
    src = force_text(src, charset)
    out = StringIO('')
    message_context = None
    intrans = False
    inplural = False
    trimmed = False
    singular = []
    plural = []
    incomment = False
    comment = []
    lineno_comment_map = {}
    comment_lineno_cache = None
    # Adding the u prefix allows gettext to recognize the Unicode string
    # (#26093).
    raw_prefix = 'u'

    def join_tokens(tokens, trim=False):
        message = ''.join(tokens)
        if trim:
            message = trim_whitespace(message)
        return message

    for t in Lexer(src).tokenize():
        if incomment:
            if t.token_type == TOKEN_BLOCK and t.contents == 'endcomment':
                content = ''.join(comment)
                translators_comment_start = None
                for lineno, line in enumerate(content.splitlines(True)):
                    if line.lstrip().startswith(TRANSLATOR_COMMENT_MARK):
                        translators_comment_start = lineno
                for lineno, line in enumerate(content.splitlines(True)):
                    if translators_comment_start is not None and lineno >= translators_comment_start:
                        out.write(' # %s' % line)
                    else:
                        out.write(' #\n')
                incomment = False
                comment = []
            else:
                comment.append(t.contents)
        elif intrans:
            if t.token_type == TOKEN_BLOCK:
                endbmatch = endblock_re.match(t.contents)
                pluralmatch = plural_re.match(t.contents)
                if endbmatch:
                    if inplural:
                        if message_context:
                            out.write(' npgettext({p}{!r}, {p}{!r}, {p}{!r},count) '.format(
                                message_context,
                                join_tokens(singular, trimmed),
                                join_tokens(plural, trimmed),
                                p=raw_prefix,
                            ))
                        else:
                            out.write(' ngettext({p}{!r}, {p}{!r}, count) '.format(
                                join_tokens(singular, trimmed),
                                join_tokens(plural, trimmed),
                                p=raw_prefix,
                            ))
                        for part in singular:
                            out.write(blankout(part, 'S'))
                        for part in plural:
                            out.write(blankout(part, 'P'))
                    else:
                        if message_context:
                            out.write(' pgettext({p}{!r}, {p}{!r}) '.format(
                                message_context,
                                join_tokens(singular, trimmed),
                                p=raw_prefix,
                            ))
                        else:
                            out.write(' gettext({p}{!r}) '.format(
                                join_tokens(singular, trimmed),
                                p=raw_prefix,
                            ))
                        for part in singular:
                            out.write(blankout(part, 'S'))
                    message_context = None
                    intrans = False
                    inplural = False
                    singular = []
                    plural = []
                elif pluralmatch:
                    inplural = True
                else:
                    filemsg = ''
                    if origin:
                        filemsg = 'file %s, ' % origin
                    raise SyntaxError(
                        "Translation blocks must not include other block tags: "
                        "%s (%sline %d)" % (t.contents, filemsg, t.lineno)
                    )
            elif t.token_type == TOKEN_VAR:
                if inplural:
                    plural.append('%%(%s)s' % t.contents)
                else:
                    singular.append('%%(%s)s' % t.contents)
            elif t.token_type == TOKEN_TEXT:
                contents = t.contents.replace('%', '%%')
                if inplural:
                    plural.append(contents)
                else:
                    singular.append(contents)
        else:
            # Handle comment tokens (`{# ... #}`) plus other constructs on
            # the same line:
            if comment_lineno_cache is not None:
                cur_lineno = t.lineno + t.contents.count('\n')
                if comment_lineno_cache == cur_lineno:
                    if t.token_type != TOKEN_COMMENT:
                        for c in lineno_comment_map[comment_lineno_cache]:
                            filemsg = ''
                            if origin:
                                filemsg = 'file %s, ' % origin
                            warn_msg = (
                                "The translator-targeted comment '%s' "
                                "(%sline %d) was ignored, because it wasn't "
                                "the last item on the line."
                            ) % (c, filemsg, comment_lineno_cache)
                            warnings.warn(warn_msg, TranslatorCommentWarning)
                        lineno_comment_map[comment_lineno_cache] = []
                else:
                    out.write('# %s' % ' | '.join(lineno_comment_map[comment_lineno_cache]))
                comment_lineno_cache = None

            if t.token_type == TOKEN_BLOCK:
                imatch = inline_re.match(t.contents)
                bmatch = block_re.match(t.contents)
                cmatches = constant_re.findall(t.contents)
                if imatch:
                    g = imatch.group(1)
                    if g[0] == '"':
                        g = g.strip('"')
                    elif g[0] == "'":
                        g = g.strip("'")
                    g = g.replace('%', '%%')
                    if imatch.group(2):
                        # A context is provided
                        context_match = context_re.match(imatch.group(2))
                        message_context = context_match.group(1)
                        if message_context[0] == '"':
                            message_context = message_context.strip('"')
                        elif message_context[0] == "'":
                            message_context = message_context.strip("'")
                        out.write(' pgettext({p}{!r}, {p}{!r}) '.format(
                            message_context, g, p=raw_prefix
                        ))
                        message_context = None
                    else:
                        out.write(' gettext({p}{!r}) '.format(g, p=raw_prefix))
                elif bmatch:
                    for fmatch in constant_re.findall(t.contents):
                        out.write(' _(%s) ' % fmatch)
                    if bmatch.group(1):
                        # A context is provided
                        context_match = context_re.match(bmatch.group(1))
                        message_context = context_match.group(1)
                        if message_context[0] == '"':
                            message_context = message_context.strip('"')
                        elif message_context[0] == "'":
                            message_context = message_context.strip("'")
                    intrans = True
                    inplural = False
                    trimmed = 'trimmed' in t.split_contents()
                    singular = []
                    plural = []
                elif cmatches:
                    for cmatch in cmatches:
                        out.write(' _(%s) ' % cmatch)
                elif t.contents == 'comment':
                    incomment = True
                else:
                    out.write(blankout(t.contents, 'B'))
            elif t.token_type == TOKEN_VAR:
                parts = t.contents.split('|')
                cmatch = constant_re.match(parts[0])
                if cmatch:
                    out.write(' _(%s) ' % cmatch.group(1))
                for p in parts[1:]:
                    if p.find(':_(') >= 0:
                        out.write(' %s ' % p.split(':', 1)[1])
                    else:
                        out.write(blankout(p, 'F'))
            elif t.token_type == TOKEN_COMMENT:
                if t.contents.lstrip().startswith(TRANSLATOR_COMMENT_MARK):
                    lineno_comment_map.setdefault(t.lineno, []).append(t.contents)
                    comment_lineno_cache = t.lineno
            else:
                out.write(blankout(t.contents, 'X'))
    return out.getvalue()
