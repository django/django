# -*- coding: utf-8 -*-
"""
    pygments.lexers.configs
    ~~~~~~~~~~~~~~~~~~~~~~~

    Lexers for configuration file formats.

    :copyright: Copyright 2006-2017 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import RegexLexer, default, words, bygroups, include, using
from pygments.token import Text, Comment, Operator, Keyword, Name, String, \
    Number, Punctuation, Whitespace, Literal
from pygments.lexers.shell import BashLexer
from pygments.lexers.data import JsonLexer

__all__ = ['IniLexer', 'RegeditLexer', 'PropertiesLexer', 'KconfigLexer',
           'Cfengine3Lexer', 'ApacheConfLexer', 'SquidConfLexer',
           'NginxConfLexer', 'LighttpdConfLexer', 'DockerLexer',
           'TerraformLexer', 'TermcapLexer', 'TerminfoLexer',
           'PkgConfigLexer', 'PacmanConfLexer']


class IniLexer(RegexLexer):
    """
    Lexer for configuration files in INI style.
    """

    name = 'INI'
    aliases = ['ini', 'cfg', 'dosini']
    filenames = ['*.ini', '*.cfg', '*.inf']
    mimetypes = ['text/x-ini', 'text/inf']

    tokens = {
        'root': [
            (r'\s+', Text),
            (r'[;#].*', Comment.Single),
            (r'\[.*?\]$', Keyword),
            (r'(.*?)([ \t]*)(=)([ \t]*)(.*(?:\n[ \t].+)*)',
             bygroups(Name.Attribute, Text, Operator, Text, String)),
            # standalone option, supported by some INI parsers
            (r'(.+?)$', Name.Attribute),
        ],
    }

    def analyse_text(text):
        npos = text.find('\n')
        if npos < 3:
            return False
        return text[0] == '[' and text[npos-1] == ']'


class RegeditLexer(RegexLexer):
    """
    Lexer for `Windows Registry
    <http://en.wikipedia.org/wiki/Windows_Registry#.REG_files>`_ files produced
    by regedit.

    .. versionadded:: 1.6
    """

    name = 'reg'
    aliases = ['registry']
    filenames = ['*.reg']
    mimetypes = ['text/x-windows-registry']

    tokens = {
        'root': [
            (r'Windows Registry Editor.*', Text),
            (r'\s+', Text),
            (r'[;#].*', Comment.Single),
            (r'(\[)(-?)(HKEY_[A-Z_]+)(.*?\])$',
             bygroups(Keyword, Operator, Name.Builtin, Keyword)),
            # String keys, which obey somewhat normal escaping
            (r'("(?:\\"|\\\\|[^"])+")([ \t]*)(=)([ \t]*)',
             bygroups(Name.Attribute, Text, Operator, Text),
             'value'),
            # Bare keys (includes @)
            (r'(.*?)([ \t]*)(=)([ \t]*)',
             bygroups(Name.Attribute, Text, Operator, Text),
             'value'),
        ],
        'value': [
            (r'-', Operator, '#pop'),  # delete value
            (r'(dword|hex(?:\([0-9a-fA-F]\))?)(:)([0-9a-fA-F,]+)',
             bygroups(Name.Variable, Punctuation, Number), '#pop'),
            # As far as I know, .reg files do not support line continuation.
            (r'.+', String, '#pop'),
            default('#pop'),
        ]
    }

    def analyse_text(text):
        return text.startswith('Windows Registry Editor')


class PropertiesLexer(RegexLexer):
    """
    Lexer for configuration files in Java's properties format.

    Note: trailing whitespace counts as part of the value as per spec

    .. versionadded:: 1.4
    """

    name = 'Properties'
    aliases = ['properties', 'jproperties']
    filenames = ['*.properties']
    mimetypes = ['text/x-java-properties']

    tokens = {
        'root': [
            (r'^(\w+)([ \t])(\w+\s*)$', bygroups(Name.Attribute, Text, String)),
            (r'^\w+(\\[ \t]\w*)*$', Name.Attribute),
            (r'(^ *)([#!].*)', bygroups(Text, Comment)),
            # More controversial comments
            (r'(^ *)((?:;|//).*)', bygroups(Text, Comment)),
            (r'(.*?)([ \t]*)([=:])([ \t]*)(.*(?:(?<=\\)\n.*)*)',
             bygroups(Name.Attribute, Text, Operator, Text, String)),
            (r'\s', Text),
        ],
    }


def _rx_indent(level):
    # Kconfig *always* interprets a tab as 8 spaces, so this is the default.
    # Edit this if you are in an environment where KconfigLexer gets expanded
    # input (tabs expanded to spaces) and the expansion tab width is != 8,
    # e.g. in connection with Trac (trac.ini, [mimeviewer], tab_width).
    # Value range here is 2 <= {tab_width} <= 8.
    tab_width = 8
    # Regex matching a given indentation {level}, assuming that indentation is
    # a multiple of {tab_width}. In other cases there might be problems.
    if tab_width == 2:
        space_repeat = '+'
    else:
        space_repeat = '{1,%d}' % (tab_width - 1)
    if level == 1:
        level_repeat = ''
    else:
        level_repeat = '{%s}' % level
    return r'(?:\t| %s\t| {%s})%s.*\n' % (space_repeat, tab_width, level_repeat)


class KconfigLexer(RegexLexer):
    """
    For Linux-style Kconfig files.

    .. versionadded:: 1.6
    """

    name = 'Kconfig'
    aliases = ['kconfig', 'menuconfig', 'linux-config', 'kernel-config']
    # Adjust this if new kconfig file names appear in your environment
    filenames = ['Kconfig', '*Config.in*', 'external.in*',
                 'standard-modules.in']
    mimetypes = ['text/x-kconfig']
    # No re.MULTILINE, indentation-aware help text needs line-by-line handling
    flags = 0

    def call_indent(level):
        # If indentation >= {level} is detected, enter state 'indent{level}'
        return (_rx_indent(level), String.Doc, 'indent%s' % level)

    def do_indent(level):
        # Print paragraphs of indentation level >= {level} as String.Doc,
        # ignoring blank lines. Then return to 'root' state.
        return [
            (_rx_indent(level), String.Doc),
            (r'\s*\n', Text),
            default('#pop:2')
        ]

    tokens = {
        'root': [
            (r'\s+', Text),
            (r'#.*?\n', Comment.Single),
            (words((
                'mainmenu', 'config', 'menuconfig', 'choice', 'endchoice',
                'comment', 'menu', 'endmenu', 'visible if', 'if', 'endif',
                'source', 'prompt', 'select', 'depends on', 'default',
                'range', 'option'), suffix=r'\b'),
             Keyword),
            (r'(---help---|help)[\t ]*\n', Keyword, 'help'),
            (r'(bool|tristate|string|hex|int|defconfig_list|modules|env)\b',
             Name.Builtin),
            (r'[!=&|]', Operator),
            (r'[()]', Punctuation),
            (r'[0-9]+', Number.Integer),
            (r"'(''|[^'])*'", String.Single),
            (r'"(""|[^"])*"', String.Double),
            (r'\S+', Text),
        ],
        # Help text is indented, multi-line and ends when a lower indentation
        # level is detected.
        'help': [
            # Skip blank lines after help token, if any
            (r'\s*\n', Text),
            # Determine the first help line's indentation level heuristically(!).
            # Attention: this is not perfect, but works for 99% of "normal"
            # indentation schemes up to a max. indentation level of 7.
            call_indent(7),
            call_indent(6),
            call_indent(5),
            call_indent(4),
            call_indent(3),
            call_indent(2),
            call_indent(1),
            default('#pop'),  # for incomplete help sections without text
        ],
        # Handle text for indentation levels 7 to 1
        'indent7': do_indent(7),
        'indent6': do_indent(6),
        'indent5': do_indent(5),
        'indent4': do_indent(4),
        'indent3': do_indent(3),
        'indent2': do_indent(2),
        'indent1': do_indent(1),
    }


class Cfengine3Lexer(RegexLexer):
    """
    Lexer for `CFEngine3 <http://cfengine.org>`_ policy files.

    .. versionadded:: 1.5
    """

    name = 'CFEngine3'
    aliases = ['cfengine3', 'cf3']
    filenames = ['*.cf']
    mimetypes = []

    tokens = {
        'root': [
            (r'#.*?\n', Comment),
            (r'(body)(\s+)(\S+)(\s+)(control)',
             bygroups(Keyword, Text, Keyword, Text, Keyword)),
            (r'(body|bundle)(\s+)(\S+)(\s+)(\w+)(\()',
             bygroups(Keyword, Text, Keyword, Text, Name.Function, Punctuation),
             'arglist'),
            (r'(body|bundle)(\s+)(\S+)(\s+)(\w+)',
             bygroups(Keyword, Text, Keyword, Text, Name.Function)),
            (r'(")([^"]+)(")(\s+)(string|slist|int|real)(\s*)(=>)(\s*)',
             bygroups(Punctuation, Name.Variable, Punctuation,
                      Text, Keyword.Type, Text, Operator, Text)),
            (r'(\S+)(\s*)(=>)(\s*)',
             bygroups(Keyword.Reserved, Text, Operator, Text)),
            (r'"', String, 'string'),
            (r'(\w+)(\()', bygroups(Name.Function, Punctuation)),
            (r'([\w.!&|()]+)(::)', bygroups(Name.Class, Punctuation)),
            (r'(\w+)(:)', bygroups(Keyword.Declaration, Punctuation)),
            (r'@[{(][^)}]+[})]', Name.Variable),
            (r'[(){},;]', Punctuation),
            (r'=>', Operator),
            (r'->', Operator),
            (r'\d+\.\d+', Number.Float),
            (r'\d+', Number.Integer),
            (r'\w+', Name.Function),
            (r'\s+', Text),
        ],
        'string': [
            (r'\$[{(]', String.Interpol, 'interpol'),
            (r'\\.', String.Escape),
            (r'"', String, '#pop'),
            (r'\n', String),
            (r'.', String),
        ],
        'interpol': [
            (r'\$[{(]', String.Interpol, '#push'),
            (r'[})]', String.Interpol, '#pop'),
            (r'[^${()}]+', String.Interpol),
        ],
        'arglist': [
            (r'\)', Punctuation, '#pop'),
            (r',', Punctuation),
            (r'\w+', Name.Variable),
            (r'\s+', Text),
        ],
    }


class ApacheConfLexer(RegexLexer):
    """
    Lexer for configuration files following the Apache config file
    format.

    .. versionadded:: 0.6
    """

    name = 'ApacheConf'
    aliases = ['apacheconf', 'aconf', 'apache']
    filenames = ['.htaccess', 'apache.conf', 'apache2.conf']
    mimetypes = ['text/x-apacheconf']
    flags = re.MULTILINE | re.IGNORECASE

    tokens = {
        'root': [
            (r'\s+', Text),
            (r'(#.*?)$', Comment),
            (r'(<[^\s>]+)(?:(\s+)(.*?))?(>)',
             bygroups(Name.Tag, Text, String, Name.Tag)),
            (r'([a-z]\w*)(\s+)',
             bygroups(Name.Builtin, Text), 'value'),
            (r'\.+', Text),
        ],
        'value': [
            (r'\\\n', Text),
            (r'$', Text, '#pop'),
            (r'\\', Text),
            (r'[^\S\n]+', Text),
            (r'\d+\.\d+\.\d+\.\d+(?:/\d+)?', Number),
            (r'\d+', Number),
            (r'/([a-z0-9][\w./-]+)', String.Other),
            (r'(on|off|none|any|all|double|email|dns|min|minimal|'
             r'os|productonly|full|emerg|alert|crit|error|warn|'
             r'notice|info|debug|registry|script|inetd|standalone|'
             r'user|group)\b', Keyword),
            (r'"([^"\\]*(?:\\.[^"\\]*)*)"', String.Double),
            (r'[^\s"\\]+', Text)
        ],
    }


class SquidConfLexer(RegexLexer):
    """
    Lexer for `squid <http://www.squid-cache.org/>`_ configuration files.

    .. versionadded:: 0.9
    """

    name = 'SquidConf'
    aliases = ['squidconf', 'squid.conf', 'squid']
    filenames = ['squid.conf']
    mimetypes = ['text/x-squidconf']
    flags = re.IGNORECASE

    keywords = (
        "access_log", "acl", "always_direct", "announce_host",
        "announce_period", "announce_port", "announce_to", "anonymize_headers",
        "append_domain", "as_whois_server", "auth_param_basic",
        "authenticate_children", "authenticate_program", "authenticate_ttl",
        "broken_posts", "buffered_logs", "cache_access_log", "cache_announce",
        "cache_dir", "cache_dns_program", "cache_effective_group",
        "cache_effective_user", "cache_host", "cache_host_acl",
        "cache_host_domain", "cache_log", "cache_mem", "cache_mem_high",
        "cache_mem_low", "cache_mgr", "cachemgr_passwd", "cache_peer",
        "cache_peer_access", "cahce_replacement_policy", "cache_stoplist",
        "cache_stoplist_pattern", "cache_store_log", "cache_swap",
        "cache_swap_high", "cache_swap_log", "cache_swap_low", "client_db",
        "client_lifetime", "client_netmask", "connect_timeout", "coredump_dir",
        "dead_peer_timeout", "debug_options", "delay_access", "delay_class",
        "delay_initial_bucket_level", "delay_parameters", "delay_pools",
        "deny_info", "dns_children", "dns_defnames", "dns_nameservers",
        "dns_testnames", "emulate_httpd_log", "err_html_text",
        "fake_user_agent", "firewall_ip", "forwarded_for", "forward_snmpd_port",
        "fqdncache_size", "ftpget_options", "ftpget_program", "ftp_list_width",
        "ftp_passive", "ftp_user", "half_closed_clients", "header_access",
        "header_replace", "hierarchy_stoplist", "high_response_time_warning",
        "high_page_fault_warning", "hosts_file", "htcp_port", "http_access",
        "http_anonymizer", "httpd_accel", "httpd_accel_host",
        "httpd_accel_port", "httpd_accel_uses_host_header",
        "httpd_accel_with_proxy", "http_port", "http_reply_access",
        "icp_access", "icp_hit_stale", "icp_port", "icp_query_timeout",
        "ident_lookup", "ident_lookup_access", "ident_timeout",
        "incoming_http_average", "incoming_icp_average", "inside_firewall",
        "ipcache_high", "ipcache_low", "ipcache_size", "local_domain",
        "local_ip", "logfile_rotate", "log_fqdn", "log_icp_queries",
        "log_mime_hdrs", "maximum_object_size", "maximum_single_addr_tries",
        "mcast_groups", "mcast_icp_query_timeout", "mcast_miss_addr",
        "mcast_miss_encode_key", "mcast_miss_port", "memory_pools",
        "memory_pools_limit", "memory_replacement_policy", "mime_table",
        "min_http_poll_cnt", "min_icp_poll_cnt", "minimum_direct_hops",
        "minimum_object_size", "minimum_retry_timeout", "miss_access",
        "negative_dns_ttl", "negative_ttl", "neighbor_timeout",
        "neighbor_type_domain", "netdb_high", "netdb_low", "netdb_ping_period",
        "netdb_ping_rate", "never_direct", "no_cache", "passthrough_proxy",
        "pconn_timeout", "pid_filename", "pinger_program", "positive_dns_ttl",
        "prefer_direct", "proxy_auth", "proxy_auth_realm", "query_icmp",
        "quick_abort", "quick_abort_max", "quick_abort_min",
        "quick_abort_pct", "range_offset_limit", "read_timeout",
        "redirect_children", "redirect_program",
        "redirect_rewrites_host_header", "reference_age",
        "refresh_pattern", "reload_into_ims", "request_body_max_size",
        "request_size", "request_timeout", "shutdown_lifetime",
        "single_parent_bypass", "siteselect_timeout", "snmp_access",
        "snmp_incoming_address", "snmp_port", "source_ping", "ssl_proxy",
        "store_avg_object_size", "store_objects_per_bucket",
        "strip_query_terms", "swap_level1_dirs", "swap_level2_dirs",
        "tcp_incoming_address", "tcp_outgoing_address", "tcp_recv_bufsize",
        "test_reachability", "udp_hit_obj", "udp_hit_obj_size",
        "udp_incoming_address", "udp_outgoing_address", "unique_hostname",
        "unlinkd_program", "uri_whitespace", "useragent_log",
        "visible_hostname", "wais_relay", "wais_relay_host", "wais_relay_port",
    )

    opts = (
        "proxy-only", "weight", "ttl", "no-query", "default", "round-robin",
        "multicast-responder", "on", "off", "all", "deny", "allow", "via",
        "parent", "no-digest", "heap", "lru", "realm", "children", "q1", "q2",
        "credentialsttl", "none", "disable", "offline_toggle", "diskd",
    )

    actions = (
        "shutdown", "info", "parameter", "server_list", "client_list",
        r'squid.conf',
    )

    actions_stats = (
        "objects", "vm_objects", "utilization", "ipcache", "fqdncache", "dns",
        "redirector", "io", "reply_headers", "filedescriptors", "netdb",
    )

    actions_log = ("status", "enable", "disable", "clear")

    acls = (
        "url_regex", "urlpath_regex", "referer_regex", "port", "proto",
        "req_mime_type", "rep_mime_type", "method", "browser", "user", "src",
        "dst", "time", "dstdomain", "ident", "snmp_community",
    )

    ip_re = (
        r'(?:(?:(?:[3-9]\d?|2(?:5[0-5]|[0-4]?\d)?|1\d{0,2}|0x0*[0-9a-f]{1,2}|'
        r'0+[1-3]?[0-7]{0,2})(?:\.(?:[3-9]\d?|2(?:5[0-5]|[0-4]?\d)?|1\d{0,2}|'
        r'0x0*[0-9a-f]{1,2}|0+[1-3]?[0-7]{0,2})){3})|(?!.*::.*::)(?:(?!:)|'
        r':(?=:))(?:[0-9a-f]{0,4}(?:(?<=::)|(?<!::):)){6}(?:[0-9a-f]{0,4}'
        r'(?:(?<=::)|(?<!::):)[0-9a-f]{0,4}(?:(?<=::)|(?<!:)|(?<=:)(?<!::):)|'
        r'(?:25[0-4]|2[0-4]\d|1\d\d|[1-9]?\d)(?:\.(?:25[0-4]|2[0-4]\d|1\d\d|'
        r'[1-9]?\d)){3}))'
    )

    tokens = {
        'root': [
            (r'\s+', Whitespace),
            (r'#', Comment, 'comment'),
            (words(keywords, prefix=r'\b', suffix=r'\b'), Keyword),
            (words(opts, prefix=r'\b', suffix=r'\b'), Name.Constant),
            # Actions
            (words(actions, prefix=r'\b', suffix=r'\b'), String),
            (words(actions_stats, prefix=r'stats/', suffix=r'\b'), String),
            (words(actions_log, prefix=r'log/', suffix=r'='), String),
            (words(acls, prefix=r'\b', suffix=r'\b'), Keyword),
            (ip_re + r'(?:/(?:' + ip_re + r'|\b\d+\b))?', Number.Float),
            (r'(?:\b\d+\b(?:-\b\d+|%)?)', Number),
            (r'\S+', Text),
        ],
        'comment': [
            (r'\s*TAG:.*', String.Escape, '#pop'),
            (r'.+', Comment, '#pop'),
            default('#pop'),
        ],
    }


class NginxConfLexer(RegexLexer):
    """
    Lexer for `Nginx <http://nginx.net/>`_ configuration files.

    .. versionadded:: 0.11
    """
    name = 'Nginx configuration file'
    aliases = ['nginx']
    filenames = ['nginx.conf']
    mimetypes = ['text/x-nginx-conf']

    tokens = {
        'root': [
            (r'(include)(\s+)([^\s;]+)', bygroups(Keyword, Text, Name)),
            (r'[^\s;#]+', Keyword, 'stmt'),
            include('base'),
        ],
        'block': [
            (r'\}', Punctuation, '#pop:2'),
            (r'[^\s;#]+', Keyword.Namespace, 'stmt'),
            include('base'),
        ],
        'stmt': [
            (r'\{', Punctuation, 'block'),
            (r';', Punctuation, '#pop'),
            include('base'),
        ],
        'base': [
            (r'#.*\n', Comment.Single),
            (r'on|off', Name.Constant),
            (r'\$[^\s;#()]+', Name.Variable),
            (r'([a-z0-9.-]+)(:)([0-9]+)',
             bygroups(Name, Punctuation, Number.Integer)),
            (r'[a-z-]+/[a-z-+]+', String),  # mimetype
            # (r'[a-zA-Z._-]+', Keyword),
            (r'[0-9]+[km]?\b', Number.Integer),
            (r'(~)(\s*)([^\s{]+)', bygroups(Punctuation, Text, String.Regex)),
            (r'[:=~]', Punctuation),
            (r'[^\s;#{}$]+', String),  # catch all
            (r'/[^\s;#]*', Name),  # pathname
            (r'\s+', Text),
            (r'[$;]', Text),  # leftover characters
        ],
    }


class LighttpdConfLexer(RegexLexer):
    """
    Lexer for `Lighttpd <http://lighttpd.net/>`_ configuration files.

    .. versionadded:: 0.11
    """
    name = 'Lighttpd configuration file'
    aliases = ['lighty', 'lighttpd']
    filenames = []
    mimetypes = ['text/x-lighttpd-conf']

    tokens = {
        'root': [
            (r'#.*\n', Comment.Single),
            (r'/\S*', Name),  # pathname
            (r'[a-zA-Z._-]+', Keyword),
            (r'\d+\.\d+\.\d+\.\d+(?:/\d+)?', Number),
            (r'[0-9]+', Number),
            (r'=>|=~|\+=|==|=|\+', Operator),
            (r'\$[A-Z]+', Name.Builtin),
            (r'[(){}\[\],]', Punctuation),
            (r'"([^"\\]*(?:\\.[^"\\]*)*)"', String.Double),
            (r'\s+', Text),
        ],

    }


class DockerLexer(RegexLexer):
    """
    Lexer for `Docker <http://docker.io>`_ configuration files.

    .. versionadded:: 2.0
    """
    name = 'Docker'
    aliases = ['docker', 'dockerfile']
    filenames = ['Dockerfile', '*.docker']
    mimetypes = ['text/x-dockerfile-config']

    _keywords = (r'(?:FROM|MAINTAINER|EXPOSE|WORKDIR|USER|STOPSIGNAL)')
    _bash_keywords = (r'(?:RUN|CMD|ENTRYPOINT|ENV|ARG|LABEL|ADD|COPY)')
    _lb = r'(?:\s*\\?\s*)' # dockerfile line break regex
    flags = re.IGNORECASE | re.MULTILINE

    tokens = {
        'root': [
            (r'#.*', Comment),
            (r'(ONBUILD)(%s)' % (_lb,), bygroups(Keyword, using(BashLexer))),
            (r'(HEALTHCHECK)((%s--\w+=\w+%s)*)' % (_lb, _lb),
                bygroups(Keyword, using(BashLexer))),
            (r'(VOLUME|ENTRYPOINT|CMD|SHELL)(%s)(\[.*?\])' % (_lb,),
                bygroups(Keyword, using(BashLexer), using(JsonLexer))),
            (r'(LABEL|ENV|ARG)((%s\w+=\w+%s)*)' % (_lb, _lb),
                bygroups(Keyword, using(BashLexer))),
            (r'(%s|VOLUME)\b(.*)' % (_keywords), bygroups(Keyword, String)),
            (r'(%s)' % (_bash_keywords,), Keyword),
            (r'(.*\\\n)*.+', using(BashLexer)),
        ]
    }


class TerraformLexer(RegexLexer):
    """
    Lexer for `terraformi .tf files <https://www.terraform.io/>`_.

    .. versionadded:: 2.1
    """

    name = 'Terraform'
    aliases = ['terraform', 'tf']
    filenames = ['*.tf']
    mimetypes = ['application/x-tf', 'application/x-terraform']

    tokens = {
        'root': [
             include('string'),
             include('punctuation'),
             include('curly'),
             include('basic'),
             include('whitespace'),
             (r'[0-9]+', Number),
        ],
        'basic': [
             (words(('true', 'false'), prefix=r'\b', suffix=r'\b'), Keyword.Type),
             (r'\s*/\*', Comment.Multiline, 'comment'),
             (r'\s*#.*\n', Comment.Single),
             (r'(.*?)(\s*)(=)', bygroups(Name.Attribute, Text, Operator)),
             (words(('variable', 'resource', 'provider', 'provisioner', 'module'),
                    prefix=r'\b', suffix=r'\b'), Keyword.Reserved, 'function'),
             (words(('ingress', 'egress', 'listener', 'default', 'connection', 'alias'),
                    prefix=r'\b', suffix=r'\b'), Keyword.Declaration),
             (r'\$\{', String.Interpol, 'var_builtin'),
        ],
        'function': [
             (r'(\s+)(".*")(\s+)', bygroups(Text, String, Text)),
             include('punctuation'),
             include('curly'),
        ],
        'var_builtin': [
            (r'\$\{', String.Interpol, '#push'),
            (words(('concat', 'file', 'join', 'lookup', 'element'),
                   prefix=r'\b', suffix=r'\b'), Name.Builtin),
            include('string'),
            include('punctuation'),
            (r'\s+', Text),
            (r'\}', String.Interpol, '#pop'),
        ],
        'string': [
            (r'(".*")', bygroups(String.Double)),
        ],
        'punctuation': [
            (r'[\[\](),.]', Punctuation),
        ],
        # Keep this seperate from punctuation - we sometimes want to use different
        # Tokens for { }
        'curly': [
            (r'\{', Text.Punctuation),
            (r'\}', Text.Punctuation),
        ],
        'comment': [
            (r'[^*/]', Comment.Multiline),
            (r'/\*', Comment.Multiline, '#push'),
            (r'\*/', Comment.Multiline, '#pop'),
            (r'[*/]', Comment.Multiline)
        ],
        'whitespace': [
            (r'\n', Text),
            (r'\s+', Text),
            (r'\\\n', Text),
        ],
    }


class TermcapLexer(RegexLexer):
    """
    Lexer for termcap database source.

    This is very simple and minimal.

    .. versionadded:: 2.1
    """
    name = 'Termcap'
    aliases = ['termcap']
    filenames = ['termcap', 'termcap.src']
    mimetypes = []

    # NOTE:
    #   * multiline with trailing backslash
    #   * separator is ':'
    #   * to embed colon as data, we must use \072
    #   * space after separator is not allowed (mayve)
    tokens = {
        'root': [
            (r'^#.*$', Comment),
            (r'^[^\s#:|]+', Name.Tag, 'names'),
        ],
        'names': [
            (r'\n', Text, '#pop'),
            (r':', Punctuation, 'defs'),
            (r'\|', Punctuation),
            (r'[^:|]+', Name.Attribute),
        ],
        'defs': [
            (r'\\\n[ \t]*', Text),
            (r'\n[ \t]*', Text, '#pop:2'),
            (r'(#)([0-9]+)', bygroups(Operator, Number)),
            (r'=', Operator, 'data'),
            (r':', Punctuation),
            (r'[^\s:=#]+', Name.Class),
        ],
        'data': [
            (r'\\072', Literal),
            (r':', Punctuation, '#pop'),
            (r'[^:\\]+', Literal),  # for performance
            (r'.', Literal),
        ],
    }


class TerminfoLexer(RegexLexer):
    """
    Lexer for terminfo database source.

    This is very simple and minimal.

    .. versionadded:: 2.1
    """
    name = 'Terminfo'
    aliases = ['terminfo']
    filenames = ['terminfo', 'terminfo.src']
    mimetypes = []

    # NOTE:
    #   * multiline with leading whitespace
    #   * separator is ','
    #   * to embed comma as data, we can use \,
    #   * space after separator is allowed
    tokens = {
        'root': [
            (r'^#.*$', Comment),
            (r'^[^\s#,|]+', Name.Tag, 'names'),
        ],
        'names': [
            (r'\n', Text, '#pop'),
            (r'(,)([ \t]*)', bygroups(Punctuation, Text), 'defs'),
            (r'\|', Punctuation),
            (r'[^,|]+', Name.Attribute),
        ],
        'defs': [
            (r'\n[ \t]+', Text),
            (r'\n', Text, '#pop:2'),
            (r'(#)([0-9]+)', bygroups(Operator, Number)),
            (r'=', Operator, 'data'),
            (r'(,)([ \t]*)', bygroups(Punctuation, Text)),
            (r'[^\s,=#]+', Name.Class),
        ],
        'data': [
            (r'\\[,\\]', Literal),
            (r'(,)([ \t]*)', bygroups(Punctuation, Text), '#pop'),
            (r'[^\\,]+', Literal),  # for performance
            (r'.', Literal),
        ],
    }


class PkgConfigLexer(RegexLexer):
    """
    Lexer for `pkg-config
    <http://www.freedesktop.org/wiki/Software/pkg-config/>`_
    (see also `manual page <http://linux.die.net/man/1/pkg-config>`_).

    .. versionadded:: 2.1
    """

    name = 'PkgConfig'
    aliases = ['pkgconfig']
    filenames = ['*.pc']
    mimetypes = []

    tokens = {
        'root': [
            (r'#.*$', Comment.Single),

            # variable definitions
            (r'^(\w+)(=)', bygroups(Name.Attribute, Operator)),

            # keyword lines
            (r'^([\w.]+)(:)',
             bygroups(Name.Tag, Punctuation), 'spvalue'),

            # variable references
            include('interp'),

            # fallback
            (r'[^${}#=:\n.]+', Text),
            (r'.', Text),
        ],
        'interp': [
            # you can escape literal "$" as "$$"
            (r'\$\$', Text),

            # variable references
            (r'\$\{', String.Interpol, 'curly'),
        ],
        'curly': [
            (r'\}', String.Interpol, '#pop'),
            (r'\w+', Name.Attribute),
        ],
        'spvalue': [
            include('interp'),

            (r'#.*$', Comment.Single, '#pop'),
            (r'\n', Text, '#pop'),

            # fallback
            (r'[^${}#\n]+', Text),
            (r'.', Text),
        ],
    }


class PacmanConfLexer(RegexLexer):
    """
    Lexer for `pacman.conf
    <https://www.archlinux.org/pacman/pacman.conf.5.html>`_.

    Actually, IniLexer works almost fine for this format,
    but it yield error token. It is because pacman.conf has
    a form without assignment like:

        UseSyslog
        Color
        TotalDownload
        CheckSpace
        VerbosePkgLists

    These are flags to switch on.

    .. versionadded:: 2.1
    """

    name = 'PacmanConf'
    aliases = ['pacmanconf']
    filenames = ['pacman.conf']
    mimetypes = []

    tokens = {
        'root': [
            # comment
            (r'#.*$', Comment.Single),

            # section header
            (r'^\s*\[.*?\]\s*$', Keyword),

            # variable definitions
            # (Leading space is allowed...)
            (r'(\w+)(\s*)(=)',
             bygroups(Name.Attribute, Text, Operator)),

            # flags to on
            (r'^(\s*)(\w+)(\s*)$',
             bygroups(Text, Name.Attribute, Text)),

            # built-in special values
            (words((
                '$repo',  # repository
                '$arch',  # architecture
                '%o',     # outfile
                '%u',     # url
                ), suffix=r'\b'),
             Name.Variable),

            # fallback
            (r'.', Text),
        ],
    }
