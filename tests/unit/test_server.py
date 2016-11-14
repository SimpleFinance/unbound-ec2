from tests import unittest
from tests import mock
from unbound_ec2 import server
from tests import attrs


class TestServer(server.Server):
    HANDLE_FORWARD_RESULT = 'dummy_handle_forward'
    HANDLE_PASS_RESULT = True
    DNSMSG = mock.MagicMock()

    def handle_request(self, _id, event, qstate, qdata, request_type):
        return self.HANDLE_FORWARD_RESULT

    def new_dns_msg(self, qname):
        return self.DNSMSG


class TestAbstractServer(unittest.TestCase):
    def setUp(self):
        server.log_info = mock.Mock()
        lookup_mock = mock.MagicMock()
        self.zone = '.bogus.tld'
        self.reverse_zone = '127.in-addr.arpa'
        self.ttl = 'bogus_ttl'
        self.ip_order = 'bogus_ip_order'
        self.forwarded_zones = ''
        self.srv = TestServer(self.zone, self.reverse_zone, self.ttl, lookup_mock, self.ip_order, self.forwarded_zones)

    def tearDown(self):
        self.srv = None

    def test_operate_event_new(self):
        id = 'bogus_id'
        event = attrs['MODULE_EVENT_NEW']
        qstate = mock.MagicMock()
        qdata = mock.MagicMock()
        qstate.qinfo.qname_str = "fqdn.not-bogus.tld"
        self.assertTrue(self.srv.operate(id, event, qstate, qdata))
        qstate.ext_state.__setitem__.assert_called_with(id, attrs['MODULE_WAIT_MODULE'])

    def test_operate_event_pass(self):
        id = 'bogus_id'
        event = attrs['MODULE_EVENT_PASS']
        qstate = mock.MagicMock()
        qdata = mock.MagicMock()
        qstate.qinfo.qname_str = "fqdn.not-bogus.tld"
        self.assertTrue(self.srv.operate(id, event, qstate, qdata))
        qstate.ext_state.__setitem__.assert_called_with(id, attrs['MODULE_WAIT_MODULE'])

    def test_operate_event_moddone(self):
        id = 'bogus_id'
        event = attrs['MODULE_EVENT_MODDONE']
        qstate = mock.MagicMock()
        qdata = mock.MagicMock()
        self.assertTrue(self.srv.operate(id, event, qstate, qdata))
        qstate.ext_state.__setitem__.assert_called_with(id, attrs['MODULE_FINISHED'])

    def test_operate_forward(self):
        id = 'bogus_id'
        event = attrs['MODULE_EVENT_NEW']
        qstate = mock.MagicMock()
        qstate.qinfo.qtype = attrs['RR_TYPE_A']
        qstate.qinfo.qname_str = 'bogus-name%s.' % self.zone
        qdata = mock.MagicMock()
        self.assertEqual(self.srv.operate(id, event, qstate, qdata), TestServer.HANDLE_FORWARD_RESULT)
        qstate.qinfo.qtype = attrs['RR_TYPE_ANY']
        self.assertEqual(self.srv.operate(id, event, qstate, qdata), TestServer.HANDLE_FORWARD_RESULT)

    def test_forwarded_zones(self):
        server.log_info = mock.Mock()
        lookup_mock = mock.MagicMock()
        forwarded_zones = '.subdomain%s' % self.zone
        self.srv2 = TestServer(self.zone, self.reverse_zone, self.ttl, lookup_mock, self.ip_order, forwarded_zones)
        id = 'bogus_id'
        event = attrs['MODULE_EVENT_NEW']
        qstate = mock.MagicMock()
        qstate.qinfo.qtype = attrs['RR_TYPE_A']
        qstate.qinfo.qname_str = 'bogus-name%s' % self.forwarded_zones
        qdata = mock.MagicMock()
        self.assertEqual(self.srv.operate(id, event, qstate, qdata), TestServer.HANDLE_PASS_RESULT)
        qstate.ext_state.__setitem__.assert_called_with(id, attrs['MODULE_WAIT_MODULE'])


class TestAuthoritativeServer(unittest.TestCase):
    def setUp(self):
        server.log_info = mock.Mock()
        lookup_mock = mock.MagicMock()
        self.zone = '.bogus.tld'
        self.reverse_zone = '127.in-addr.arpa'
        self.ttl = 'bogus_ttl'
        self.ip_order = 'bogus_ip_order'
        self.forwarded_zones = ''
        self.srv = server.Authoritative(self.zone, self.reverse_zone, self.ttl, lookup_mock, self.ip_order,
                                        self.forwarded_zones)

    def tearDown(self):
        self.srv = None

    def test_handle_forward(self):
        id = 'bogus_id'
        event = attrs['MODULE_EVENT_NEW']
        qstate = mock.MagicMock()
        qstate.qinfo.qtype = attrs['RR_TYPE_A']
        qstate.qinfo.qname_str = 'bogus-name%s.' % self.zone
        qdata = mock.MagicMock()
        server.DNSMessage = mock.MagicMock()
        self.assertTrue(self.srv.operate(id, event, qstate, qdata))

    def test_handle_empty(self):
        id = 'bogus_id'
        event = attrs['MODULE_EVENT_NEW']
        qstate = mock.MagicMock()
        qstate.qinfo.qtype = attrs['RR_TYPE_TXT']
        qstate.qinfo.qname_str = 'bogus-name%s.' % self.zone
        qdata = mock.MagicMock()
        server.DNSMessage = mock.MagicMock()
        self.assertTrue(self.srv.operate(id, event, qstate, qdata))


class TestCachingServer(unittest.TestCase):
    def setUp(self):
        server.log_info = mock.Mock()
        self.lookup_mock = mock.MagicMock()
        self.zone = '.bogus.tld'
        self.reverse_zone = '127.in-addr.arpa'
        self.ttl = 88888881
        self.ip_order = 'bogus_ip_order'
        self.forwarded_zones = ''
        self.srv = server.Caching(self.zone, self.reverse_zone, self.ttl, self.lookup_mock, self.ip_order,
                                  self.forwarded_zones)

    def tearDown(self):
        self.srv = None

    def test_handle_forward(self):
        server.storeQueryInCache = mock.Mock()
        server.DNSMessage = mock.MagicMock()
        instances_mock = mock.MagicMock()
        instances_mock.tags = {'Address': 'bogus_ip_address'}
        self.lookup_mock.lookup.return_value = [instances_mock]
        id = 'bogus_id'
        event = attrs['MODULE_EVENT_NEW']
        qstate = mock.MagicMock()
        qstate.qinfo.qtype = attrs['RR_TYPE_A']
        qstate.qinfo.qname_str = 'bogus-name%s.' % self.zone
        qdata = mock.MagicMock()
        self.assertTrue(self.srv.operate(id, event, qstate, qdata))
        qstate.ext_state.__setitem__.assert_called_with(id, attrs['MODULE_FINISHED'])
        self.assertEqual(qstate.return_msg.rep.security, 2)
        server.DNSMessage.return_value.answer.append.assert_called_with(
            '%s %d IN A %s' % (qstate.qinfo.qname_str, self.ttl, 'bogus_ip_address'))
