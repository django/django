# -*- coding: utf-8 -*-
"""
    pygments.lexers.actionscript
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Lexers for ActionScript and MXML.

    :copyright: Copyright 2006-2017 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import RegexLexer, bygroups, using, this, words, default
from pygments.token import Text, Comment, Operator, Keyword, Name, String, \
    Number, Punctuation

__all__ = ['ActionScriptLexer', 'ActionScript3Lexer', 'MxmlLexer']


class ActionScriptLexer(RegexLexer):
    """
    For ActionScript source code.

    .. versionadded:: 0.9
    """

    name = 'ActionScript'
    aliases = ['as', 'actionscript']
    filenames = ['*.as']
    mimetypes = ['application/x-actionscript', 'text/x-actionscript',
                 'text/actionscript']

    flags = re.DOTALL
    tokens = {
        'root': [
            (r'\s+', Text),
            (r'//.*?\n', Comment.Single),
            (r'/\*.*?\*/', Comment.Multiline),
            (r'/(\\\\|\\/|[^/\n])*/[gim]*', String.Regex),
            (r'[~^*!%&<>|+=:;,/?\\-]+', Operator),
            (r'[{}\[\]();.]+', Punctuation),
            (words((
                'case', 'default', 'for', 'each', 'in', 'while', 'do', 'break',
                'return', 'continue', 'if', 'else', 'throw', 'try', 'catch',
                'var', 'with', 'new', 'typeof', 'arguments', 'instanceof', 'this',
                'switch'), suffix=r'\b'),
             Keyword),
            (words((
                'class', 'public', 'final', 'internal', 'native', 'override', 'private',
                'protected', 'static', 'import', 'extends', 'implements', 'interface',
                'intrinsic', 'return', 'super', 'dynamic', 'function', 'const', 'get',
                'namespace', 'package', 'set'), suffix=r'\b'),
             Keyword.Declaration),
            (r'(true|false|null|NaN|Infinity|-Infinity|undefined|Void)\b',
             Keyword.Constant),
            (words((
                'Accessibility', 'AccessibilityProperties', 'ActionScriptVersion',
                'ActivityEvent', 'AntiAliasType', 'ApplicationDomain', 'AsBroadcaster', 'Array',
                'AsyncErrorEvent', 'AVM1Movie', 'BevelFilter', 'Bitmap', 'BitmapData',
                'BitmapDataChannel', 'BitmapFilter', 'BitmapFilterQuality', 'BitmapFilterType',
                'BlendMode', 'BlurFilter', 'Boolean', 'ByteArray', 'Camera', 'Capabilities', 'CapsStyle',
                'Class', 'Color', 'ColorMatrixFilter', 'ColorTransform', 'ContextMenu',
                'ContextMenuBuiltInItems', 'ContextMenuEvent', 'ContextMenuItem',
                'ConvultionFilter', 'CSMSettings', 'DataEvent', 'Date', 'DefinitionError',
                'DeleteObjectSample', 'Dictionary', 'DisplacmentMapFilter', 'DisplayObject',
                'DisplacmentMapFilterMode', 'DisplayObjectContainer', 'DropShadowFilter',
                'Endian', 'EOFError', 'Error', 'ErrorEvent', 'EvalError', 'Event', 'EventDispatcher',
                'EventPhase', 'ExternalInterface', 'FileFilter', 'FileReference',
                'FileReferenceList', 'FocusDirection', 'FocusEvent', 'Font', 'FontStyle', 'FontType',
                'FrameLabel', 'FullScreenEvent', 'Function', 'GlowFilter', 'GradientBevelFilter',
                'GradientGlowFilter', 'GradientType', 'Graphics', 'GridFitType', 'HTTPStatusEvent',
                'IBitmapDrawable', 'ID3Info', 'IDataInput', 'IDataOutput', 'IDynamicPropertyOutput'
                'IDynamicPropertyWriter', 'IEventDispatcher', 'IExternalizable',
                'IllegalOperationError', 'IME', 'IMEConversionMode', 'IMEEvent', 'int',
                'InteractiveObject', 'InterpolationMethod', 'InvalidSWFError', 'InvokeEvent',
                'IOError', 'IOErrorEvent', 'JointStyle', 'Key', 'Keyboard', 'KeyboardEvent', 'KeyLocation',
                'LineScaleMode', 'Loader', 'LoaderContext', 'LoaderInfo', 'LoadVars', 'LocalConnection',
                'Locale', 'Math', 'Matrix', 'MemoryError', 'Microphone', 'MorphShape', 'Mouse', 'MouseEvent',
                'MovieClip', 'MovieClipLoader', 'Namespace', 'NetConnection', 'NetStatusEvent',
                'NetStream', 'NewObjectSample', 'Number', 'Object', 'ObjectEncoding', 'PixelSnapping',
                'Point', 'PrintJob', 'PrintJobOptions', 'PrintJobOrientation', 'ProgressEvent', 'Proxy',
                'QName', 'RangeError', 'Rectangle', 'ReferenceError', 'RegExp', 'Responder', 'Sample',
                'Scene', 'ScriptTimeoutError', 'Security', 'SecurityDomain', 'SecurityError',
                'SecurityErrorEvent', 'SecurityPanel', 'Selection', 'Shape', 'SharedObject',
                'SharedObjectFlushStatus', 'SimpleButton', 'Socket', 'Sound', 'SoundChannel',
                'SoundLoaderContext', 'SoundMixer', 'SoundTransform', 'SpreadMethod', 'Sprite',
                'StackFrame', 'StackOverflowError', 'Stage', 'StageAlign', 'StageDisplayState',
                'StageQuality', 'StageScaleMode', 'StaticText', 'StatusEvent', 'String', 'StyleSheet',
                'SWFVersion', 'SyncEvent', 'SyntaxError', 'System', 'TextColorType', 'TextField',
                'TextFieldAutoSize', 'TextFieldType', 'TextFormat', 'TextFormatAlign',
                'TextLineMetrics', 'TextRenderer', 'TextSnapshot', 'Timer', 'TimerEvent', 'Transform',
                'TypeError', 'uint', 'URIError', 'URLLoader', 'URLLoaderDataFormat', 'URLRequest',
                'URLRequestHeader', 'URLRequestMethod', 'URLStream', 'URLVariabeles', 'VerifyError',
                'Video', 'XML', 'XMLDocument', 'XMLList', 'XMLNode', 'XMLNodeType', 'XMLSocket',
                'XMLUI'), suffix=r'\b'),
             Name.Builtin),
            (words((
                'decodeURI', 'decodeURIComponent', 'encodeURI', 'escape', 'eval', 'isFinite', 'isNaN',
                'isXMLName', 'clearInterval', 'fscommand', 'getTimer', 'getURL', 'getVersion',
                'parseFloat', 'parseInt', 'setInterval', 'trace', 'updateAfterEvent',
                'unescape'), suffix=r'\b'),
             Name.Function),
            (r'[$a-zA-Z_]\w*', Name.Other),
            (r'[0-9][0-9]*\.[0-9]+([eE][0-9]+)?[fd]?', Number.Float),
            (r'0x[0-9a-f]+', Number.Hex),
            (r'[0-9]+', Number.Integer),
            (r'"(\\\\|\\"|[^"])*"', String.Double),
            (r"'(\\\\|\\'|[^'])*'", String.Single),
        ]
    }


class ActionScript3Lexer(RegexLexer):
    """
    For ActionScript 3 source code.

    .. versionadded:: 0.11
    """

    name = 'ActionScript 3'
    aliases = ['as3', 'actionscript3']
    filenames = ['*.as']
    mimetypes = ['application/x-actionscript3', 'text/x-actionscript3',
                 'text/actionscript3']

    identifier = r'[$a-zA-Z_]\w*'
    typeidentifier = identifier + r'(?:\.<\w+>)?'

    flags = re.DOTALL | re.MULTILINE
    tokens = {
        'root': [
            (r'\s+', Text),
            (r'(function\s+)(' + identifier + r')(\s*)(\()',
             bygroups(Keyword.Declaration, Name.Function, Text, Operator),
             'funcparams'),
            (r'(var|const)(\s+)(' + identifier + r')(\s*)(:)(\s*)(' +
             typeidentifier + r')',
             bygroups(Keyword.Declaration, Text, Name, Text, Punctuation, Text,
                      Keyword.Type)),
            (r'(import|package)(\s+)((?:' + identifier + r'|\.)+)(\s*)',
             bygroups(Keyword, Text, Name.Namespace, Text)),
            (r'(new)(\s+)(' + typeidentifier + r')(\s*)(\()',
             bygroups(Keyword, Text, Keyword.Type, Text, Operator)),
            (r'//.*?\n', Comment.Single),
            (r'/\*.*?\*/', Comment.Multiline),
            (r'/(\\\\|\\/|[^\n])*/[gisx]*', String.Regex),
            (r'(\.)(' + identifier + r')', bygroups(Operator, Name.Attribute)),
            (r'(case|default|for|each|in|while|do|break|return|continue|if|else|'
             r'throw|try|catch|with|new|typeof|arguments|instanceof|this|'
             r'switch|import|include|as|is)\b',
             Keyword),
            (r'(class|public|final|internal|native|override|private|protected|'
             r'static|import|extends|implements|interface|intrinsic|return|super|'
             r'dynamic|function|const|get|namespace|package|set)\b',
             Keyword.Declaration),
            (r'(true|false|null|NaN|Infinity|-Infinity|undefined|void)\b',
             Keyword.Constant),
            (r'(decodeURI|decodeURIComponent|encodeURI|escape|eval|isFinite|isNaN|'
             r'isXMLName|clearInterval|fscommand|getTimer|getURL|getVersion|'
             r'isFinite|parseFloat|parseInt|setInterval|trace|updateAfterEvent|'
             r'unescape)\b', Name.Function),
            (identifier, Name),
            (r'[0-9][0-9]*\.[0-9]+([eE][0-9]+)?[fd]?', Number.Float),
            (r'0x[0-9a-f]+', Number.Hex),
            (r'[0-9]+', Number.Integer),
            (r'"(\\\\|\\"|[^"])*"', String.Double),
            (r"'(\\\\|\\'|[^'])*'", String.Single),
            (r'[~^*!%&<>|+=:;,/?\\{}\[\]().-]+', Operator),
        ],
        'funcparams': [
            (r'\s+', Text),
            (r'(\s*)(\.\.\.)?(' + identifier + r')(\s*)(:)(\s*)(' +
             typeidentifier + r'|\*)(\s*)',
             bygroups(Text, Punctuation, Name, Text, Operator, Text,
                      Keyword.Type, Text), 'defval'),
            (r'\)', Operator, 'type')
        ],
        'type': [
            (r'(\s*)(:)(\s*)(' + typeidentifier + r'|\*)',
             bygroups(Text, Operator, Text, Keyword.Type), '#pop:2'),
            (r'\s+', Text, '#pop:2'),
            default('#pop:2')
        ],
        'defval': [
            (r'(=)(\s*)([^(),]+)(\s*)(,?)',
             bygroups(Operator, Text, using(this), Text, Operator), '#pop'),
            (r',', Operator, '#pop'),
            default('#pop')
        ]
    }

    def analyse_text(text):
        if re.match(r'\w+\s*:\s*\w', text):
            return 0.3
        return 0


class MxmlLexer(RegexLexer):
    """
    For MXML markup.
    Nested AS3 in <script> tags is highlighted by the appropriate lexer.

    .. versionadded:: 1.1
    """
    flags = re.MULTILINE | re.DOTALL
    name = 'MXML'
    aliases = ['mxml']
    filenames = ['*.mxml']
    mimetimes = ['text/xml', 'application/xml']

    tokens = {
        'root': [
            ('[^<&]+', Text),
            (r'&\S*?;', Name.Entity),
            (r'(\<\!\[CDATA\[)(.*?)(\]\]\>)',
             bygroups(String, using(ActionScript3Lexer), String)),
            ('<!--', Comment, 'comment'),
            (r'<\?.*?\?>', Comment.Preproc),
            ('<![^>]*>', Comment.Preproc),
            (r'<\s*[\w:.-]+', Name.Tag, 'tag'),
            (r'<\s*/\s*[\w:.-]+\s*>', Name.Tag),
        ],
        'comment': [
            ('[^-]+', Comment),
            ('-->', Comment, '#pop'),
            ('-', Comment),
        ],
        'tag': [
            (r'\s+', Text),
            (r'[\w.:-]+\s*=', Name.Attribute, 'attr'),
            (r'/?\s*>', Name.Tag, '#pop'),
        ],
        'attr': [
            (r'\s+', Text),
            ('".*?"', String, '#pop'),
            ("'.*?'", String, '#pop'),
            (r'[^\s>]+', String, '#pop'),
        ],
    }
