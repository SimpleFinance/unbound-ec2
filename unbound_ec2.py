#!/usr/bin/env python
# coding: utf-8

__license__ = """
Copyright (c) 2013 Will Maier <wcmaier@m.aier.us>

Permission to use, copy, modify, and distribute this software for any
purpose with or without fee is hereby granted, provided that the above
copyright notice and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
"""

from Queue import PriorityQueue
from boto.ec2.connection import EC2Connection
from boto.exception import EC2ResponseError
from collections import defaultdict

import Queue
import atexit
import boto
import boto.ec2
import os
import random
import threading
import time


Ec2Resolver = None
RecordInvalidator = None
TTL = None
ZONE = None
ec2 = None


class Repeater(threading.Thread):
    def __init__(self, delay, callme):
        threading.Thread.__init__(self)
        self.callme = callme
        self.delay = delay
        self.event = threading.Event()

    def run(self):
        while not self.event.wait(1.0):
            self.callme()
            self.event.wait(self.delay)

    def stop(self):
        self.event.set()
        self.join()


class Invalidator(object):
    """Every N seconds, pop a message off the priority queue and
    check for any changes to each instance in the message.
    If there were any changes, invalidate the dns record.
    """

    def __init__(self, interval, resolver):
        self.resolver = resolver
        self.interval = interval
        self._timers = []
        self.queue = PriorityQueue()
        self.repeater = Repeater(self.interval, self._worker)
        atexit.register(self.stop)
        self.repeater.start()

    def stop(self):
        self.repeater.stop()
        self.queue.join()

    def request(self, qst, instances):
        """Record a lookup request."""
        self.queue.put((time.time(), (qst, set(i.id for i in instances))), False)

    def _worker(self):
        try:
            self._worker_impl()
        except Queue.Empty:
            pass

    def _worker_impl(self):
        try:
            _, item = self.queue.get(False)
        except Queue.Empty:
            return
        qst, old_instances = item
        instances = self.resolver(qst.qinfo.qname_str)
        if set(i.id for i in instances) != old_instances:
            invalidateQueryInCache(qst, qst.qinfo)
        else:
            self.queue.put((time.time(), item), False)
        self.queue.task_done()


class BatchInvalidator(Invalidator):
    def _worker(self):
        # update instance list.
        self.resolver.initialize()
        while True:
            try:
                self._worker_impl()
            except Queue.Empty:
                return


class EC2NameResolver(object):
    def __init__(self, ec2):
        self.ec2 = ec2
    def __call__(self, name):
        pass

class SingleLookupResolver(EC2NameResolver):
    def __call__(self, name):
        reservations = self.ec2.get_all_instances(filters={
            "instance-state-name": "running",
            "tag:Name": name.rstrip("."),
        })

        return [instance for reservation in reservations
                     for instance in reservation.instances]

class BatchLookupResolver(EC2NameResolver):
    def __init__(self, ec2, zone):
        super(BatchLookupResolver, self).__init__(ec2)
        self.zone = zone
        self.lookup_by_name = defaultdict(list)
        self.initialize()

    def initialize(self):
        """Reload cache with instances."""

        reservations = self.ec2.get_all_instances(filters={
            "instance-state-name": "running",
            "tag:Name": self.zone,
        })

        self.lookup_by_name.clear()
        self.instances =  [instance for reservation in reservations
                           for instance in reservation.instances]
        for i in self.instances:
            self.lookup_by_name[i.tags['Name'].rstrip('.')].append(i)
            self.instances_by_id = dict((i.id, i) for i in self.instances)

    def __call__(self, name):
        return self.lookup_by_name[name]


def ec2_log(msg):
    log_info("unbound_ec2: %s" % msg)

