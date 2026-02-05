import unittest
import unittest.mock
import asyncio
import httpx
from sources.tools.searxSearch import searxSearch
from unittest import IsolatedAsyncioTestCase
import os

class TestSearxLinkValidation(IsolatedAsyncioTestCase):
    def setUp(self):
        os.environ['WORK_DIR'] = "/tmp"
        os.environ['SEARXNG_BASE_URL'] = "http://127.0.0.1:8080"
        self.search_tool = searxSearch()

    async def test_check_all_links_async(self):
        links = ["http://example.com/1", "http://example.com/2"]

        # Mock httpx.AsyncClient
        with unittest.mock.patch("httpx.AsyncClient") as MockClient:
            mock_client_instance = MockClient.return_value
            mock_client_instance.__aenter__.return_value = mock_client_instance

            # Mock get responses
            async def side_effect(url, **kwargs):
                mock_response = unittest.mock.Mock()
                mock_response.status_code = 200
                mock_response.text = "ok content"
                mock_response.reason_phrase = "OK"
                if "paywall" in url:
                     mock_response.text = "Member-only content"
                elif "404" in url:
                    mock_response.status_code = 404
                    mock_response.reason_phrase = "Not Found"
                return mock_response

            mock_client_instance.get.side_effect = side_effect

            # We expect check_all_links to be async now
            statuses = await self.search_tool.check_all_links(links)

            self.assertEqual(len(statuses), 2)
            self.assertEqual(statuses[0], "Status: OK")
            self.assertEqual(statuses[1], "Status: OK")

    async def test_check_paywall(self):
        links = ["http://paywall.com"]
        with unittest.mock.patch("httpx.AsyncClient") as MockClient:
            mock_client_instance = MockClient.return_value
            mock_client_instance.__aenter__.return_value = mock_client_instance

            async def side_effect(url, **kwargs):
                mock_response = unittest.mock.Mock()
                mock_response.status_code = 200
                mock_response.text = "Member-only content"
                mock_response.reason_phrase = "OK"
                return mock_response

            mock_client_instance.get.side_effect = side_effect

            statuses = await self.search_tool.check_all_links(links)
            self.assertEqual(statuses[0], "Status: Possible Paywall")

    async def test_check_404(self):
        links = ["http://example.com/404"]
        with unittest.mock.patch("httpx.AsyncClient") as MockClient:
            mock_client_instance = MockClient.return_value
            mock_client_instance.__aenter__.return_value = mock_client_instance

            async def side_effect(url, **kwargs):
                mock_response = unittest.mock.Mock()
                mock_response.status_code = 404
                mock_response.reason_phrase = "Not Found"
                return mock_response

            mock_client_instance.get.side_effect = side_effect

            statuses = await self.search_tool.check_all_links(links)
            self.assertEqual(statuses[0], "Status: 404 Not Found")

    async def test_check_exception(self):
        links = ["http://error.com"]
        with unittest.mock.patch("httpx.AsyncClient") as MockClient:
            mock_client_instance = MockClient.return_value
            mock_client_instance.__aenter__.return_value = mock_client_instance

            async def side_effect(url, **kwargs):
                raise httpx.RequestError("Mock Error", request=None)

            mock_client_instance.get.side_effect = side_effect

            statuses = await self.search_tool.check_all_links(links)
            self.assertTrue("Error: Mock Error" in statuses[0])
