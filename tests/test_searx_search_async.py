import unittest
from unittest.mock import MagicMock, AsyncMock, patch
import os
import sys
import asyncio
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sources.tools.searxSearch import searxSearch

load_dotenv()

class TestSearxSearchAsync(unittest.TestCase):
    def setUp(self):
        os.environ['SEARXNG_BASE_URL'] = "http://127.0.0.1:8080"
        os.environ['WORK_DIR'] = "/tmp"
        self.search_tool = searxSearch(base_url=os.getenv("SEARXNG_BASE_URL"))

    def test_link_valid_async_success(self):
        async def run_test():
            # Mock the client
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = "This is a valid page content."
            mock_client.get.return_value = mock_response

            status = await self.search_tool.link_valid_async(mock_client, "http://example.com")
            self.assertEqual(status, "Status: OK")

        asyncio.run(run_test())

    def test_link_valid_async_paywall(self):
        async def run_test():
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = "This content is Member-only access denied."
            mock_client.get.return_value = mock_response

            status = await self.search_tool.link_valid_async(mock_client, "http://paywall.com")
            self.assertEqual(status, "Status: Possible Paywall")

        asyncio.run(run_test())

    def test_link_valid_async_404(self):
        async def run_test():
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_client.get.return_value = mock_response

            status = await self.search_tool.link_valid_async(mock_client, "http://notfound.com")
            self.assertEqual(status, "Status: 404 Not Found")

        asyncio.run(run_test())

    @patch('sources.tools.searxSearch.httpx.AsyncClient')
    def test_check_all_links_async(self, mock_async_client_cls):
        async def run_test():
            # Setup mock client instance
            mock_client = AsyncMock()
            # Must set __aenter__ and __aexit__ for context manager
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None

            mock_async_client_cls.return_value = mock_client

            # Setup responses for client.get
            # We have 3 links. client.get will be called 3 times.
            # We can use side_effect to return different responses.

            resp1 = MagicMock()
            resp1.status_code = 200
            resp1.text = "ok content"

            resp2 = MagicMock()
            resp2.status_code = 404

            resp3 = MagicMock()
            resp3.status_code = 200
            resp3.text = "access denied"

            mock_client.get.side_effect = [resp1, resp2, resp3]

            links = ["http://ok.com", "http://404.com", "http://paywall.com"]
            statuses = await self.search_tool.check_all_links(links)

            # Note: asyncio.gather does not guarantee order if we didn't wait for all.
            # But since we await gather(*tasks), and tasks is a list ordered by links,
            # the result of gather is also ordered by the tasks order.

            self.assertEqual(len(statuses), 3)
            self.assertEqual(statuses[0], "Status: OK")
            self.assertEqual(statuses[1], "Status: 404 Not Found")
            self.assertEqual(statuses[2], "Status: Possible Paywall")

        asyncio.run(run_test())

if __name__ == '__main__':
    unittest.main()
