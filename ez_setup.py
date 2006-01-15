#!python
"""Bootstrap setuptools installation

If you want to use setuptools in your package's setup.py, just include this
file in the same directory with it, and add this to the top of your setup.py::

    from ez_setup import use_setuptools
    use_setuptools()

If you want to require a specific version of setuptools, set a download
mirror, or use an alternate download directory, you can do so by supplying
the appropriate options to ``use_setuptools()``.

This file can also be run as a script to install or upgrade setuptools.
"""
import sys
DEFAULT_VERSION = "0.6a9"
DEFAULT_URL     = "http://cheeseshop.python.org/packages/%s/s/setuptools/" % sys.version[:3]

md5_data = {
    'setuptools-0.5a13-py2.3.egg': '85edcf0ef39bab66e130d3f38f578c86',
    'setuptools-0.5a13-py2.4.egg': 'ede4be600e3890e06d4ee5e0148e092a',
    'setuptools-0.6a1-py2.3.egg': 'ee819a13b924d9696b0d6ca6d1c5833d',
    'setuptools-0.6a1-py2.4.egg': '8256b5f1cd9e348ea6877b5ddd56257d',
    'setuptools-0.6a2-py2.3.egg': 'b98da449da411267c37a738f0ab625ba',
    'setuptools-0.6a2-py2.4.egg': 'be5b88bc30aed63fdefd2683be135c3b',
    'setuptools-0.6a3-py2.3.egg': 'ee0e325de78f23aab79d33106dc2a8c8',
    'setuptools-0.6a3-py2.4.egg': 'd95453d525a456d6c23e7a5eea89a063',
    'setuptools-0.6a4-py2.3.egg': 'e958cbed4623bbf47dd1f268b99d7784',
    'setuptools-0.6a4-py2.4.egg': '7f33c3ac2ef1296f0ab4fac1de4767d8',
    'setuptools-0.6a5-py2.3.egg': '748408389c49bcd2d84f6ae0b01695b1',
    'setuptools-0.6a5-py2.4.egg': '999bacde623f4284bfb3ea77941d2627',
    'setuptools-0.6a6-py2.3.egg': '7858139f06ed0600b0d9383f36aca24c',
    'setuptools-0.6a6-py2.4.egg': 'c10d20d29acebce0dc76219dc578d058',
    'setuptools-0.6a7-py2.3.egg': 'cfc4125ddb95c07f9500adc5d6abef6f',
    'setuptools-0.6a7-py2.4.egg': 'c6d62dab4461f71aed943caea89e6f20',
    'setuptools-0.6a8-py2.3.egg': '2f18eaaa3f544f5543ead4a68f3b2e1a',
    'setuptools-0.6a8-py2.4.egg': '799018f2894f14c9f8bcb2b34e69b391',
    'setuptools-0.6a9-py2.3.egg': '8e438ad70438b07b0d8f82cae42b278f',
    'setuptools-0.6a9-py2.4.egg': '8f6e01fc12fb1cd006dc0d6c04327ec1',
}

import sys, os

def _validate_md5(egg_name, data):
    if egg_name in md5_data:
        from md5 import md5
        digest = md5(data).hexdigest()
        if digest != md5_data[egg_name]:
            print >>sys.stderr, (
                "md5 validation of %s failed!  (Possible download problem?)"
                % egg_name
            )
            sys.exit(2)
    return data    


def use_setuptools(
    version=DEFAULT_VERSION, download_base=DEFAULT_URL, to_dir=os.curdir,
    download_delay=15
):
    """Automatically find/download setuptools and make it available on sys.path

    `version` should be a valid setuptools version number that is available
    as an egg for download under the `download_base` URL (which should end with
    a '/').  `to_dir` is the directory where setuptools will be downloaded, if
    it is not already available.  If `download_delay` is specified, it should
    be the number of seconds that will be paused before initiating a download,
    should one be required.  If an older version of setuptools is installed,
    this routine will print a message to ``sys.stderr`` and raise SystemExit in
    an attempt to abort the calling script.  
    """
    try:
        import setuptools
        if setuptools.__version__ == '0.0.1':
            print >>sys.stderr, (
            "You have an obsolete version of setuptools installed.  Please\n"
            "remove it from your system entirely before rerunning this script."
            )
            sys.exit(2)
    except ImportError:
        egg = download_setuptools(version, download_base, to_dir, download_delay)
        sys.path.insert(0, egg)
        import setuptools; setuptools.bootstrap_install_from = egg

    import pkg_resources
    try:
        pkg_resources.require("setuptools>="+version)

    except pkg_resources.VersionConflict:
        # XXX could we install in a subprocess here?
        print >>sys.stderr, (
            "The required version of setuptools (>=%s) is not available, and\n"
            "can't be installed while this script is running. Please install\n"
            " a more recent version first."
        ) % version
        sys.exit(2)

