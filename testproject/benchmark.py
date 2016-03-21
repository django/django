from __future__ import unicode_literals

import time
import random
import statistics
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
                "latencies": self.latencies,
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
        host, port = self.url.split("://")[1].split(":")
        for i in range(self.rate):
            # TODO: Look at URL
            reactor.connectTCP(host, port, self.factory)

    def print_progress(self):
        open_protocols = len([x for x in stats.values() if not x])
        print("%s open, %s total" % (
            open_protocols,
            len(stats),
        ))
        if open_protocols == 0 and len(stats) >= self.num:
            reactor.stop()
            self.print_stats()

    def percentile(self, values, fraction):
        """
        Returns a percentile value (e.g. fraction = 0.95 -> 95th percentile)
        """
        values = sorted(values)
        stopat = int(len(values) * fraction)
        if stopat == len(values):
            stopat -= 1
        return values[stopat]

    def print_stats(self):
        # Collect stats together
        latencies = []
        num_good = 0
        num_incomplete = 0
        num_failed = 0
        num_corruption = 0
        num_out_of_order = 0
        for entry in stats.values():
            latencies.extend(entry.get("latencies", []))
            if not entry['connect']:
                num_failed += 1
            elif entry['sent'] != entry['received']:
                num_incomplete += 1
            elif entry['corrupted']:
                num_corruption += 1
            elif entry['out_of_order']:
                num_out_of_order += 1
            else:
                num_good += 1
        # Some analysis on latencies
        latency_mean = statistics.mean(latencies)
        latency_median = statistics.median(latencies)
        latency_stdev = statistics.stdev(latencies)
        latency_5 = self.percentile(latencies, 0.05)
        latency_95 = self.percentile(latencies, 0.95)
        # Print results
        print("-------")
        print("Sockets opened: %s" % len(stats))
        print("Latency stats: Mean %.2fs  Median %.2fs  Stdev %.2f  5%% %.2fs  95%% %.2fs" % (
            latency_mean,
            latency_median,
            latency_stdev,
            latency_5,
            latency_95,
        ))
        print("Good sockets: %s (%.2f%%)" % (num_good, (float(num_good) / len(stats))*100))
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
