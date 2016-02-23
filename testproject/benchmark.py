from __future__ import unicode_literals

import time
import random
from autobahn.twisted.websocket import WebSocketClientProtocol, \
    WebSocketClientFactory


stats = {}


class MyClientProtocol(WebSocketClientProtocol):

    num_messages = 5
    message_gap = 1

    def onConnect(self, response):
        self.opened = time.time()
        self.sent = 0
        self.last_send = None
        self.received = 0
        self.corrupted = 0
        self.out_of_order = 0
        self.latencies = []
        self.fingerprint = "".join(random.choice("abcdefghijklmnopqrstuvwxyz") for i in range(16))
        stats[self.fingerprint] = {}

    def onOpen(self):
        def hello():
            if self.last_send is None:
                if self.sent >= self.num_messages:
                    self.sendClose()
                    return
                self.sendMessage(("%s:%s" % (self.sent, self.fingerprint)).encode("ascii"))
                self.last_send = time.time()
                self.sent += 1
            else:
                # Wait for receipt of ping
                pass
            self.factory.reactor.callLater(1, hello)
        hello()

    def onMessage(self, payload, isBinary):
        num, fingerprint = payload.decode("ascii").split(":")
        if fingerprint != self.fingerprint:
            self.corrupted += 1
        if int(num) != self.received:
            self.out_of_order += 1
        self.received += 1
        self.latencies.append(time.time() - self.last_send)
        self.last_send = None

    def onClose(self, wasClean, code, reason):
        if hasattr(self, "sent"):
            stats[self.fingerprint] = {
                "sent": self.sent,
                "received": self.received,
                "corrupted": self.corrupted,
                "out_of_order": self.out_of_order,
                "connect": True,
            }
        else:
            self.fingerprint = "".join(random.choice("abcdefghijklmnopqrstuvwxyz") for i in range(16))
            stats[self.fingerprint] = {
                "sent": 0,
                "received": 0,
                "corrupted": 0,
                "out_of_order": 0,
                "connect": False,
            }



class Benchmarker(object):
    """
    Performs benchmarks against WebSockets.
    """

    def __init__(self, url, num, rate):
        self.url = url
        self.num = num
        self.rate = rate
        self.factory = WebSocketClientFactory(
            args.url,
            debug=False,
        )
        self.factory.protocol = MyClientProtocol

    def loop(self):
        self.spawn_connections()
        self.print_progress()
        reactor.callLater(1, self.loop)

    def spawn_connections(self):
        if len(stats) >= self.num:
            return
        for i in range(self.rate):
            # TODO: Look at URL
            reactor.connectTCP("127.0.0.1", 8000, self.factory)

    def print_progress(self):
        open_protocols = len([x for x in stats.values() if not x])
        print("%s open, %s total" % (
            open_protocols,
            len(stats),
        ))
        if open_protocols == 0 and len(stats) >= self.num:
            print("Reached %s open connections, quitting" % self.num)
            reactor.stop()
            self.print_stats()

    def print_stats(self):
        num_incomplete = len([x for x in stats.values() if x['sent'] != x['received']])
        num_corruption = len([x for x in stats.values() if x['corrupted']])
        num_out_of_order = len([x for x in stats.values() if x['out_of_order']])
        num_failed = len([x for x in stats.values() if not x['connect']])
        print("-------")
        print("Sockets opened: %s" % len(stats))
        print("Incomplete sockets: %s (%.2f%%)" % (num_incomplete, (float(num_incomplete) / len(stats))*100))
        print("Corrupt sockets: %s (%.2f%%)" % (num_corruption, (float(num_corruption) / len(stats))*100))
        print("Out of order sockets: %s (%.2f%%)" % (num_out_of_order, (float(num_out_of_order) / len(stats))*100))
        print("Failed to connect: %s (%.2f%%)" % (num_failed, (float(num_failed) / len(stats))*100))


if __name__ == '__main__':

    import sys
    import argparse

    from twisted.python import log
    from twisted.internet import reactor

#    log.startLogging(sys.stdout)

    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("-n", "--num", type=int, default=100)
    parser.add_argument("-r", "--rate", type=int, default=10)
    args = parser.parse_args()

    benchmarker = Benchmarker(
        url=args.url,
        num=args.num,
        rate=args.rate,
    )
    benchmarker.loop()
    reactor.run()
