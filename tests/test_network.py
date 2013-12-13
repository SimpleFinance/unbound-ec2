from collections import namedtuple
from dns import resolver, query
from unittest import TestCase

import dns.message
import dns.name
import os.path
import shlex
import subprocess
import tempfile
import time

UnboundConf = namedtuple('UnboundConf', ('port', 'module'))

Record = "mwhooker.dev.banksimple.com. 300 IN A 50.18.31.82"


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

class TestBadNetword(TestCase):

    @staticmethod
    def _start_unbound(conf):
        nt = tempfile.NamedTemporaryFile(suffix='.conf')
        nt.write(make_config(conf))
        nt.flush()

        args = shlex.split("/usr/local/sbin/unbound -dv -c %s" % nt.name)
        time.sleep(1)
        proc = subprocess.Popen(args)
        time.sleep(1)

        def finish():
            proc.terminate()
            proc.wait()
            nt.close()

        return finish

    def setUp(self):
        module = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'unbound_ec2.py')
        self.conf = UnboundConf(5003, module)
        self.unbound_stop = self._start_unbound(self.conf)

    def tearDown(self):
        self.unbound_stop()

    def _query_ns(self):
        domain = "mwhooker.dev.banksimple.com."
        domain = dns.name.from_text(domain)
        if not domain.is_absolute():
            domain = domain.concatenate(dns.name.root)
        request = dns.message.make_query(domain, dns.rdatatype.ANY)

        return query.tcp(
            request, where='127.0.0.1',
            port=self.conf.port)

    def test_normal(self):
        # dig A @127.0.0.1 -p 5003 mwhooker.dev.banksimple.com.
        result = self._query_ns()

        self.assertTrue(len(result.answer) == 1)
        self.assertEquals(result.answer[0].to_text(), Record)
