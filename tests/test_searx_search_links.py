import unittest
import os
import sys
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sources.tools.searxSearch import searxSearch

class TestSearxSearchLinks(unittest.TestCase):
    def setUp(self):
        os.environ['SEARXNG_BASE_URL'] = "http://mock.url"
        os.environ['WORK_DIR'] = "/tmp"
        self.tool = searxSearch(base_url="http://mock.url")

    def test_check_all_links_async(self):
        # Mock httpx response
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "content"

        # AsyncMock for client.get
        mock_get = AsyncMock(return_value=mock_resp)

        links = ["http://link1.com", "http://link2.com"]

        # Patch httpx.AsyncClient
        with patch('httpx.AsyncClient') as mock_client_cls:
            mock_client_instance = mock_client_cls.return_value
            mock_client_instance.__aenter__.return_value = mock_client_instance
            mock_client_instance.get = mock_get

            # Since check_all_links runs async loop, we can call it directly
            results = self.tool.check_all_links(links)

            self.assertEqual(len(results), 2)
            self.assertEqual(results[0], "Status: OK")
            self.assertEqual(results[1], "Status: OK")

            # Verify concurrent calls: we can't easily check concurrency with mocks,
            # but we can check call count
            self.assertEqual(mock_get.call_count, 2)

    def test_link_valid_async_paywall(self):
        # Test paywall detection
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "Access Denied"

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp

        result = asyncio.run(self.tool.link_valid_async(mock_client, "http://paywall.com"))
        self.assertEqual(result, "Status: Possible Paywall")

    def test_link_valid_async_404(self):
        # Test 404
        mock_resp = MagicMock()
        mock_resp.status_code = 404

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp

        result = asyncio.run(self.tool.link_valid_async(mock_client, "http://404.com"))
        self.assertEqual(result, "Status: 404 Not Found")

if __name__ == '__main__':
    unittest.main()
