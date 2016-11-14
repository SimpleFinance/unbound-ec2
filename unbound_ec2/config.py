import ConfigParser
import os.path
import ast

DEFAULT_CONF_FILE = '/etc/unbound/unbound_ec2.conf'
DEFAULT_AWS_REGION = 'us-west-1'
DEFAULT_ZONE = 'zone.tld'
DEFAULT_REVERSE_ZONE = '127.in-addr.arpa'
DEFAULT_TTL = '300'
DEFAULT_CACHE_TTL = '30'
DEFAULT_SERVER_TYPE = 'caching'
DEFAULT_LOOKUP_TYPE = 'cache'
DEFAULT_LOOKUP_TAG_NAME_INCLUDE_DOMAIN = 'True'
DEFAULT_LOOKUP_FILTERS = "{'instance-state-name': 'running'}"
DEFAULT_IP_ORDER = 'private'
DEFAULT_FORWARDED_ZONES = ''


class UnboundEc2Conf(object):
    """Configuration parser for Unbound EC2 module.

    """

    def __init__(self, conf_file=None):
        self.config = ConfigParser.ConfigParser()
        self.conf_file = conf_file if conf_file else os.environ.get('UNBOUND_EC2_CONF',
                                                                    DEFAULT_CONF_FILE).encode('ascii')
        self.ec2 = {}
        self.main = {}
        self.lookup = {}
        self.lookup_filters = {}
        self.server = {}

    def set_defaults(self):
        """Sets default values for defined self instance attributes.

        """
        self.ec2['aws_region'] = os.environ.get('AWS_DEFAULT_REGION', DEFAULT_AWS_REGION).encode('ascii')
        self.main['zone'] = os.environ.get('UNBOUND_ZONE', DEFAULT_ZONE).encode('ascii')
        self.main['reverse_zone'] = os.environ.get('UNBOUND_REVERSE_ZONE', DEFAULT_REVERSE_ZONE).encode('ascii')
        self.main['ttl'] = self.__try_type(os.environ.get('UNBOUND_TTL', DEFAULT_TTL).encode('ascii'))
        self.main['cache_ttl'] = self.__try_type(
            os.environ.get('UNBOUND_CACHE_TTL', DEFAULT_CACHE_TTL).encode('ascii'))
        self.server['type'] = os.environ.get('UNBOUND_SERVER_TYPE', DEFAULT_SERVER_TYPE).encode('ascii')
        self.lookup['type'] = os.environ.get('UNBOUND_LOOKUP_TYPE', DEFAULT_LOOKUP_TYPE).encode('ascii')
        self.lookup['tag_name_include_domain'] = self.__try_type(
            os.environ.get('UNBOUND_LOOKUP_TAG_NAME_INCLUDE_DOMAIN',
                           DEFAULT_LOOKUP_TAG_NAME_INCLUDE_DOMAIN).encode('ascii'))
        self.lookup_filters = self.__try_type(
            os.environ.get('UNBOUND_LOOKUP_FILTERS', DEFAULT_LOOKUP_FILTERS).encode('ascii'))
        self.main['ip_order'] = os.environ.get('UNBOUND_IP_ORDER', DEFAULT_IP_ORDER).encode('ascii')
        self.main['forwarded_zones'] = os.environ.get('UNBOUND_FORWARDED_ZONES', DEFAULT_FORWARDED_ZONES)\
            .encode('ascii')

    def parse(self):
        """Tries to read defined configuration file and merge values with instance attributes.

        """
        result = False
        if os.path.isfile(self.conf_file):
            self.config.read(self.conf_file)

            for section in self.config.sections():
                setattr(self, section, self.__get_merged_attribute(section, dict(self.config.items(section))))
            result = True
        return result

    def __get_merged_attribute(self, name, value):
        string_result = value
        if getattr(self, name):
            string_result = getattr(self, name).copy()
            string_result.update(value)

        result = {}
        for key in string_result:
            result[key] = self.__try_type(string_result[key])

        return result

    def __try_type(self, value):
        try:
            result = ast.literal_eval(value)
        except (ValueError, SyntaxError):
            result = value
        return result
