import os
import ast

from tests import unittest
from unbound_ec2 import config


class TestConfig(unittest.TestCase):
    def setUp(self):
        self.config = config.UnboundEc2Conf()

    def tearDown(self):
        os.environ['UNBOUND_ZONE'] = config.DEFAULT_ZONE
        os.environ['UNBOUND_TTL'] = config.DEFAULT_TTL
        os.environ['UNBOUND_CACHE_TTL'] = config.DEFAULT_CACHE_TTL
        os.environ['UNBOUND_SERVER_TYPE'] = config.DEFAULT_SERVER_TYPE
        os.environ['UNBOUND_LOOKUP_TYPE'] = config.DEFAULT_LOOKUP_TYPE
        os.environ['UNBOUND_LOOKUP_TAG_NAME_INCLUDE_DOMAIN'] = config.DEFAULT_LOOKUP_TAG_NAME_INCLUDE_DOMAIN
        os.environ['AWS_DEFAULT_REGION'] = config.DEFAULT_AWS_REGION
        os.environ['UNBOUND_EC2_CONF'] = config.DEFAULT_CONF_FILE
        os.environ['UNBOUND_IP_ORDER'] = config.DEFAULT_IP_ORDER
        self.config = None

    def test_init(self):
        self.assertTrue(hasattr(self.config, 'ec2'))
        self.assertTrue(hasattr(self.config, 'main'))
        self.assertTrue(hasattr(self.config, 'lookup'))
        self.assertTrue(hasattr(self.config, 'lookup_filters'))
        self.assertTrue(hasattr(self.config, 'server'))

    def test_init_conf_file(self):
        fixture_conf_file = os.path.join(os.path.dirname(__file__), 'data', 'unbound_ec2.conf')
        self.config = config.UnboundEc2Conf(fixture_conf_file)
        self.assertEqual(self.config.conf_file, fixture_conf_file)

    def test_init_env_conf_file(self):
        fixture_conf_file = os.path.join(os.path.dirname(__file__), 'data', 'unbound_ec2.conf')
        os.environ['UNBOUND_EC2_CONF'] = fixture_conf_file
        self.config = config.UnboundEc2Conf()
        self.assertEqual(self.config.conf_file, fixture_conf_file)

    def test_set_defaults(self):
        self.config.set_defaults()
        self.assertIn('aws_region', self.config.ec2)
        self.assertIn('zone', self.config.main)
        self.assertIn('ttl', self.config.main)
        self.assertIn('cache_ttl', self.config.main)
        self.assertIn('type', self.config.server)
        self.assertIn('type', self.config.lookup)
        self.assertIn('tag_name_include_domain', self.config.lookup)
        self.assertEqual(self.config.ec2['aws_region'], config.DEFAULT_AWS_REGION)
        self.assertEqual(self.config.main['zone'], config.DEFAULT_ZONE)
        self.assertEqual(self.config.main['ttl'], int(config.DEFAULT_TTL))
        self.assertEqual(self.config.main['ip_order'], config.DEFAULT_IP_ORDER)
        self.assertEqual(self.config.server['type'], config.DEFAULT_SERVER_TYPE)
        self.assertEqual(self.config.lookup['type'], config.DEFAULT_LOOKUP_TYPE)
        self.assertEqual(self.config.lookup['tag_name_include_domain'],
                         bool(config.DEFAULT_LOOKUP_TAG_NAME_INCLUDE_DOMAIN))
        self.assertEqual(self.config.lookup_filters, ast.literal_eval(config.DEFAULT_LOOKUP_FILTERS))

    def test_set_defaults_env_overwrite(self):
        os.environ['UNBOUND_ZONE'] = 'BOGUS_TLD'
        os.environ['UNBOUND_TTL'] = 'BOGUS_TTL'
        os.environ['UNBOUND_CACHE_TTL'] = 'BOGUS_CACHE_TTL'
        os.environ['AWS_DEFAULT_REGION'] = 'BOGUS_AWS_REGION'
        os.environ['UNBOUND_SERVER_TYPE'] = 'BOGUS_SERVER_TYPE'
        os.environ['UNBOUND_LOOKUP_TYPE'] = 'BOGUS_LOOKUP_TYPE'
        os.environ['UNBOUND_LOOKUP_TAG_NAME_INCLUDE_DOMAIN'] = 'BOGUS_LOOKUP_TAG_NAME_INCLUDE_DOMAIN'
        os.environ['UNBOUND_IP_ORDER'] = 'BOGUS_IP_ORDER'
        self.config.set_defaults()
        self.assertEqual(self.config.ec2['aws_region'], 'BOGUS_AWS_REGION')
        self.assertEqual(self.config.main['zone'], 'BOGUS_TLD')
        self.assertEqual(self.config.main['ttl'], 'BOGUS_TTL')
        self.assertEqual(self.config.main['cache_ttl'], 'BOGUS_CACHE_TTL')
        self.assertEqual(self.config.main['ip_order'], 'BOGUS_IP_ORDER')
        self.assertEqual(self.config.server['type'], 'BOGUS_SERVER_TYPE')
        self.assertEqual(self.config.lookup['type'], 'BOGUS_LOOKUP_TYPE')
        self.assertEqual(self.config.lookup['tag_name_include_domain'], 'BOGUS_LOOKUP_TAG_NAME_INCLUDE_DOMAIN')
        self.assertEqual(self.config.lookup_filters, ast.literal_eval(config.DEFAULT_LOOKUP_FILTERS))

    def test_parse_full(self):
        fixture_conf_file = os.path.join(os.path.dirname(__file__), 'data', 'unbound_ec2_full.conf')
        self.config = config.UnboundEc2Conf(fixture_conf_file)
        self.assertTrue(self.config.parse())
        self.assertIn('aws_region', self.config.ec2)
        self.assertIn('zone', self.config.main)
        self.assertIn('ttl', self.config.main)
        self.assertIn('cache_ttl', self.config.main)
        self.assertEqual(self.config.ec2['aws_region'], 'BOGUS_AWS_REGION_FROM_CONF_FILE')
        self.assertEqual(self.config.main['zone'], 'BOGUS_ZONE_FROM_CONF_FILE')
        self.assertEqual(self.config.main['ttl'], 'BOGUS_TTL_FROM_CONF_FILE')
        self.assertEqual(self.config.main['cache_ttl'], 'BOGUS_CACHE_TTL_FROM_CONF_FILE')
        self.assertEqual(self.config.main['ip_order'], 'BOGUS_IP_ORDER_FROM_CONF_FILE')
        self.assertEqual(self.config.server['type'], 'BOGUS_SERVER_TYPE_FROM_FILE')
        self.assertEqual(self.config.lookup['type'], 'BOGUS_LOOKUP_TYPE_FROM_FILE')
        self.assertEqual(self.config.lookup['tag_name_include_domain'], 'BOGUS_TAG_NAME_INCLUDE_DOMAIN_FROM_FILE')
        self.assertEqual(self.config.lookup_filters, {'bogus-key': 'bogus-value-from-file'})

    def test_parse_partial(self):
        fixture_conf_file = os.path.join(os.path.dirname(__file__), 'data', 'unbound_ec2_partial.conf')
        self.config = config.UnboundEc2Conf(fixture_conf_file)
        self.assertTrue(self.config.parse())
        self.assertIn('aws_region', self.config.ec2)
        self.assertIn('zone', self.config.main)
        self.assertNotIn('ttl', self.config.main)
        self.assertNotIn('cache_ttl', self.config.main)
        self.assertNotIn('tag_name_include_domain', self.config.lookup)
        self.assertEqual(self.config.ec2['aws_region'], 'BOGUS_AWS_REGION_FROM_CONF_FILE')
        self.assertEqual(self.config.main['zone'], 'BOGUS_ZONE_FROM_CONF_FILE')
        self.assertEqual(self.config.server['type'], 'BOGUS_SERVER_TYPE_FROM_FILE')
        self.assertEqual(self.config.lookup['type'], 'BOGUS_LOOKUP_TYPE_FROM_FILE')
        self.assertFalse(self.config.lookup_filters)

    def test_parse_partial_with_defaults(self):
        fixture_conf_file = os.path.join(os.path.dirname(__file__), 'data', 'unbound_ec2_partial.conf')
        self.config = config.UnboundEc2Conf(fixture_conf_file)
        self.config.set_defaults()
        self.assertTrue(self.config.parse())
        self.assertEqual(self.config.ec2['aws_region'], 'BOGUS_AWS_REGION_FROM_CONF_FILE')
        self.assertEqual(self.config.main['zone'], 'BOGUS_ZONE_FROM_CONF_FILE')
        self.assertEqual(self.config.main['ttl'], int(config.DEFAULT_TTL))
        self.assertEqual(self.config.main['cache_ttl'], int(config.DEFAULT_CACHE_TTL))
        self.assertEqual(self.config.server['type'], 'BOGUS_SERVER_TYPE_FROM_FILE')
        self.assertEqual(self.config.lookup['type'], 'BOGUS_LOOKUP_TYPE_FROM_FILE')
        self.assertEqual(self.config.lookup['tag_name_include_domain'],
                         bool(config.DEFAULT_LOOKUP_TAG_NAME_INCLUDE_DOMAIN))
        self.assertEqual(self.config.lookup_filters, ast.literal_eval(config.DEFAULT_LOOKUP_FILTERS))
