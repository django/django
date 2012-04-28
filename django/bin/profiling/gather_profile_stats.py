#!/usr/bin/env python

"""
gather_profile_stats.py /path/to/dir/of/profiles

Note that the aggregated profiles must be read with pstats.Stats, not
hotshot.stats (the formats are incompatible)
"""

from hotshot import stats
import os
import pstats
import sys

def gather_stats(p):
    profiles = {}
    for f in os.listdir(p):
        if f.endswith('.agg.prof'):
            path = f[:-9]
            prof = pstats.Stats(os.path.join(p, f))
        elif f.endswith('.prof'):
            bits = f.split('.')
            path = ".".join(bits[:-3])
            prof = stats.load(os.path.join(p, f))
        else:
            continue
        print("Processing %s" % f)
        if path in profiles:
            profiles[path].add(prof)
        else:
            profiles[path] = prof
        os.unlink(os.path.join(p, f))
    for (path, prof) in profiles.items():
        prof.dump_stats(os.path.join(p, "%s.agg.prof" % path))
    
if __name__ == '__main__':
    gather_stats(sys.argv[1])
