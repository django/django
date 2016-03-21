from __future__ import unicode_literals

import time
import random
import statistics
from autobahn.twisted.websocket import WebSocketClientProtocol, \
    WebSocketClientFactory


stats = {}


class MyClientProtocol(WebSocketClientProtocol):

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
                if self.sent >= self.factory.num_messages:
                    self.sendClose()
                    return
                self.last_send = time.time()
                self.sendMessage(("%s:%s" % (self.sent, self.fingerprint)).encode("ascii"))
                self.sent += 1
            else:
                # Wait for receipt of ping
                pass
            self.factory.reactor.callLater(1.0 / self.factory.message_rate, hello)
        hello()

    def onMessage(self, payload, isBinary):
        # Detect receive-before-send
        if self.last_send is None:
            self.corrupted += 1
            print("CRITICAL: Socket %s received before sending: %s" % (self.fingerprint, payload))
            return
        num, fingerprint = payload.decode("ascii").split(":")
        if fingerprint != self.fingerprint:
            self.corrupted += 1
        try:
            if int(num) != self.received:
                self.out_of_order += 1
        except ValueError:
            self.corrupted += 1
        self.latencies.append(time.time() - self.last_send)
        self.received += 1
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

    def __init__(self, url, num, concurrency, rate, messages):
        self.url = url
        self.num = num
        self.concurrency = concurrency
        self.rate = rate
        self.messages = messages
        self.factory = WebSocketClientFactory(
            args.url,
        )
        self.factory.protocol = MyClientProtocol
        self.factory.num_messages = self.messages
        self.factory.message_rate = self.rate

    def loop(self):
        self.spawn_loop()
        self.progress_loop()

    def spawn_loop(self):
        self.spawn_connections()
        reactor.callLater(0.01, self.spawn_loop)

    def progress_loop(self):
        self.print_progress()
        reactor.callLater(1, self.progress_loop)

    def spawn_connections(self):
        # Stop spawning if we did the right total number
        max_to_spawn = self.num - len(stats)
        if max_to_spawn <= 0:
            return
        # Decode connection args
        host, port = self.url.split("://")[1].split(":")
        port = int(port)
        # Only spawn enough to get up to concurrency
        open_protocols = len([x for x in stats.values() if not x])
        to_spawn = min(max(self.concurrency - open_protocols, 0), max_to_spawn)
        for _ in range(to_spawn):
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
        latency_95 = self.percentile(latencies, 0.95)
        latency_99 = self.percentile(latencies, 0.99)
        # Print results
        print("-------")
        print("Sockets opened: %s" % len(stats))
        print("Latency stats: Mean %.3fs  Median %.3fs  Stdev %.3f  95%% %.3fs  95%% %.3fs" % (
            latency_mean,
            latency_median,
            latency_stdev,
            latency_95,
            latency_99,
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
    parser.add_argument("-n", "--num", type=int, default=100, help="Total number of sockets to open")
    parser.add_argument("-c", "--concurrency", type=int, default=10, help="Number of sockets to open at once")
    parser.add_argument("-r", "--rate", type=float, default=1, help="Number of messages to send per socket per second")
    parser.add_argument("-m", "--messages", type=int, default=5, help="Number of messages to send per socket before close")
    args = parser.parse_args()

    benchmarker = Benchmarker(
        url=args.url,
        num=args.num,
        concurrency=args.concurrency,
        rate=args.rate,
        messages=args.messages,
    )
    benchmarker.loop()
    reactor.run()
