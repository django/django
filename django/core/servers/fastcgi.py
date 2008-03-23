"""
FastCGI (or SCGI, or AJP1.3 ...) server that implements the WSGI protocol.

Uses the flup python package: http://www.saddi.com/software/flup/

This is a adaptation of the flup package to add FastCGI server support
to run Django apps from Web servers that support the FastCGI protocol.
This module can be run standalone or from the django-admin / manage.py
scripts using the "runfcgi" directive.

Run with the extra option "help" for a list of additional options you can
pass to this server.
"""

import sys, os

__version__ = "0.1"
__all__ = ["runfastcgi"]

FASTCGI_HELP = r"""
  Run this project as a fastcgi (or some other protocol supported
  by flup) application. To do this, the flup package from
  http://www.saddi.com/software/flup/ is required.

   runfcgi [options] [fcgi settings]

Optional Fcgi settings: (setting=value)
  protocol=PROTOCOL    fcgi, scgi, ajp, ... (default fcgi)
  host=HOSTNAME        hostname to listen on..
  port=PORTNUM         port to listen on.
  socket=FILE          UNIX socket to listen on.
  method=IMPL          prefork or threaded (default prefork)
  maxrequests=NUMBER   number of requests a child handles before it is 
                       killed and a new child is forked (0 = no limit).
  maxspare=NUMBER      max number of spare processes / threads
  minspare=NUMBER      min number of spare processes / threads.
  maxchildren=NUMBER   hard limit number of processes / threads
  daemonize=BOOL       whether to detach from terminal.
  pidfile=FILE         write the spawned process-id to this file.
  workdir=DIRECTORY    change to this directory when daemonizing.
  outlog=FILE          write stdout to this file.
  errlog=FILE          write stderr to this file.

Examples:
  Run a "standard" fastcgi process on a file-descriptor
  (for webservers which spawn your processes for you)
    $ manage.py runfcgi method=threaded

  Run a scgi server on a TCP host/port
    $ manage.py runfcgi protocol=scgi method=prefork host=127.0.0.1 port=8025

  Run a fastcgi server on a UNIX domain socket (posix platforms only)
    $ manage.py runfcgi method=prefork socket=/tmp/fcgi.sock

  Run a fastCGI as a daemon and write the spawned PID in a file
    $ manage.py runfcgi socket=/tmp/fcgi.sock method=prefork \
        daemonize=true pidfile=/var/run/django-fcgi.pid

"""

FASTCGI_OPTIONS = {
    'protocol': 'fcgi',
    'host': None,
    'port': None,
    'socket': None,
    'method': 'fork',
    'daemonize': None,
    'workdir': '/',
    'pidfile': None,
    'maxspare': 5,
    'minspare': 2,
    'maxchildren': 50,
    'maxrequests': 0,
    'outlog': None,
    'errlog': None,
}

def fastcgi_help(message=None):
    print FASTCGI_HELP
    if message:
        print message
    return False

def runfastcgi(argset=[], **kwargs):
    options = FASTCGI_OPTIONS.copy()
    options.update(kwargs)
    for x in argset:
        if "=" in x:
            k, v = x.split('=', 1)
        else:
            k, v = x, True
        options[k.lower()] = v

    if "help" in options:
        return fastcgi_help()

    try:
        import flup
    except ImportError, e:
        print >> sys.stderr, "ERROR: %s" % e
        print >> sys.stderr, "  Unable to load the flup package.  In order to run django"
        print >> sys.stderr, "  as a FastCGI application, you will need to get flup from"
        print >> sys.stderr, "  http://www.saddi.com/software/flup/   If you've already"
        print >> sys.stderr, "  installed flup, then make sure you have it in your PYTHONPATH."
        return False

    flup_module = 'server.' + options['protocol']

    if options['method'] in ('prefork', 'fork'):
        wsgi_opts = {
            'maxSpare': int(options["maxspare"]),
            'minSpare': int(options["minspare"]),
            'maxChildren': int(options["maxchildren"]),
            'maxRequests': int(options["maxrequests"]), 
        }
        flup_module += '_fork'
    elif options['method'] in ('thread', 'threaded'):
        wsgi_opts = {
            'maxSpare': int(options["maxspare"]),
            'minSpare': int(options["minspare"]),
            'maxThreads': int(options["maxchildren"]),
        }
    else:
        return fastcgi_help("ERROR: Implementation must be one of prefork or thread.")

    wsgi_opts['debug'] = False # Turn off flup tracebacks

    try:
        WSGIServer = getattr(__import__('flup.' + flup_module, '', '', flup_module), 'WSGIServer')
    except:
        print "Can't import flup." + flup_module
        return False

    # Prep up and go
    from django.core.handlers.wsgi import WSGIHandler

    if options["host"] and options["port"] and not options["socket"]:
        wsgi_opts['bindAddress'] = (options["host"], int(options["port"]))
    elif options["socket"] and not options["host"] and not options["port"]:
        wsgi_opts['bindAddress'] = options["socket"]
    elif not options["socket"] and not options["host"] and not options["port"]:
        wsgi_opts['bindAddress'] = None
    else:
        return fastcgi_help("Invalid combination of host, port, socket.")

    if options["daemonize"] is None:
        # Default to daemonizing if we're running on a socket/named pipe.
        daemonize = (wsgi_opts['bindAddress'] is not None)
    else:
        if options["daemonize"].lower() in ('true', 'yes', 't'):
            daemonize = True
        elif options["daemonize"].lower() in ('false', 'no', 'f'):
            daemonize = False
        else:
            return fastcgi_help("ERROR: Invalid option for daemonize parameter.")

    daemon_kwargs = {}
    if options['outlog']:
        daemon_kwargs['out_log'] = options['outlog']
    if options['errlog']:
        daemon_kwargs['err_log'] = options['errlog']

    if daemonize:
        from django.utils.daemonize import become_daemon
        become_daemon(our_home_dir=options["workdir"], **daemon_kwargs)

    if options["pidfile"]:
        fp = open(options["pidfile"], "w")
        fp.write("%d\n" % os.getpid())
        fp.close()

    WSGIServer(WSGIHandler(), **wsgi_opts).run()

if __name__ == '__main__':
    runfastcgi(sys.argv[1:])
