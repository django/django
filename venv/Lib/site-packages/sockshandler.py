#!/usr/bin/env python
"""
SocksiPy + urllib2 handler

version: 0.3
author: e<e@tr0ll.in>

This module provides a Handler which you can use with urllib2 to allow it to tunnel your connection through a socks.sockssocket socket, with out monkey patching the original socket...
"""
import socket
import ssl

try:
    import urllib2
    import httplib
except ImportError: # Python 3
    import urllib.request as urllib2
    import http.client as httplib

import socks # $ pip install PySocks

def merge_dict(a, b):
    d = a.copy()
    d.update(b)
    return d

def is_ip(s):
    try:
        if ':' in s:
            socket.inet_pton(socket.AF_INET6, s)
        elif '.' in s:
            socket.inet_aton(s)
        else:
            return False
    except:
        return False
    else:
        return True

socks4_no_rdns = set()

class SocksiPyConnection(httplib.HTTPConnection):
    def __init__(self, proxytype, proxyaddr, proxyport=None, rdns=True, username=None, password=None, *args, **kwargs):
        self.proxyargs = (proxytype, proxyaddr, proxyport, rdns, username, password)
        httplib.HTTPConnection.__init__(self, *args, **kwargs)

    def connect(self):
        (proxytype, proxyaddr, proxyport, rdns, username, password) = self.proxyargs
        rdns = rdns and proxyaddr not in socks4_no_rdns
        while True:
            try:
                sock = socks.create_connection(
                    (self.host, self.port), self.timeout, None,
                    proxytype, proxyaddr, proxyport, rdns, username, password,
                    ((socket.IPPROTO_TCP, socket.TCP_NODELAY, 1),))
                break
            except socks.SOCKS4Error as e:
                if rdns and "0x5b" in str(e) and not is_ip(self.host):
                    # Maybe a SOCKS4 server that doesn't support remote resolving
                    # Let's try again
                    rdns = False
                    socks4_no_rdns.add(proxyaddr)
                else:
                    raise
        self.sock = sock

class SocksiPyConnectionS(httplib.HTTPSConnection):
    def __init__(self, proxytype, proxyaddr, proxyport=None, rdns=True, username=None, password=None, *args, **kwargs):
        self.proxyargs = (proxytype, proxyaddr, proxyport, rdns, username, password)
        httplib.HTTPSConnection.__init__(self, *args, **kwargs)

    def connect(self):
        SocksiPyConnection.connect(self)
        self.sock = self._context.wrap_socket(self.sock, server_hostname=self.host)
        if not self._context.check_hostname and self._check_hostname:
            try:
                ssl.match_hostname(self.sock.getpeercert(), self.host)
            except Exception:
                self.sock.shutdown(socket.SHUT_RDWR)
                self.sock.close()
                raise

class SocksiPyHandler(urllib2.HTTPHandler, urllib2.HTTPSHandler):
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kw = kwargs
        urllib2.HTTPHandler.__init__(self)

    def http_open(self, req):
        def build(host, port=None, timeout=0, **kwargs):
            kw = merge_dict(self.kw, kwargs)
            conn = SocksiPyConnection(*self.args, host=host, port=port, timeout=timeout, **kw)
            return conn
        return self.do_open(build, req)

    def https_open(self, req):
        def build(host, port=None, timeout=0, **kwargs):
            kw = merge_dict(self.kw, kwargs)
            conn = SocksiPyConnectionS(*self.args, host=host, port=port, timeout=timeout, **kw)
            return conn
        return self.do_open(build, req)

if __name__ == "__main__":
    import sys
    try:
        port = int(sys.argv[1])
    except (ValueError, IndexError):
        port = 9050
    opener = urllib2.build_opener(SocksiPyHandler(socks.PROXY_TYPE_SOCKS5, "localhost", port))
    print("HTTP: " + opener.open("http://httpbin.org/ip").read().decode())
    print("HTTPS: " + opener.open("https://httpbin.org/ip").read().decode())
