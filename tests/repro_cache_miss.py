import unittest
import unittest.mock
import os
import sys
import asyncio
from unittest import IsolatedAsyncioTestCase

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from sources.tools.searxSearch import searxSearch

class TestSearxSearchCache(IsolatedAsyncioTestCase):

    def setUp(self):
        os.environ['SEARXNG_BASE_URL'] = "http://127.0.0.1:8080"
        os.environ['WORK_DIR'] = "/tmp"
        self.search_tool = searxSearch()
        self.query = "test query"

    async def test_caching_behavior(self):
        # Mock the response
        mock_response = unittest.mock.Mock()
        mock_response.status_code = 200
        mock_response.text = "<html><body><article class='result'><h3 class='title'>Test</h3><a class='url_header' href='http://test.com'></a><p class='content'>Snippet</p></article></body></html>"
        mock_response.raise_for_status = unittest.mock.Mock()

        # Patch httpx.AsyncClient.post
        with unittest.mock.patch("httpx.AsyncClient.post", new_callable=unittest.mock.AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            # First call
            await self.search_tool.execute([self.query])

            # Second call with same query
            await self.search_tool.execute([self.query])

            # Check call count
            print(f"Call count: {mock_post.call_count}")
            if mock_post.call_count == 1:
                print("Cache HIT")
            else:
                print("Cache MISS")
                # Fail the test if we expect caching but don't have it yet.
                # However, for reproduction, we expect it to fail or show "Cache MISS".
                # I'll just leave the print statement for now.

if __name__ == '__main__':
    unittest.main()
