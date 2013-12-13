from unittest import TestCase
import shlex
import os.path
from dns import resolver, query
import dns.name
import dns.message
import time

import subprocess
import tempfile

from contextlib import contextmanager
from collections import namedtuple

UnboundConf = namedtuple('UnboundConf', ('port', 'module'))


def make_config(conf):
    tpl = """
server:
        interface: 127.0.0.1
        port: {conf.port}
        username: ""
        do-daemonize: no
        verbosity: 2
        directory: ""
        logfile: ""
        chroot: ""
        pidfile: ""
        module-config: "python validator iterator"


remote-control:
        control-enable: no

python:
        python-script: "{conf.module}"
"""
    return tpl.format(conf=conf)

@contextmanager
def unbound(conf):
        yield


class TestBadNetword(TestCase):

    def setUp(self):
        module = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'unbound_ec2.py')
        self.conf = UnboundConf(5003, module)
        print make_config(self.conf)

        self.nt = tempfile.NamedTemporaryFile(suffix='.conf')
        self.nt.write(make_config(self.conf))
        self.nt.flush()

        args = shlex.split("/usr/local/sbin/unbound -dv -c %s" % self.nt.name)
        print " ".join(args)
        time.sleep(1)
        self.proc = subprocess.Popen(args)
        time.sleep(1)

    def tearDown(self):

        self.proc.terminate()
        self.proc.wait()
        self.nt.close()


    def test_normal(self):
        # dig A @127.0.0.1 -p 5003 mwhooker.dev.banksimple.com.

        domain = "mwhooker.dev.banksimple.com."
        domain = dns.name.from_text(domain)
        if not domain.is_absolute():
            domain = domain.concatenate(dns.name.root)
        request = dns.message.make_query(domain, dns.rdatatype.ANY)

        result = query.tcp(
            request, where='127.0.0.1',
            port=self.conf.port)
        print result

        self.assertTrue(len(result.answer[0]) > 0)
