from collections import namedtuple
import itertools

from tests import unittest
from tests import mock
from unbound_ec2 import lookup
from unbound_ec2 import config

RESERVATION_COUNT = 2


def mock_ec2():
    reservation = namedtuple('Reservation', ('instances'))
    instance = namedtuple('Instance', ('id', 'tags'))
    ec2 = mock.Mock()
    ec2.get_all_reservations = mock.MagicMock(return_value=[reservation(
        [instance("id-%s" % i, {
            "Name": "name-%s" % i,
            "Address": "192.168.1.%s" % i}
                  ) for i in xrange(RESERVATION_COUNT)])])
    return ec2


class TestDirectLookup(unittest.TestCase):
    def setUp(self):
        self.zone = '.bogus.tld'
        self.domain = self.zone.strip('.')
        self.directlookup = lookup.DirectLookup(mock_ec2(), self.zone, config.DEFAULT_LOOKUP_FILTERS)

    def tearDown(self):
        self.directlookup = None

    def test_resolve(self):
        resolve = self.directlookup.resolve()
        self.assertEqual(len(resolve), RESERVATION_COUNT * 3)
        for i in xrange(RESERVATION_COUNT):
            self.assertIn('id-%d.%s' % (i, self.domain), resolve)
            self.assertIn('name-%d.%s' % (i, self.domain), resolve)

    def test_lookup(self):
        for i in xrange(RESERVATION_COUNT):
            instances = self.directlookup.lookup('id-%d.%s' % (i, self.domain))
            for instance in itertools.chain(instances):
                self.assertEqual('id-%d' % i, instance.id)
                self.assertEqual('name-%d' % i, instance.tags['Name'])


class TestCacheLookup(unittest.TestCase):
    def setUp(self):
        self.zone = '.bogus.tld'
        self.domain = self.zone.strip('.')
        self.cachelookup = lookup.CacheLookup(mock_ec2(), self.zone, config.DEFAULT_LOOKUP_FILTERS)

    def tearDown(self):
        self.cachelookup = None

    def test_invalidate(self):
        self.assertEqual(0, len(self.cachelookup.cache))
        self.cachelookup.resolve()
        self.assertEqual(len(self.cachelookup.cache), RESERVATION_COUNT * 3)
        self.assertIn('id-0.%s' % self.domain, self.cachelookup.cache)
        self.cachelookup.invalidate('id-0.%s' % self.domain)
        self.assertEqual(len(self.cachelookup.cache), (RESERVATION_COUNT * 3) - 1)
        self.assertNotIn('id-0.%s' % self.domain, self.cachelookup.cache)
        self.cachelookup.invalidate()
        self.assertEqual(0, len(self.cachelookup.cache))
