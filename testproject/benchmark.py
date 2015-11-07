import random

from autobahn.twisted.websocket import WebSocketClientProtocol, \
    WebSocketClientFactory


NUM_CONNECTIONS = 100
PER_SECOND = 10
stats = {}


class MyClientProtocol(WebSocketClientProtocol):

    num_messages = 5
    message_gap = 1

    def onConnect(self, response):
        self.sent = 0
        self.received = 0
        self.corrupted = 0
        self.out_of_order = 0
        self.fingerprint = "".join(random.choice("abcdefghijklmnopqrstuvwxyz") for i in range(16))
        stats[self.fingerprint] = {}

    def onOpen(self):
        def hello():
            self.sendMessage("%s:%s" % (self.sent, self.fingerprint))
            self.sent += 1
            if self.sent < self.num_messages:
                self.factory.reactor.callLater(1, hello)
            else:
                self.sendClose()
        hello()

    def onMessage(self, payload, isBinary):
        num, fingerprint = payload.split(":")
        if fingerprint != self.fingerprint:
            self.corrupted += 1
        if num != self.received:
            self.out_of_order += 1
        self.received += 1

    def onClose(self, wasClean, code, reason):
        stats[self.fingerprint] = {
            "sent": self.sent,
            "received": self.received,
            "corrupted": self.corrupted,
            "out_of_order": self.out_of_order,
        }


def spawn_connections():
    if len(stats) >= NUM_CONNECTIONS:
        return
    for i in range(PER_SECOND):
        reactor.connectTCP("127.0.0.1", 9000, factory)
    reactor.callLater(1, spawn_connections)


def print_progress():
    open_protocols = len([x for x in stats.values() if not x])
    print "%s open, %s total" % (
        open_protocols,
        len(stats),
    )
    reactor.callLater(1, print_progress)
    if open_protocols == 0 and len(stats) >= NUM_CONNECTIONS:
        reactor.stop()
        print_stats()


def print_stats():
    num_incomplete = len([x for x in stats.values() if x['sent'] != x['received']])
    num_corruption = len([x for x in stats.values() if x['corrupted']])
    num_out_of_order = len([x for x in stats.values() if x['out_of_order']])
    print "-------"
    print "Sockets opened: %s" % len(stats)
    print "Incomplete sockets: %s (%.2f%%)" % (num_incomplete, (float(num_incomplete) / len(stats))*100)
    print "Corrupt sockets: %s (%.2f%%)" % (num_corruption, (float(num_corruption) / len(stats))*100)
    print "Out of order sockets: %s (%.2f%%)" % (num_out_of_order, (float(num_out_of_order) / len(stats))*100)


if __name__ == '__main__':

    import sys

    from twisted.python import log
    from twisted.internet import reactor

#    log.startLogging(sys.stdout)

    factory = WebSocketClientFactory(u"ws://127.0.0.1:9000", debug=False)
    factory.protocol = MyClientProtocol

    reactor.callLater(1, spawn_connections)
    reactor.callLater(1, print_progress)

    reactor.run()
