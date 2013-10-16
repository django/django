"""URI utilities"""

# The IANA URI scheme lists have been produced with the following code:
#
#   import lxml.html, urllib
#   text = "".join(urllib.urlopen("https://www.iana.org/assignments/uri-schemes/uri-schemes.xhtml").readlines())
#   root = lxml.html.fromstring(text)
#   permanent_uri_schemes = [e.text for e in root.xpath("//table[@id='table-uri-schemes-1']//tbody//tr/*[1]")]
#   provisional_uri_schemes = [e.text for e in root.xpath("//table[@id='table-uri-schemes-2']//tbody//tr/*[1]")]
#   historical_uri_schemes = [e.text for e in root.xpath("//table[@id='table-uri-schemes-3']//tbody//tr/*[1]")]
#
# Last updated 2013-10-16:

IANA_PERMANENT_URI_SCHEMES = ['aaa', 'aaas', 'about', 'acap', 'acct', 'cap', 'cid', 'coap', 'coaps', 'crid', 'data', 'dav', 'dict', 'dns', 'file', 'ftp', 'geo', 'go', 'gopher', 'h323', 'http', 'https', 'iax', 'icap', 'im', 'imap', 'info', 'ipp', 'iris', 'iris.beep', 'iris.xpc', 'iris.xpcs', 'iris.lwz', 'jabber', 'ldap', 'mailto', 'mid', 'msrp', 'msrps', 'mtqp', 'mupdate', 'news', 'nfs', 'ni', 'nih', 'nntp', 'opaquelocktoken', 'pop', 'pres', 'reload', 'rtsp', 'service', 'session', 'shttp', 'sieve', 'sip', 'sips', 'sms', 'snmp', 'soap.beep', 'soap.beeps', 'stun', 'stuns', 'tag', 'tel', 'telnet', 'tftp', 'thismessage', 'tn3270', 'tip', 'turn', 'turns', 'tv', 'urn', 'vemmi', 'ws', 'wss', 'xcon', 'xcon-userid', 'xmlrpc.beep', 'xmlrpc.beeps', 'xmpp', 'z39.50r', 'z39.50s']
IANA_PROVISIONAL_URI_SCHEMES = ['adiumxtra', 'afp', 'afs', 'aim', 'apt', 'attachment', 'aw', 'beshare', 'bitcoin', 'bolo', 'callto', 'chrome', 'chrome-extension', 'com-eventbrite-attendee', 'content', 'cvs', 'dlna-playsingle', 'dlna-playcontainer', 'dtn', 'dvb', 'ed2k', 'facetime', 'feed', 'feedready', 'finger', 'fish', 'gg', 'git', 'gizmoproject', 'gtalk', 'hcp', 'icon', 'ipn', 'irc', 'irc6', 'ircs', 'itms', 'jar', 'jms', 'keyparc', 'lastfm', 'ldaps', 'magnet', 'maps', 'market', 'message', 'mms', 'ms-help', 'ms-settings-power', 'msnim', 'mumble', 'mvn', 'notes', 'oid', 'palm', 'paparazzi', 'pkcs11', 'platform', 'proxy', 'psyc', 'query', 'res', 'resource', 'rmi', 'rsync', 'rtmp', 'secondlife', 'sftp', 'sgn', 'skype', 'smb', 'soldat', 'spotify', 'ssh', 'steam', 'svn', 'teamspeak', 'things', 'udp', 'unreal', 'ut2004', 'ventrilo', 'view-source', 'webcal', 'wtai', 'wyciwyg', 'xfire', 'xri', 'ymsgr']
IANA_HISTORICAL_URI_SCHEMES = ['fax', 'mailserver', 'modem', 'pack', 'prospero', 'snews', 'videotex', 'wais', 'z39.50']

IANA_URI_SCHEMES = IANA_PERMANENT_URI_SCHEMES + IANA_PROVISIONAL_URI_SCHEMES + IANA_HISTORICAL_URI_SCHEMES
