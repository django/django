Channels Test Project
=====================

This subdirectory contains benchmarking code and a companion Django project
that can be used to benchmark Channels for both HTTP and WebSocket performance.

Preparation:
~~~~~~~~~~~~

    Set up a Python 2.7 virtualenv however you do that and activate it.

    e.g. to create it right in the test directory (assuming python 2 is your system's default)::

        virtualenv channels-test-py27
        source channels-test-py27/bin/activate
        pip install -U -r requirements.txt

How to use with Docker:
~~~~~~~~~~~~~~~~~~~~~~~

    Build the docker image from Dockerfile, tag it `channels-test`::

        docker build -t channels-test .

    Run the server::

        docker-compose up -d

    The benchmark project will now be running on: http:{your-docker-ip}:80

    Test it by navigating to that address in a browser.  It should just say "OK".

    It is also running a WebSocket server at: ws://{your-docker-ip}:80

    Run the benchmark's help to show the parameters::

        python benchmark.py --help

    Let's just try a quick test with the default values from the parameter list::

        python benchmark.py ws://localhost:80

How to use with runserver:
~~~~~~~~~~~~~~~~~~~~~~~~~~

    You must have a local Redis server running on localhost:6739 for this to work!  If you happen
    to be running Docker, this can easily be done with::

        docker run -d --name redis_local -p 6379:6379 redis:alpine

    Just to make sure you're up to date with migrations, run::

        python manage.py migrate

    In one terminal window, run the server with::

        python manage.py runserver

    In another terminal window, run the benchmark with::

        python benchmark.py ws://localhost:8000





