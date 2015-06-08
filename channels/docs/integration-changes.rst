Message Standards
=================

Some standardised message formats are used for common message types - they
are detailed below.

HTTP Request
------------

Represents a full-fledged, single HTTP request coming in from a client.
Contains the following keys:

* request: An encoded Django HTTP request
* response_channel: The channel name to write responses to


HTTP Response
-------------

Sends a whole response to a client.
Contains the following keys:

* response: An encoded Django HTTP response
