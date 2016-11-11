from abc import ABCMeta, abstractmethod
import time

from unboundmodule import *


class Server:
    """Abstract server class for serving DNS requests.
    Provides functional framework for implementing authoritative or caching servers.
    """
    __metaclass__ = ABCMeta

    def __init__(self, zone, reverse_zone, ttl, lookup, ip_order, forwarded_zones):
        self.zone = '%s.' % zone.strip('.')
        self.reverse_zone = '%s.' % reverse_zone.strip('.')
        self.lookup = lookup
        self.ttl = ttl
        self.ip_order = ip_order
        if len(forwarded_zones) > 0:
            self.forwarded_zones = ['%s.' % z.rstrip('.') for z in forwarded_zones.split(',')]
        else:
            self.forwarded_zones = []

    def operate(self, _id, event, qstate, qdata):
        """
        This is a main entry point function that will be called from the unbound python script

        :param _id:
        :param event:
        :param qstate:
        :param qdata:
        :return:
        """
        if event in [MODULE_EVENT_NEW, MODULE_EVENT_PASS]:
            if self.should_handle_request(qstate):
                return self._operate_forward(_id, event, qstate, qdata)
            return self.handle_pass(_id, event, qstate, qdata)

        if event == MODULE_EVENT_MODDONE:
            return self.handle_finished(_id, event, qstate, qdata)

        return self.handle_error(_id, event, qstate, qdata)

    def should_handle_request(self, qstate):
        qname = qstate.qinfo.qname_str
        for x in self.forwarded_zones:
            if qname.endswith(x):
                return False
        if qname.endswith(self.zone):
            return True
        if qname.endswith(self.reverse_zone):
            return True
        return False

    def _operate_forward(self, _id, event, qstate, qdata):
        qname = qstate.qinfo.qname_str
        if qstate.qinfo.qtype in [RR_TYPE_A, RR_TYPE_ANY] and qname.endswith(self.zone):
            return self.handle_request(_id, event, qstate, qdata, getattr(self, 'forward_record'))
        elif qstate.qinfo.qtype in [RR_TYPE_PTR] and qname.endswith(self.reverse_zone):
            return self.handle_request(_id, event, qstate, qdata, getattr(self, 'reverse_record'))
        return self.handle_request_empty(_id, event, qstate, qdata)

    def handle_request_empty(self, _id, event, qstate, qdata):
        """
        Handle requests within the managed domains but RR types that we ignore

        :param _id:
        :param event:
        :param qstate:
        :param qdata:
        :return:
        """
        qname = qstate.qinfo.qname_str
        msg = self.new_dns_msg(qname)
        qstate.return_rcode = RCODE_NOERROR
        msg.set_return_msg(qstate)
        qstate.return_msg.rep.security = 2
        qstate.ext_state[_id] = MODULE_FINISHED
        return True

    def handle_request(self, _id, event, qstate, qdata, record_function):
        """
        Handle requests that match the serving criteria

        :param _id:
        :param event:
        :param qstate:
        :param qdata:
        :return:
        """
        qname = qstate.qinfo.qname_str
        msg = self.new_dns_msg(qname)
        instances = self.lookup.lookup(qname)
        if len(instances) == 0:
            log_info('%s not found' % qname)
            qstate.return_rcode = RCODE_NXDOMAIN
        else:
            qstate.return_rcode = RCODE_NOERROR
            for instance in instances:
                record = record_function(qname, instance).encode("ascii")
                msg.answer.append(record)

        if not msg.set_return_msg(qstate):
            qstate.ext_state[_id] = MODULE_ERROR
            return True

        qstate.return_msg.rep.security = 2
        qstate.ext_state[_id] = MODULE_FINISHED

        return True

    @abstractmethod
    def new_dns_msg(self, qname):
        """
        Abstract function for instantiating DNSMessage

        :param qname:
        :return:
        """
        return NotImplemented

    def handle_pass(self, _id, event, qstate, qdata):
        """
        Pass on the requests that do not match the serving criteria

        :param _id:
        :param event:
        :param qstate:
        :param qdata:
        :return:
        """
        qstate.ext_state[_id] = MODULE_WAIT_MODULE
        return True

    def handle_finished(self, _id, event, qstate, qdata):
        """
        Complete serving the request that do not match the serving criteria

        :param _id:
        :param event:
        :param qstate:
        :param qdata:
        :return:
        """
        qstate.ext_state[_id] = MODULE_FINISHED
        return True

    def handle_error(self, _id, event, qstate, qdata):
        """
        Serve request error

        :param _id:
        :param event:
        :param qstate:
        :param qdata:
        :return:
        """
        qstate.ext_state[_id] = MODULE_ERROR
        return True

    def __determine_address(self, instance):
        if self.ip_order == 'private':
            ordered_address = instance.private_ip_address or instance.ip_address
        else:
            ordered_address = instance.ip_address or instance.private_ip_address
        return (instance.tags.get('Address')
                or ordered_address).encode("ascii")

    def __determine_name(self, instance):
        domain = self.zone.rstrip('.')
        name = instance.tags['Name'].split(',')[0].rstrip('.') if 'Name' in instance.tags else instance.id
        return '%s.' % (name if domain in name else '%s.%s' % (name, domain)).encode("ascii")

    def forward_record(self, qname, instance):
        return "%s %d IN A %s" % (qname, self.ttl, self.__determine_address(instance))

    def reverse_record(self, qname, instance):
        return "%s %d IN PTR %s" % (qname, self.ttl, self.__determine_name(instance))


class Authoritative(Server):
    """This server will return non-cached authoritative answers.
    """

    def new_dns_msg(self, qname):
        """
        Return DNSMessage instance with AA flag set

        :param qname:
        :return:
        """
        return DNSMessage(qname, RR_TYPE_A, RR_CLASS_IN, PKT_QR | PKT_RA | PKT_AA)


class Caching(Server):
    """This server will serve cached answers.
    """

    def __init__(self, zone, reverse_zone, ttl, lookup, ip_order, forwarded_zones):
        Server.__init__(self, zone, reverse_zone, ttl, lookup, ip_order, forwarded_zones)
        self.cached_requests = {}

    def new_dns_msg(self, qname):
        """
        Return DNSMessage instance

        :param qname:
        :return:
        """
        return DNSMessage(qname, RR_TYPE_A, RR_CLASS_IN, PKT_QR | PKT_RA)

    def handle_forward(self, _id, event, qstate, qdata):
        """
        Apart from the standard Server handle_forward answer, results will be stored in query and request cache

        :param _id:
        :param event:
        :param qstate:
        :param qdata:
        :return:
        """
        result = Server.handle_forward(self, _id, event, qstate, qdata)
        qname = qstate.qinfo.qname_str

        if not storeQueryInCache(qstate, qstate.qinfo, qstate.return_msg.rep, 0):
            log_warn('Unable to store query in cache. possibly out of memory.')
        else:
            self.cached_requests[qname.rstrip('.')] = {'time': time.time(), 'qstate': qstate}

        return result