def init(id_, cfg):
    global ZONE
    global TTL
    global ec2
    global RecordInvalidator
    global Ec2Resolver

    aws_region = os.environ.get("AWS_REGION", "us-west-1").encode("ascii")
    ZONE = os.environ.get("ZONE", ".banksimple.com").encode("ascii")
    TTL = int(os.environ.get("TTL", "3600"))
    testing = os.environ.get('UNBOUND_DEBUG') == "true"
    ec2 = EC2Connection(region=boto.ec2.get_region(aws_region),
                        is_secure=not testing)

    Ec2Resolver = BatchLookupResolver(ec2, ZONE)
    if not testing:
        RecordInvalidator = BatchInvalidator(int(
            os.environ.get('UNBOUND_REFRESH_INTERVAL', "300")),
            Ec2Resolver
        )


    if not ZONE.endswith("."):
        ZONE += "."

    ec2_log("connected to aws region %s" % aws_region)
    ec2_log("authoritative for zone %s" % ZONE)

    return True

def deinit(id_):
    if RecordInvalidator:
        RecordInvalidator.stop()
    return True

def inform_super(id_, qstate, superqstate, qdata): return True

def operate(id_, event, qstate, qdata):
    """
    Perform action on pending query. Accepts a new query, or work on pending
    query.

    You have to set qstate.ext_state on exit. The state informs unbound about result
    and controls the following states.

    Parameters:
        id – module identifier (integer)
        qstate – module_qstate query state structure
        qdata – query_info per query data, here you can store your own dat
    """
    global ZONE

    if (event == MODULE_EVENT_NEW) or (event == MODULE_EVENT_PASS):
        if (qstate.qinfo.qtype == RR_TYPE_A) or (qstate.qinfo.qtype == RR_TYPE_ANY):
            qname = qstate.qinfo.qname_str
            if qname.endswith(ZONE):
                ec2_log("handling forward query for %s" % qname)
                return handle_forward(id_, event, qstate, qdata)

        # Fall through; pass on this rquest.
        return handle_pass(id_, event, qstate, qdata)

    if event == MODULE_EVENT_MODDONE:
        return handle_finished(id_, event, qstate, qdata)

    return handle_error(id_, event, qstate, qdata)

def handle_forward(id_, event, qstate, qdata):
    global TTL

    qname = qstate.qinfo.qname_str
    msg = DNSMessage(qname, RR_TYPE_A, RR_CLASS_IN, PKT_QR | PKT_RA)

    try:
        instances = Ec2Resolver(qname)
    except EC2ResponseError:
        ec2_log("Error connecting to ec2.")
        qstate.ext_state[id_] = MODULE_ERROR
        return True

    if len(instances) == 0:
        ec2_log("no results found")
        qstate.return_rcode = RCODE_NXDOMAIN
    else:
        qstate.return_rcode = RCODE_NOERROR
        random.shuffle(instances)
        for instance in instances:
            address = determine_address(instance)
            record = "%s %d IN A %s" % (qname, TTL, address)
            msg.answer.append(record)

    if not msg.set_return_msg(qstate):
        qstate.ext_state[id_] = MODULE_ERROR
        return True

    qstate.return_msg.rep.security = 2
    qstate.ext_state[id_] = MODULE_FINISHED
    if not storeQueryInCache(qstate, qstate.qinfo, qstate.return_msg.rep, 0):
        log_warn("Unable to store query in cache. possibly out of memory.")
    else:
        try:
            if RecordInvalidator:
                RecordInvalidator.request(qstate, instances)
        except Queue.Full:
            log_warn("Invalidator Queue is full!")
    return True

def handle_pass(id_, event, qstate, qdata):
    qstate.ext_state[id_] = MODULE_WAIT_MODULE
    return True

def handle_finished(id_, event, qstate, qdata):
    qstate.ext_state[id_] = MODULE_FINISHED
    return True

def handle_error(id_, event, qstate, qdata):
    ec2_log("bad event")
    qstate.ext_state[id_] = MODULE_ERROR
    return True

def determine_address(instance):
    return (instance.tags.get('Address')
            or instance.ip_address
            or instance.private_ip_address).encode("ascii")
