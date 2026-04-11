# $Id: urischemes.py 10272 2025-12-14 13:20:59Z milde $
# Author: David Goodger <goodger@python.org>
# Copyright: This module has been placed in the public domain.

"""
`schemes` is a dictionary with lowercase URI addressing schemes as
keys and descriptions as values. It was compiled from the index at
http://www.iana.org/assignments/uri-schemes (revised 2005-11-28)
and an older list at https://www.w3.org/Addressing/schemes.html.
"""

# Many values are blank and should be filled in with useful descriptions.

schemes: dict[str, str] = {
      'about': 'provides information on Navigator',
      'acap': 'Application Configuration Access Protocol; RFC 2244',
      'addbook': "To add vCard entries to Communicator's Address Book",
      'afp': 'Apple Filing Protocol',
      'afs': 'Andrew File System global file names',
      'aim': 'AOL Instant Messenger',
      'callto': 'for NetMeeting links',
      'castanet': 'Castanet Tuner URLs for Netcaster',
      'chttp': 'cached HTTP supported by RealPlayer',
      'cid': 'content identifier; RFC 2392',
      'crid': 'TV-Anytime Content Reference Identifier; RFC 4078',
      'data': 'allows inclusion of small data items as "immediate" data; '
              'RFC 2397',
      'dav': 'Distributed Authoring and Versioning Protocol; RFC 2518',
      'dict': 'dictionary service protocol; RFC 2229',
      'dns': 'Domain Name System resources',
      'eid': 'External ID; non-URL data; general escape mechanism to allow '
             'access to information for applications that are too '
             'specialized to justify their own schemes',
      'fax': 'a connection to a terminal that can handle telefaxes '
             '(facsimiles); RFC 2806',
      'feed': 'NetNewsWire feed',
      'file': 'Host-specific file names; RFC 1738',
      'finger': 'Querying user information using the Finger protocol',
      'freenet': '',
      'ftp': 'File Transfer Protocol; RFC 1738',
      'go': 'go; RFC 3368',
      'gopher': 'The Gopher Protocol',
      'gsm-sms': 'Global System for Mobile Communications Short Message '
                 'Service',
      'h323': 'video (audiovisual) communication on local area networks; '
              'RFC 3508',
      'h324': 'video and audio communications over low bitrate connections '
              'such as POTS modem connections',
      'hdl': 'CNRI handle system',
      'hnews': 'an HTTP-tunneling variant of the NNTP news protocol',
      'http': 'Hypertext Transfer Protocol; RFC 2616',
      'https': 'HTTP over SSL; RFC 2818',
      'hydra': 'SubEthaEdit URI. '
               'See http://www.codingmonkeys.de/subethaedit.',
      'iioploc': 'Internet Inter-ORB Protocol Location?',
      'ilu': 'Inter-Language Unification',
      'im': 'Instant Messaging; RFC 3860',
      'imap': 'Internet Message Access Protocol; RFC 2192',
      'info': 'Information Assets with Identifiers in Public Namespaces',
      'ior': 'CORBA interoperable object reference',
      'ipp': 'Internet Printing Protocol; RFC 3510',
      'irc': 'Internet Relay Chat',
      'iris.beep': 'iris.beep; RFC 3983',
      'iseek': 'See www.ambrosiasw.com;  a little util for OS X.',
      'jar': 'Java archive',
      'javascript': 'JavaScript code; '
                    'evaluates the expression after the colon',
      'jdbc': 'JDBC connection URI.',
      'ldap': 'Lightweight Directory Access Protocol',
      'lifn': '',
      'livescript': '',
      'lrq': '',
      'mailbox': 'Mail folder access',
      'mailserver': 'Access to data available from mail servers',
      'mailto': 'Electronic mail address; RFC 2368',
      'md5': '',
      'mid': 'message identifier; RFC 2392',
      'mocha': '',
      'modem': 'a connection to a terminal that can handle incoming data '
               'calls; RFC 2806',
      'mtqp': 'Message Tracking Query Protocol; RFC 3887',
      'mupdate': 'Mailbox Update (MUPDATE) Protocol; RFC 3656',
      'news': 'USENET news; RFC 1738',
      'nfs': 'Network File System protocol; RFC 2224',
      'nntp': 'USENET news using NNTP access; RFC 1738',
      'opaquelocktoken': 'RFC 2518',
      'phone': '',
      'pop': 'Post Office Protocol; RFC 2384',
      'pop3': 'Post Office Protocol v3',
      'pres': 'Presence; RFC 3859',
      'printer': '',
      'prospero': 'Prospero Directory Service; RFC 4157',
      'rdar': 'URLs found in Darwin source '
              '(http://www.opensource.apple.com/darwinsource/).',
      'res': '',
      'rtsp': 'real time streaming protocol; RFC 2326',
      'rvp': '',
      'rwhois': '',
      'rx': 'Remote Execution',
      'sdp': '',
      'service': 'service location; RFC 2609',
      'shttp': 'secure hypertext transfer protocol (OBSOLETE)',
      'sip': 'Session Initiation Protocol; RFC 3261',
      'sips': 'secure session intitiaion protocol; RFC 3261',
      'smb': 'SAMBA filesystems.',
      'snews': 'For NNTP postings via SSL',
      'snmp': 'Simple Network Management Protocol; RFC 4088',
      'soap.beep': 'RFC 3288',
      'soap.beeps': 'RFC 3288',
      'ssh': 'Reference to interactive sessions via ssh.',
      't120': 'real time data conferencing (audiographics)',
      'tag': 'RFC 4151',
      'tcp': '',
      'tel': 'a connection to a terminal that handles normal voice '
             'telephone calls, a voice mailbox or another voice messaging '
             'system or a service that can be operated using DTMF tones; '
             'RFC 3966.',
      'telephone': 'telephone',
      'telnet': 'Reference to interactive sessions; RFC 4248',
      'tftp': 'Trivial File Transfer Protocol; RFC 3617',
      'tip': 'Transaction Internet Protocol; RFC 2371',
      'tn3270': 'Interactive 3270 emulation sessions',
      'tv': '',
      'urn': 'Uniform Resource Name; RFC 2141',
      'uuid': '',
      'vemmi': 'versatile multimedia interface; RFC 2122',
      'videotex': 'videotex (historical)',
      'view-source': 'displays HTML code that was generated with JavaScript',
      'wais': 'Wide Area Information Servers; RFC 4156',
      'whodp': '',
      'whois++': 'Distributed directory service.',
      'x-man-page': 'Opens man page in Terminal.app on OS X '
                    '(see macosxhints.com)',
      'xmlrpc.beep': 'RFC 3529',
      'xmlrpc.beeps': 'RFC 3529',
      'z39.50r': 'Z39.50 Retrieval; RFC 2056',
      'z39.50s': 'Z39.50 Session; RFC 2056',
      }
