Django Channels Load Testing Results for (2016-09-06)
===============

The goal of these load tests is to see how Channels performs with normal HTTP traffic under heavy load.

In order to handle WebSockets, Channels introduced ASGI, a new interface spec for asynchronous request handling. Also,
Channels implemented this spec with Daphne--an HTTP, HTTP2, and WebSocket protocol server.

The load testing completed has been to compare how well Daphne using 1 worker performs with normal HTTP traffic in
comparison to a WSGI HTTP server. Gunincorn was chosen as its configuration was simple and well-understood.


Summary of Results
~~~~~~~~~~~~

Daphne is not as efficient as its WSGI counterpart. When considering only latency, Daphne can have 10 times the latency
when under the same traffic load as gunincorn. When considering only throughput, Daphne can have 40-50% of the total
throughput of gunicorn while still being at 2 times latency.

The results should not be surprising considering the overhead involved. However, these results represent the simplest
case to test and should be represented as saying that Daphne is always slower than an WSGI server. These results are
a starting point, not a final conclusion.

Some additional things that should be tested:

- More than 1 worker
- A separate server for redis
- Comparison to other WebSocket servers, such as Node's socket.io or Rails' Action cable


Methodology
~~~~~~~~~~~~

In order to control for variances, several measures were taken:

- the same testing tool was used across all tests, `loadtest <https://github.com/alexfernandez/loadtest/>`_.
- all target machines were identical
- all target code variances were separated into appropriate files in the dir of /testproject in this repo
- all target config variances necessary to the different setups were controlled by supervisord so that human error was limited
- across different test types, the same target machines were used, using the same target code and the same target config
- several tests were run for each setup and test type


Setups
~~~~~~~~~~~~

3 setups were used for this set of tests:

1) Normal Django with Gunicorn (19.6.0)
2) Django Channels with local Redis (0.14.0) and Daphne (0.14.3)
3) Django Channels with IPC (1.1.0) and Daphne (0.14.3)


Latency
~~~~~~~~~~~~

All target and sources machines were identical ec2 instances m3.2xlarge running Ubuntu 16.04.

In order to ensure that the same number of requests were sent, the rps flag was set to 300.


.. image:: channels-latency.png


Throughput
~~~~~~~~~~~~

The same source machine was used for all tests: ec2 instance m3.large running Ubuntu 16.04.
All target machines were identical ec2 instances m3.2xlarge running Ubuntu 16.04.

For the following tests, loadtest was permitted to autothrottle so as to limit errors; this led to varied latency times.

Gunicorn had a latency of 6 ms; daphne and Redis, 12 ms; daphne and IPC,  35 ms.


.. image:: channels-throughput.png


Supervisor Configs
~~~~~~~~~~~~

**Gunicorn (19.6.0)**

This is the non-channels config. It's a standard Django environment on one machine, using gunicorn to handle requests.

.. code-block:: bash

  [program:gunicorn]
  command = gunicorn testproject.wsgi_no_channels -b 0.0.0.0:80
  directory = /srv/channels/testproject/
  user = root
  
  [group:django_http]
  programs=gunicorn
  priority=999


**Redis (0.14.0) and Daphne (0.14.3)**

This is the channels config using redis as the backend. It's on one machine, so a local redis confog.

Also, it's a single worker, not multiple, as that's the default config.

.. code-block:: bash

  [program:daphne]
  command = daphne -b 0.0.0.0 -p 80 testproject.asgi:channel_layer
  directory = /srv/channels/testproject/
  user = root
  
  [program:worker]
  command = python manage.py runworker
  directory = /srv/channels/testproject/
  user = django-channels
  
  
  [group:django_channels]
  programs=daphne,worker
  priority=999


**IPC (1.1.0) and Daphne (0.14.3)**

This is the channels config using IPC (Inter Process Communication). It's only possible to have this work on one machine.


.. code-block:: bash

  [program:daphne]
  command = daphne -b 0.0.0.0 -p 80 testproject.asgi_for_ipc:channel_layer
  directory = /srv/channels/testproject/
  user = root
  
  [program:worker]
  command = python manage.py runworker --settings=testproject.settings.channels_ipc
  directory = /srv/channels/testproject/
  user = root
  
  
  [group:django_channels]
  programs=daphne,worker
  priority=999
