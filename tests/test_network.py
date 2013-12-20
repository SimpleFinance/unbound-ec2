from collections import namedtuple
from vaurien.util import start_proxy, stop_proxy
from vaurienclient import Client as VClient

import boto.ec2
import vaurien.behaviors.error



# boto doesn't retry 501s
del vaurien.behaviors.error._ERRORS[501]
vaurien.behaviors.error._ERROR_CODES = vaurien.behaviors.error._ERRORS.keys()

from .util import UnboundTest

class TestBadNetwork(UnboundTest):
    def setUp(self):

        super(TestBadNetwork, self).setUp()
        self.unbound_stop = self._start_unbound(self.conf)

    def tearDown(self):
        self.unbound_stop()
        stop_proxy(self.proxy_pid)

    def _setup_proxy(self, protocol='http', options=None):
        # vaurien --protocol tcp --proxy localhost:8888 --backend
        # ec2.us-west-2.amazonaws.com:80 --log-level debug --protocol-tcp-reuse-socket
        # --protocol-tcp-keep-alive

        # vaurien.run --backend ec2.us-west-1.amazonaws.com:80 --proxy
        # localhost:8000 --log-level info --log-output - --protocol tcp --http
        # --http-host localhost --http-port 8080 --protocol-tcp-reuse-socket
        # --protocol-tcp-keep-alive
        if not options:
            options = []
        self.proxy_pid = start_proxy(
            protocol=protocol,
            proxy_port=8000,
            backend_host=boto.ec2.RegionData['us-west-1'],
            backend_port=80,
            options=[
                '--protocol-tcp-reuse-socket',
                '--protocol-tcp-keep-alive'
            ] + options
        )
        assert self.proxy_pid is not None

    def test_normal(self):
        # dig A @127.0.0.1 -p 5003 mwhooker.dev.banksimple.com.
        self._setup_proxy()
        client = VClient()

        with client.with_behavior('dummy'):
            result = self._query_ns()
            self._test_result(result)

    def test_under_partition(self):
        """Test that we succeed on network errors
        if we have a cached result."""
        self._setup_proxy(protocol='tcp')
        client = VClient()
        options = {
            'inject': True
        }

        result = self._query_ns()
        with client.with_behavior('error', **options):
            result = self._query_ns()
            self._test_result(result)

    def test_aws_transient(self):
        """Tests that we retry requests."""
        self._setup_proxy()
        client = VClient()

        with client.with_behavior('transient'):
            result = self._query_ns()
            self._test_result(result)

    def test_aws_5xx(self):
        """test that we succeed on 5xx errors if we have a cached
        result."""
        self._setup_proxy()
        client = VClient()
        options = {
            'inject': True
        }

        result = self._query_ns()
        with client.with_behavior('error', **options):
            result = self._query_ns()
            self._test_result(result)
