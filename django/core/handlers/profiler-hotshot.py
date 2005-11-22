import hotshot, time, os
from django.core.handlers.modpython import ModPythonHandler

PROFILE_DATA_DIR = "/var/log/cmsprofile"

def handler(req):
    '''
    Handler that uses hotshot to store profile data.

    Stores profile data in PROFILE_DATA_DIR.  Since hotshot has no way (that I
    know of) to append profile data to a single file, each request gets its own
    profile.  The file names are in the format <url>.<n>.prof where <url> is
    the request path with "/" replaced by ".", and <n> is a timestamp with
    microseconds to prevent overwriting files.

    Use the gather_profile_stats.py script to gather these individual request
    profiles into aggregated profiles by request path.
    '''
    profname = "%s.%.3f.prof" % (req.uri.strip("/").replace('/', '.'), time.time())
    profname = os.path.join(PROFILE_DATA_DIR, profname)
    prof = hotshot.Profile(profname)
    return prof.runcall(ModPythonHandler(), req)
