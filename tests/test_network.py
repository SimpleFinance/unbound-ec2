from collections import namedtuple
from dns import resolver, query
from unittest import TestCase

from vaurien.util import start_proxy, stop_proxy
from vaurienclient import Client as VClient
import dns.message
import dns.name
import os.path
import shlex
import subprocess
import tempfile
import time
import boto.ec2
import atexit

UnboundConf = namedtuple('UnboundConf', ('port', 'module'))

GoodRecord = "mwhooker.dev.banksimple.com. 300 IN A 50.18.31.82"


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
        testenv = os.environ.copy()
        testenv.update({
            'AWS_REGION': 'proxy',
            'http_proxy': 'localhost:8000',
            'UNBOUND_DEBUG': "1"
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

        module = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'unbound_ec2.py')
        self.conf = UnboundConf(5003, module)

        # vaurien --protocol tcp --proxy localhost:8888 --backend
        # ec2.us-west-2.amazonaws.com:80 --log-level debug --protocol-tcp-reuse-socket
        # --protocol-tcp-keep-alive

        # vaurien.run --backend ec2.us-west-1.amazonaws.com:80 --proxy
        # localhost:8000 --log-level info --log-output - --protocol tcp --http
        # --http-host localhost --http-port 8080 --protocol-tcp-reuse-socket
        # --protocol-tcp-keep-alive
        self.proxy_pid = start_proxy(
            proxy_port=8000,
            backend_host=boto.ec2.RegionData['us-west-1'],
            backend_port=80,
            options=[
                '--protocol-tcp-reuse-socket',
                '--protocol-tcp-keep-alive'
            ]
        )
        assert self.proxy_pid is not None
        self.unbound_stop = self._start_unbound(self.conf)


    def tearDown(self):
        self.unbound_stop()
        stop_proxy(self.proxy_pid)

    def _query_ns(self):
        domain = "mwhooker.dev.banksimple.com."
        domain = dns.name.from_text(domain)
        if not domain.is_absolute():
            domain = domain.concatenate(dns.name.root)
        request = dns.message.make_query(domain, dns.rdatatype.ANY)

        res = query.tcp(
            request, where='127.0.0.1',
            port=self.conf.port)
        print [str(a) for a in res.answer]
        return res

    def _test_result(self, result):
        self.assertTrue(len(result.answer) == 1)
        self.assertEquals(result.answer[0].to_text(), GoodRecord)

    def test_normal(self):
        # dig A @127.0.0.1 -p 5003 mwhooker.dev.banksimple.com.
        client = VClient()

        with client.with_behavior('dummy'):
            # do something...
            result = self._query_ns()
            self._test_result(result)

    #def test_under_partition(self):
    def test_aws_5xx(self):
        client = VClient()
        options = {'inject': True}

        with client.with_behavior('error', **options):
            # do something...
            result = self._query_ns()
            self._test_result(result)
