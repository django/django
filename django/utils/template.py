from django.conf import settings

def compile_string(template_string, origin):
    "Compiles template_string into NodeList ready for rendering"
    if settings.TEMPLATE_DEBUG:
        from django.template.debug import DebugLexer, DebugParser
        lexer_class, parser_class = DebugLexer, DebugParser
    else:
        lexer_class, parser_class = Lexer, Parser
    lexer = lexer_class(template_string, origin)
    parser = parser_class(lexer.tokenize())
    return parser.parse()

