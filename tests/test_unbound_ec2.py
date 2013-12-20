from .util import UnboundTest

class TestUnboundEc2(UnboundTest):

    def setUp(self):
        super(TestUnboundEc2, self).setUp()
        self.unbound_stop = self._start_unbound(
            self.conf,
            {'mock_ec2connection': True}
        )

    def tearDown(self):
        self.unbound_stop()

    def test_resolve(self):
        self.domain = '1.banksimple.com.'
        self._test_result(self._query_ns())
