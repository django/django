"""
    pygments.lexers.bqn
    ~~~~~~~~~~~~~~~~~~~

    Lexer for BQN.

    :copyright: Copyright 2006-2023 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from pygments.lexer import RegexLexer
from pygments.token import Comment, Operator, Keyword, Name, String, \
    Number, Punctuation, Whitespace

__all__ = ['BQNLexer']


class BQNLexer(RegexLexer):
    """
    A simple BQN lexer.

    .. versionadded:: 2.16
    """
    name = 'BQN'
    url = 'https://mlochbaum.github.io/BQN/index.html'
    aliases = ['bqn']
    filenames = ['*.bqn']
    mimetypes = []

    tokens = {
        'root': [
            # Whitespace
            # ==========
            (r'\s+', Whitespace),
            #
            # Comment
            # =======
            # '#' is a comment that continues to the end of the line
            (r'#.*$', Comment.Single),
            #
            # Strings
            # =======
            (r'\'((\'\')|[^\'])*\'', String.Single),
            (r'"(("")|[^"])*"', String.Double),
            #
            # Null Character
            # ==============
            # Literal representation of the null character
            (r'@', String.Symbol),
            #
            # Punctuation
            # ===========
            # This token type is used for diamond, commas
            # and  array and list brackets and strand syntax
            (r'[\.⋄,\[\]⟨⟩‿]', Punctuation),
            #
            # Expression Grouping
            # ===================
            # Since this token type is important in BQN, it is not included in
            # the punctuation token type but rather in the following one
            (r'[\(\)]', String.Regex), 
            #
            # Numbers
            # =======
            # Includes the numeric literals and the Nothing character
            (r'¯?([0-9]+\.?[0-9]+|[0-9]+)([Ee][¯]?[0-9]+)?|¯|∞|π|·', Number),
            #
            # Variables
            # =========
            (r'\b[a-z]\w*\b', Name.Variable),
            #
            # 1-Modifiers
            # ===========
            (r'[˙˜˘¨⌜⁼´˝`𝕣]', Name.Attribute),
            (r'\b_[a-zA-Z0-9]+\b', Name.Attribute),
            #
            # 2-Modifiers
            # ===========
            (r'[∘○⊸⟜⌾⊘◶⎉⚇⍟⎊]', Name.Property),
            (r'\b_[a-zA-Z0-9]+_\b', Name.Property),
            #
            # Functions
            # =========
            # The monadic or dyadic function primitives and function
            # operands and arguments, along with function self-reference
            (r'[+\-×÷\*√⌊⌈∧∨¬|≤<>≥=≠≡≢⊣⊢⥊∾≍⋈↑↓↕«»⌽⍉/⍋⍒⊏⊑⊐⊒∊⍷⊔!𝕎𝕏𝔽𝔾𝕊]',
             Operator),
            (r'[A-Z]\w*|•\w+\b', Operator),
            #
            # Constant
            # ========
            (r'˙', Name.Constant),
            #
            # Define/Export/Change
            # ====================
            (r'[←↩⇐]', Keyword.Declaration),
            #
            # Blocks
            # ======
            (r'[{}]', Keyword.Type),
            #
            # Extra characters
            # ================
            (r'[;:?𝕨𝕩𝕗𝕘𝕤]', Name.Entity),
            #
            
        ],
    }

    
