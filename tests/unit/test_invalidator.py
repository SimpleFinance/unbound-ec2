from collections import namedtuple
from collections import defaultdict

from tests import unittest
from tests import mock
from unbound_ec2 import invalidator
from unbound_ec2 import lookup


def lookup_resolve(_range):
    instance = namedtuple('Instance', ('id', 'tags'))
    instances = defaultdict(list)
    for i in range(min(_range), max(_range)):
        instances['id-%s.bogus.tld' % i].append(instance("id-%s" % i, {
            "Name": "name-%s" % i,
            "Address": "192.168.1.%s" % (i + max(_range) + min(_range))}))
    return instances


class TestCacheInvalidator(unittest.TestCase):
    def setUp(self):
        self.server_mock = mock.MagicMock()
        self.server_mock.lookup.__class__ = lookup.CacheLookup
        self.invalidator = invalidator.CacheInvalidator(self.server_mock)

    def tearDown(self):
        self.server_mock = None
        self.invalidator = None

    def test_invalidate_cached(self):
        invalidator.invalidateQueryInCache = mock.MagicMock()
        self.server_mock.lookup.resolve.side_effect = [lookup_resolve([1, 3]), lookup_resolve([1, 3])]
        self.invalidator.invalidate()
        self.server_mock.lookup.invalidate.assert_called_with()
        self.assertFalse(invalidator.invalidateQueryInCache.mock_calls)

    def test_invalidate_notcached(self):
        invalidator.invalidateQueryInCache = mock.MagicMock()
        qstate = mock.MagicMock()
        self.server_mock.cached_requests = {'id-2.bogus.tld': {'time': 'bogus_time', 'qstate': qstate}}
        self.server_mock.lookup.resolve.side_effect = [lookup_resolve([1, 3]), lookup_resolve([4, 6])]
        self.invalidator.invalidate()
        self.server_mock.lookup.invalidate.assert_called_with()
        self.assertTrue(invalidator.invalidateQueryInCache.mock_calls)
        invalidator.invalidateQueryInCache.assert_called_with(qstate, qstate.qinfo)

    def test_invalidate_direct(self):
        invalidator.invalidateQueryInCache = mock.MagicMock()
        self.server_mock.lookup.__class__ = lookup.DirectLookup
        self.invalidator.invalidate()
        self.assertFalse(self.server_mock.lookup.mock_calls)
        self.assertFalse(invalidator.invalidateQueryInCache.mock_calls)
