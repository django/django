from django.conf import settings
from django.template.base import Lexer, Parser, tag_re, NodeList, VariableNode, TemplateSyntaxError
from django.utils.encoding import force_unicode
from django.utils.html import escape
from django.utils.safestring import SafeData, EscapeData
from django.utils.formats import localize

class DebugLexer(Lexer):
    def __init__(self, template_string, origin):
        super(DebugLexer, self).__init__(template_string, origin)

    def tokenize(self):
        "Return a list of tokens from a given template_string"
        result, upto = [], 0
        for match in tag_re.finditer(self.template_string):
            start, end = match.span()
            if start > upto:
                result.append(self.create_token(self.template_string[upto:start], (upto, start), False))
                upto = start
            result.append(self.create_token(self.template_string[start:end], (start, end), True))
            upto = end
        last_bit = self.template_string[upto:]
        if last_bit:
            result.append(self.create_token(last_bit, (upto, upto + len(last_bit)), False))
        return result

    def create_token(self, token_string, source, in_tag):
        token = super(DebugLexer, self).create_token(token_string, in_tag)
        token.source = self.origin, source
        return token

class DebugParser(Parser):
    def __init__(self, lexer):
        super(DebugParser, self).__init__(lexer)
        self.command_stack = []

    def enter_command(self, command, token):
        self.command_stack.append( (command, token.source) )

    def exit_command(self):
        self.command_stack.pop()

    def error(self, token, msg):
        return self.source_error(token.source, msg)

    def source_error(self, source,msg):
        e = TemplateSyntaxError(msg)
        e.source = source
        return e

    def create_nodelist(self):
        return DebugNodeList()

    def create_variable_node(self, contents):
        return DebugVariableNode(contents)

    def extend_nodelist(self, nodelist, node, token):
        node.source = token.source
        super(DebugParser, self).extend_nodelist(nodelist, node, token)

    def unclosed_block_tag(self, parse_until):
        command, source = self.command_stack.pop()
        msg = "Unclosed tag '%s'. Looking for one of: %s " % (command, ', '.join(parse_until))
        raise self.source_error(source, msg)

    def compile_function_error(self, token, e):
        if not hasattr(e, 'source'):
            e.source = token.source

class DebugNodeList(NodeList):
    def render_node(self, node, context):
        try:
            result = node.render(context)
        except TemplateSyntaxError, e:
            if not hasattr(e, 'source'):
                e.source = node.source
            raise
        except Exception, e:
            from sys import exc_info
            wrapped = TemplateSyntaxError(u'Caught %s while rendering: %s' %
                (e.__class__.__name__, force_unicode(e, errors='replace')))
            wrapped.source = node.source
            wrapped.exc_info = exc_info()
            raise wrapped, None, wrapped.exc_info[2]
        return result

class DebugVariableNode(VariableNode):
    def render(self, context):
        try:
            output = self.filter_expression.resolve(context)
            output = localize(output, use_l10n=context.use_l10n)
            output = force_unicode(output)
        except TemplateSyntaxError, e:
            if not hasattr(e, 'source'):
                e.source = self.source
            raise
        except UnicodeDecodeError:
            return ''
        if (context.autoescape and not isinstance(output, SafeData)) or isinstance(output, EscapeData):
            return escape(output)
        else:
            return output
