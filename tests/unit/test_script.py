from tests import unittest
from tests import mock
from unbound_ec2 import script

class TestAbstractServer(unittest.TestCase):
    def setUp(self):
        self.id = mock.Mock()
        self.cfg = mock.Mock()
        script.EC2Connection = mock.MagicMock()

    def tearDown(self):
        self.id = None
        self.cfg = None
        script.EC2Connection = None

    def test_init(self):
        script.init(self.id, self.cfg)

    def test_operate(self):
        event = mock.Mock()
        qstate = mock.MagicMock()
        qdata = mock.Mock()
        script.operate(self.id, event, qstate, qdata)