def download_setuptools(
    version=DEFAULT_VERSION, download_base=DEFAULT_URL, to_dir=os.curdir,
    delay = 15
):
    """Download setuptools from a specified location and return its filename

    `version` should be a valid setuptools version number that is available
    as an egg for download under the `download_base` URL (which should end
    with a '/'). `to_dir` is the directory where the egg will be downloaded.
    `delay` is the number of seconds to pause before an actual download attempt.
    """
    import urllib2, shutil
    egg_name = "setuptools-%s-py%s.egg" % (version,sys.version[:3])
    url = download_base + egg_name
    saveto = os.path.join(to_dir, egg_name)
    src = dst = None
    if not os.path.exists(saveto):  # Avoid repeated downloads
        try:
            from distutils import log
            if delay:
                log.warn("""
---------------------------------------------------------------------------
This script requires setuptools version %s to run (even to display
help).  I will attempt to download it for you (from
%s), but
you may need to enable firewall access for this script first.
I will start the download in %d seconds.
---------------------------------------------------------------------------""",
                    version, download_base, delay
                ); from time import sleep; sleep(delay)
            log.warn("Downloading %s", url)
            src = urllib2.urlopen(url)
            # Read/write all in one block, so we don't create a corrupt file
            # if the download is interrupted.
            data = _validate_md5(egg_name, src.read())
            dst = open(saveto,"wb"); dst.write(data)
        finally:
            if src: src.close()
            if dst: dst.close()
    return os.path.realpath(saveto)

def main(argv, version=DEFAULT_VERSION):
    """Install or upgrade setuptools and EasyInstall"""

    try:
        import setuptools
    except ImportError:
        import tempfile, shutil
        tmpdir = tempfile.mkdtemp(prefix="easy_install-")
        try:
            egg = download_setuptools(version, to_dir=tmpdir, delay=0)
            sys.path.insert(0,egg)
            from setuptools.command.easy_install import main
            main(list(argv)+[egg])
        finally:
            shutil.rmtree(tmpdir)
    else:
        if setuptools.__version__ == '0.0.1':
            # tell the user to uninstall obsolete version
            use_setuptools(version)

    req = "setuptools>="+version
    import pkg_resources
    try:
        pkg_resources.require(req)
    except pkg_resources.VersionConflict:
        try:
            from setuptools.command.easy_install import main
        except ImportError:
            from easy_install import main
        main(list(argv)+[download_setuptools(delay=0)])
        sys.exit(0) # try to force an exit
    else:
        if argv:
            from setuptools.command.easy_install import main
            main(argv)
        else:
            print "Setuptools version",version,"or greater has been installed."
            print '(Run "ez_setup.py -U setuptools" to reinstall or upgrade.)'


            
def update_md5(filenames):
    """Update our built-in md5 registry"""

    import re
    from md5 import md5

    for name in filenames:
        base = os.path.basename(name)
        f = open(name,'rb')       
        md5_data[base] = md5(f.read()).hexdigest()
        f.close()

    data = ["    %r: %r,\n" % it for it in md5_data.items()]
    data.sort()
    repl = "".join(data)

    import inspect
    srcfile = inspect.getsourcefile(sys.modules[__name__])
    f = open(srcfile, 'rb'); src = f.read(); f.close()

    match = re.search("\nmd5_data = {\n([^}]+)}", src)
    if not match:
        print >>sys.stderr, "Internal error!"
        sys.exit(2)

    src = src[:match.start(1)] + repl + src[match.end(1):]
    f = open(srcfile,'w')
    f.write(src)
    f.close()


if __name__=='__main__':
    if len(sys.argv)>2 and sys.argv[1]=='--md5update':
        update_md5(sys.argv[2:])
    else:
        main(sys.argv[1:])





