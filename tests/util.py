from dns import resolver, query
import json
import dns.message
import dns.name
import os.path
import atexit
import shlex
import subprocess
import tempfile
import time
from collections import namedtuple
from unittest import TestCase

UNBOUND_BINARY = 'unbound'

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
class UnboundTest(TestCase):

    @staticmethod
    def _start_unbound(conf, unbound_flags=None):
        """
        unbound_flags: dict to control behavior of unbound
        """
        nt = tempfile.NamedTemporaryFile(suffix='.conf')
        nt.write(make_config(conf))
        nt.flush()

        args = shlex.split("%s -dv -c %s" % (UNBOUND_BINARY, nt.name))
        time.sleep(1)
        testenv = os.environ.copy()
        test_flags = {
            'no_invalidate': True,
            'mock_ec2connection': False
        }
        if unbound_flags:
            test_flags.update(unbound_flags)
        testenv.update({
            'AWS_REGION': 'proxy',
            'http_proxy': 'localhost:8000',
            'UNBOUND_TEST_FLAGS': json.dumps(test_flags)
        })
        proc = subprocess.Popen(args, env=testenv)
        time.sleep(1)

        @atexit.register
        def last():
            try:
                proc.kill()
            except OSError as e:
                if e.errno != 3:
                    raise

        def finish():
            proc.terminate()
            proc.wait()
            nt.close()

        return finish

    def setUp(self):
        self.domain = "mwhooker.dev.banksimple.com."
        module = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'unbound_ec2.py')
        self.conf = UnboundConf(5003, module)

    def _query_ns(self, domain=None):
        if not domain:
            domain = self.domain
        domain = dns.name.from_text(domain)
        if not domain.is_absolute():
            domain = domain.concatenate(dns.name.root)
        request = dns.message.make_query(domain, dns.rdatatype.ANY)

        res = query.tcp(
            request, where='127.0.0.1',
            port=self.conf.port)
        print [str(a) for a in res.answer]
        return res

    def _test_result(self, result, domain=None):
        if not domain:
            domain = self.domain
        self.assertTrue(len(result.answer) == 1)
        self.assertRegexpMatches(
            result.answer[0].to_text(), 
            "%s \d+ IN A \d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}" % domain
        )

