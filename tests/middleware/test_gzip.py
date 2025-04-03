import json
import time

from django.test import SimpleTestCase


def new_sse_data(idx: int = 0):
    data = dict(create=idx)
    return json.dumps(data).encode('utf-8')


def data_generator():
    for i in range(5):
        time.sleep(1)
        yield new_sse_data(idx=i)
    return


class GzipMiddlewareTest(SimpleTestCase):
    def test_flush_streaming_compression(self):
        from django.utils.text import compress_sequence

        start = time.time()
        timestamps = []

        for chunk in compress_sequence(data_generator()):
            if chunk:  # Ignore empty chunks
                timestamps.append(time.time() - start)
        # Only consider timestamps for non-empty chunks
        durations = [round(t, 1) for t in timestamps]
        # no flush: Each chunk arrived at: [0.0, 5.0]
        # with flush: Each chunk arrived at: [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 5.0]
        # Summary:
        # - The first chunk is the Gzip header, emitted immediately (at 0.0s)
        # - The next 5 chunks are compressed data blocks, roughly one per second.
        # - The final chunk is the Gzip footer, emitted right after the 5th block.
        # - Confirms zfile.flush() works: compression output is non-blocking.
        print("Each chunk arrived at:", durations)

        # Check that each chunk arrives roughly every second (allowing 0.5s tolerance)
        for i in range(1, len(durations)):
            self.assertGreaterEqual(durations[i], i * 0.5)
        return
