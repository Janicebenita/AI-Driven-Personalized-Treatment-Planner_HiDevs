import os
import unittest
from unittest.mock import patch

from deploy.start import command


class CloudEntrypointTests(unittest.TestCase):
    def test_honors_cloud_port_and_listens_on_all_interfaces(self):
        with patch.dict(os.environ, {'PORT': '9090'}):
            args = command()
        self.assertIn('--server.port=9090', args)
        self.assertIn('--server.address=0.0.0.0', args)
        self.assertNotIn('--server.enableXsrfProtection=false', args)

    def test_invalid_port_fails_before_serving(self):
        for port in ['0', '70000', 'invalid']:
            with patch.dict(os.environ, {'PORT': port}), self.assertRaises(ValueError):
                command()
