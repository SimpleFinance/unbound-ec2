import sys

# The unittest module got a significant overhaul
# in 2.7, so if we're in 2.6 we can use the backported
# version unittest2.
if sys.version_info[:2] == (2, 6):
    import unittest2 as unittest
else:
    import unittest

# Python 3 includes mocking, while 2 requires an extra module.
if sys.version_info[0] == 2:
    import mock
else:
    from unittest import mock

# Mock unboundmodule for all tests
attrs = {
    'MODULE_EVENT_NEW': 'BOGUS_EVENT_NEW',
    'MODULE_EVENT_PASS': 'BOGUS_EVENT_PASS',
    'MODULE_EVENT_MODDONE': 'BOGUS_MODULE_EVENT_MODDONE',
    'MODULE_WAIT_MODULE': 'BOGUS_MODULE_WAIT_MODULE',
    'MODULE_FINISHED': 'BOGUS_MODULE_FINISHED',
    'MODULE_ERROR': 'BOGUS_MODULE_ERROR',
    'RR_TYPE_A': 'BOGUS_RR_TYPE_A',
    'RR_TYPE_ANY': 'BOGUS_RR_TYPE_ANY',
    'RR_TYPE_PTR': 'BOGUS_RR_TYPE_PTR',
    'RR_CLASS_IN': 'BOGUS_RR_CLASS_IN',
    'PKT_QR': 999991,
    'PKT_RA': 999992,
    'PKT_AA': 999993,
    'RCODE_NOERROR': 'BOGUS_RCODE_NOERROR',
    'RCODE_NXDOMAIN': 'BOGUS_RCODE_NXDOMAIN'
}

sys.modules['unboundmodule'] = mock.Mock(**attrs)
