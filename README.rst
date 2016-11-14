===========
unbound-ec2
===========

|Build Status| |Version|

This module uses the `Unbound`_ DNS resolver to answer simple DNS queries using EC2 API calls.
For example, the following query would match an EC2 instance with a ``Name`` tag of ``foo.example.com``:

.. _`Unbound`: http://unbound.net
.. _`DescribeInstances`: http://docs.aws.amazon.com/AWSEC2/latest/APIReference/ApiReference-query-DescribeInstances.html
.. |Build Status| image:: http://img.shields.io/travis/unibet/unbound-ec2.svg?style=flat
    :target: https://travis-ci.org/unibet/unbound-ec2
    :alt: Build Status
.. |Version| image:: http://img.shields.io/pypi/v/unbound-ec2.svg?style=flat
    :target: https://pypi.python.org/pypi/unbound-ec2/
    :alt: Version

.. code-block:: sh

    $ dig -p 5003 @127.0.0.1 foo.dev.example.com
    ; <<>> DiG 9.8.1-P1 <<>> -p 5003 @127.0.0.1 foo.dev.example.com
    ; (1 server found)
    ;; global options: +cmd
    ;; Got answer:
    ;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 5696
    ;; flags: qr aa rd ra; QUERY: 1, ANSWER: 2, AUTHORITY: 0, ADDITIONAL: 0

    ;; QUESTION SECTION:
    ;foo.dev.example.com.	IN	A

    ;; ANSWER SECTION:
    foo.dev.example.com. 300 IN	A	10.0.0.2
    foo.dev.example.com. 300 IN	A	10.0.0.1

    ;; Query time: 81 msec
    ;; SERVER: 127.0.0.1#5003(127.0.0.1)
    ;; WHEN: Sat Sep 28 23:27:16 2013
    ;; MSG SIZE  rcvd: 77

Installation
------------

On Debian family, install the ``unbound``, ``python-unbound`` system packages.

On Redhat family, install the ``unbound``, ``unbound-python`` system packages.

Then, install ``unbound-ec2``:

.. code-block:: sh

    $ pip install unbound-ec2


Configuration
-------------

The following settings must be added to your Unbound configuration:

.. code-block:: yaml

    server:
        chroot: ""
        module-config: "validator python iterator"

    python:
        python-script: "/etc/unbound/unbound_ec2_script"


EC2 module can be configured by specifying values in /etc/unbound/unbound_ec2.conf or setting environment variables in
``/etc/default/unbound``.

See unbound_ec2.conf.example and default_unbound.example for more information.

You can also define ``AWS_ACCESS_KEY`` and ``AWS_SECRET_ACCESS_KEY`` entries in the environment directory.
When ``unbound-ec2`` is run on an EC2 instance, though, it will automatically use an IAM instance profile if one is available.


Configuration - zone forwarding
-------------------------------

By default unbound will control the whole zone configured for the plugin, however in some cases you might want to delegate
subdomains to other authoritative name servers. Unbound allows this by using the forward-zone directive:

.. code-block:: yaml

    forward-zone:
          name: "sub-y.sub-x.example.com"
          forward-addr: "ns1.sub-y.sub-x.example.com"


Additionally, the unbound-ec2 plugin has to be configured with a comma separated list of all subdomains to be forwarded
in the [main] section of the unbound_ec2.conf configuration file:

.. code-block:: sh

    forwarded_zones = sub-y.sub-x.example.com


Considerations
--------------

``unbound-ec2`` queries the EC2 API to answer requests about names inside the specified ``zone``.
All other requests are handled normally by Unbound's caching resolver if caching type server was chosen.

For requests for names within the specified ``zone``, ``unbound_ec2`` calls `DescribeInstances`_
and filters the results using defined lookup filters (default is instances in the ``running`` state).

When more than one instance matches the ``DescribeInstances`` query, ``unbound-ec2`` will return multiple A records in a round-robin. 
In case of caching type server, query results will be cached by Unbound, and a TTL (default: 300 seconds) is defined
to encourage well-behaved clients to cache the information themselves.

IPv6 are not yet supported.

Unit tests
----------

Run with

.. code-block:: sh

    $ python setup.py test

