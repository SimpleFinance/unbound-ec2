from boto.ec2.connection import EC2Connection
import boto

from unboundmodule import log_info
from unbound_ec2 import config
from unbound_ec2 import server
from unbound_ec2 import lookup
from unbound_ec2 import repeater
from unbound_ec2 import invalidator

_server = None
_rr = None

"""
This module provides unbound python termination functions and can be used directly or indirectly
as an unbound python script.
"""


def init(id, cfg):
    global _server
    global _rr
    conf = config.UnboundEc2Conf()
    conf.set_defaults()
    conf.parse()

    ec2 = EC2Connection(region=boto.ec2.get_region(conf.ec2['aws_region']))

    _lookup = lookup.DirectLookup(ec2,
                                  conf.main['zone'],
                                  conf.lookup_filters,
                                  conf.lookup['tag_name_include_domain']) \
        if conf.lookup['type'] == 'direct' \
        else lookup.CacheLookup(ec2,
                                conf.main['zone'],
                                conf.lookup_filters,
                                conf.lookup['tag_name_include_domain'])

    _server = server.Authoritative(conf.main['zone'],
                                   conf.main['reverse_zone'],
                                   conf.main['ttl'],
                                   _lookup,
                                   conf.main['ip_order'],
                                   conf.main['forwarded_zones']) \
        if conf.server['type'] == 'authoritative' \
        else server.Caching(conf.main['zone'],
                            conf.main['reverse_zone'],
                            conf.main['ttl'],
                            _lookup,
                            conf.main['ip_order'],
                            conf.main['forwarded_zones'])

    if conf.lookup['type'] != 'direct':
        _rr = repeater.RecursiveRepeater(conf.main['cache_ttl'], invalidator.CacheInvalidator(_server).invalidate)
        _rr.start()

    __print_header(conf)

    return True


def deinit(id):
    if _rr:
        _rr.stop()
    return True


def inform_super(id, qstate, superqstate, qdata):
    return True


def operate(id, event, qstate, qdata):
    """
    Perform action on pending query. Accepts a new query, or work on pending
    query.

    You have to set qstate.ext_state on exit. The state informs unbound about
    result and controls the following states.

    Parameters:
        id - module identifier (integer)
        qstate - module_qstate query state structure
        qdata - query_info per query data, here you can store your own dat
    """
    return _server.operate(id, event, qstate, qdata)


def __print_header(conf):
    log_info('##########################')
    log_info('### UNBOUND EC2 SCRIPT ###')
    log_info('##########################')
    log_info('Configuration:')
    log_info('     Server type: %s' % conf.server['type'])
    log_info('            Zone: %s' % conf.main['zone'])
    log_info('        Zone TTL: %s seconds' % conf.main['ttl'])
    log_info('          Region: %s' % conf.ec2['aws_region'])
    log_info('          Lookup: %s' % conf.lookup['type'])
    log_info('  Lookup filters: %s' % conf.lookup_filters)
    log_info('Name tag include: %s' % conf.lookup['tag_name_include_domain'])
    log_info('        IP order: %s' % conf.main['ip_order'])
    log_info(' Forwarded zones: %s' % conf.main['forwarded_zones'])
    if conf.lookup['type'] != 'direct':
        log_info('       Cache TTL: %d seconds' % conf.main['cache_ttl'])
