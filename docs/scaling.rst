Scaling
=======

Of course, one of the downsides of introducing a channel layer to Django it
that it's something else that must scale. Scaling traditional Django as a
WSGI application is easy - you just add more servers and a loadbalancer. Your
database is likely to be the thing that stopped scaling before, and there's
a relatively large amount of knowledge about tackling that problem.

By comparison, there's not as much knowledge about scaling something like this
(though as it is very similar to a task queue, we have some work to build from).
In particular, the fact that messages are at-most-once - we do not guarantee
delivery, in the same way a webserver doesn't guarantee a response - means
we can loosen a lot of restrictions that slow down more traditional task queues.

In addition, because channels can only have single consumers and they're handled
by a fleet of workers all running the same code, we could easily split out
incoming work by sharding into separate clusters of channel backends
and worker servers - any cluster can handle any request, so we can just
loadbalance over them.

Of course, that doesn't work for interface servers, where only a single
particular server is listening to each response channel - if we broke things
into clusters, it might end up that a response is sent on a different cluster
to the one that the interface server is listening on.

That's why Channels labels any *response channel* with a leading ``!``, letting
you know that only one server is listening for it, and thus letting you scale
and shard the two different types of channels accordingly (for more on
the difference, see :ref:`channel-types`).
