import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Add repo root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sources.tools.mcpFinder import MCP_finder

class TestMCPFinder(unittest.TestCase):
    def setUp(self):
        os.environ['WORK_DIR'] = '/tmp/workspace'
        if not os.path.exists('/tmp/workspace'):
            os.makedirs('/tmp/workspace')
        self.finder = MCP_finder(api_key="dummy_key")

    def test_find_mcp_servers_success(self):
        # Create a list of dummy servers
        server_count = 5
        servers_list = {
            "servers": [
                {"qualifiedName": f"server-{i}", "displayName": f"Server {i}"}
                for i in range(server_count)
            ]
        }

        # Mock response for details
        def side_effect(*args, **kwargs):
            url = kwargs.get('url', '')
            if "/servers" in url and "/servers/" not in url:
                mock_resp = MagicMock()
                mock_resp.json.return_value = servers_list
                mock_resp.raise_for_status.return_value = None
                return mock_resp
            elif "/servers/" in url:
                server_name = url.split('/')[-1]
                mock_resp = MagicMock()
                mock_resp.json.return_value = {
                    "qualifiedName": server_name,
                    "displayName": f"Display {server_name}",
                    "tools": ["tool1", "tool2"]
                }
                mock_resp.raise_for_status.return_value = None
                return mock_resp
            return MagicMock()

        with patch('requests.request', side_effect=side_effect):
            # Search for "server" which should match all mock servers
            results = self.finder.find_mcp_servers("server")

            self.assertEqual(len(results), server_count)
            for i, result in enumerate(results):
                # Since we use executor.map, order should be preserved
                self.assertEqual(result['qualifiedName'], f"server-{i}")

    def test_find_mcp_servers_exception(self):
        # Create a list of dummy servers
        servers_list = {
            "servers": [
                {"qualifiedName": "server-ok", "displayName": "Server OK"},
                {"qualifiedName": "server-fail", "displayName": "Server Fail"}
            ]
        }

        import requests

        # Mock response for details
        def side_effect(*args, **kwargs):
            url = kwargs.get('url', '')
            if "/servers" in url and "/servers/" not in url:
                mock_resp = MagicMock()
                mock_resp.json.return_value = servers_list
                mock_resp.raise_for_status.return_value = None
                return mock_resp
            elif "/servers/server-fail" in url:
                 raise requests.exceptions.RequestException("Fail")
            elif "/servers/" in url:
                mock_resp = MagicMock()
                mock_resp.json.return_value = {"qualifiedName": "server-ok", "tools": []}
                mock_resp.raise_for_status.return_value = None
                return mock_resp
            return MagicMock()

        with patch('requests.request', side_effect=side_effect):
             with self.assertRaises(requests.exceptions.RequestException):
                self.finder.find_mcp_servers("server")

if __name__ == '__main__':
    unittest.main()
