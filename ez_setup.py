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

DEFAULT_VERSION = "0.5a12"
DEFAULT_URL     = "http://www.python.org/packages/source/s/setuptools/"

import sys, os





















def use_setuptools(
    version=DEFAULT_VERSION, download_base=DEFAULT_URL, to_dir=os.curdir
):
    """Automatically find/download setuptools and make it available on sys.path

    `version` should be a valid setuptools version number that is available
    as an egg for download under the `download_base` URL (which should end with
    a '/').  `to_dir` is the directory where setuptools will be downloaded, if
    it is not already available.

    If an older version of setuptools is installed, this will print a message
    to ``sys.stderr`` and raise SystemExit in an attempt to abort the calling
    script.
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
        egg = download_setuptools(version, download_base, to_dir)
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
    version=DEFAULT_VERSION, download_base=DEFAULT_URL, to_dir=os.curdir
):
    """Download setuptools from a specified location and return its filename

    `version` should be a valid setuptools version number that is available
    as an egg for download under the `download_base` URL (which should end
    with a '/'). `to_dir` is the directory where the egg will be downloaded.
    """
    import urllib2, shutil
    egg_name = "setuptools-%s-py%s.egg" % (version,sys.version[:3])
    url = download_base + egg_name + '.zip'  # XXX
    saveto = os.path.join(to_dir, egg_name)
    src = dst = None

    if not os.path.exists(saveto):  # Avoid repeated downloads
        try:
            from distutils import log
            log.warn("Downloading %s", url)
            src = urllib2.urlopen(url)
            # Read/write all in one block, so we don't create a corrupt file
            # if the download is interrupted.
            data = src.read()
            dst = open(saveto,"wb")
            dst.write(data)
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
            egg = download_setuptools(version, to_dir=tmpdir)
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
        main(list(argv)+[download_setuptools()])
        sys.exit(0) # try to force an exit
    else:
        if argv:
            from setuptools.command.easy_install import main
            main(argv)
        else:
            print "Setuptools version",version,"or greater has been installed."
            print '(Run "ez_setup.py -U setuptools" to reinstall or upgrade.)'
if __name__=='__main__':
    main(sys.argv[1:])

