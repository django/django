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

Build the docker image from Dockerfile, tag it `channels-redis-test`::

    docker build -t channels-redis-test -f Dockerfile.redis .

Run the server::

    docker-compose -f docker-compose.redis.yml up

The benchmark project will now be running on: http:{your-docker-ip}:80

Test it by navigating to that address in a browser.  It should just say "OK".

It is also running a WebSocket server at: ws://{your-docker-ip}:80

Run the benchmark's help to show the parameters::

    python benchmark.py --help

Let's just try a quick test with the default values from the parameter list::

    python benchmark.py ws://localhost:80

How to use with Docker and RabbitMQ:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Build the docker image from Dockerfile, tag it `channels-rabbitmq-test`::

    docker build -t channels-rabbitmq-test -f Dockerfile.rabbitmq .

Run the server::

    docker-compose -f docker-compose.rabbitmq.yml up

The rest is the same.

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


Additional load testing options:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you wish to setup a separate machine to loadtest your environment, you can do the following steps.

Install fabric on your machine. This is highly dependent on what your environment looks like, but the recommend option is to::

    pip install fabric

(Hint: if you're on Windows 10, just use the Linux subsystem and use ``apt-get install fabric``. It'll save you a lot of trouble.)

Git clone this project down to your machine::

    git clone https://github.com/django/channels/

Relative to where you cloned the directory, move up a couple levels::

    cd channels/testproject/

Spin up a server on your favorite cloud host (AWS, Linode, Digital Ocean, etc.) and get its host and credentials. Run the following command using those credentials::

    fab setup_load_tester -i "ida_rsa" -H ubuntu@example.com

That machine will provision itself. It may (depending on your vendor) prompt you a few times for a ``Y/n`` question. This is just asking you about increasing stroage space.


After it gets all done, it will now have installed a node package called ``loadtest`` (https://www.npmjs.com/package/loadtest). Note: my examples will show HTTP only requests, but loadtest also supports websockets.

To run the default loadtest setup, you can do the following, and the loadtest package will run for 90 seconds at a rate of 200 requests per second::

    fab run_loadtest:http://127.0.0.1 -i "id_rsa" -H ubuntu@example.com

Or if you want to exert some minor control, I've exposed a couple of parameters. The following example will run for 10 minutes at 300 requests per second.::

    fab run_loadtest:http://127.0.0.1,rps=300,t=600 -i "id_rsa" -H ubuntu@example.com

If you want more control, you can always pass in your own commands to::

    fab shell -i "id_rsa" -H ubuntu@example.com
