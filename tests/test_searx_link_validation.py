import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import requests

# Add sources to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sources.tools.searxSearch import searxSearch

class TestSearxLinkValidation(unittest.TestCase):
    def setUp(self):
        os.environ["WORK_DIR"] = "/tmp"
        os.environ["SEARXNG_BASE_URL"] = "http://mock-searxng"
        self.tool = searxSearch()

    def tearDown(self):
        if "WORK_DIR" in os.environ:
            del os.environ["WORK_DIR"]
        if "SEARXNG_BASE_URL" in os.environ:
            del os.environ["SEARXNG_BASE_URL"]

    @patch('sources.tools.searxSearch.requests.head')
    @patch('sources.tools.searxSearch.requests.get')
    def test_link_valid_200_ok(self, mock_get, mock_head):
        # HEAD returns 200
        mock_head_resp = MagicMock()
        mock_head_resp.status_code = 200
        mock_head_resp.request.method = 'HEAD'
        mock_head.return_value = mock_head_resp

        # GET returns content (since HEAD succeeded, it does GET for paywall check)
        mock_get_resp = MagicMock()
        mock_get_resp.status_code = 200
        mock_get_resp.iter_content.return_value = ["This is a normal page."]
        mock_get.return_value = mock_get_resp

        result = self.tool.link_valid("http://example.com")
        self.assertEqual(result, "Status: OK")
        mock_head.assert_called_once()
        mock_get.assert_called_once()

    @patch('sources.tools.searxSearch.requests.head')
    @patch('sources.tools.searxSearch.requests.get')
    def test_link_valid_paywall(self, mock_get, mock_head):
        # HEAD returns 200
        mock_head_resp = MagicMock()
        mock_head_resp.status_code = 200
        mock_head_resp.request.method = 'HEAD'
        mock_head.return_value = mock_head_resp

        # GET returns content with paywall
        mock_get_resp = MagicMock()
        mock_get_resp.status_code = 200
        mock_get_resp.iter_content.return_value = ["This content is restricted content."]
        mock_get.return_value = mock_get_resp

        result = self.tool.link_valid("http://example.com")
        self.assertEqual(result, "Status: Possible Paywall")

    @patch('sources.tools.searxSearch.requests.head')
    def test_link_valid_404(self, mock_head):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_head.return_value = mock_response

        result = self.tool.link_valid("http://example.com/notfound")
        self.assertEqual(result, "Status: 404 Not Found")

    def test_link_valid_invalid_url(self):
        result = self.tool.link_valid("ftp://example.com")
        self.assertEqual(result, "Status: Invalid URL")

    @patch('sources.tools.searxSearch.requests.head')
    @patch('sources.tools.searxSearch.requests.get')
    def test_link_valid_head_fail_get_ok(self, mock_get, mock_head):
        # HEAD raises exception
        mock_head.side_effect = requests.exceptions.RequestException("Connection error")

        # GET succeeds
        mock_get_resp = MagicMock()
        mock_get_resp.status_code = 200
        mock_get_resp.iter_content.return_value = ["content"]
        mock_get.return_value = mock_get_resp

        result = self.tool.link_valid("http://example.com")
        self.assertEqual(result, "Status: OK")

    @patch('sources.tools.searxSearch.requests.head')
    @patch('sources.tools.searxSearch.requests.get')
    def test_link_valid_head_ok_get_404(self, mock_get, mock_head):
        # HEAD returns 200
        mock_head_resp = MagicMock()
        mock_head_resp.status_code = 200
        mock_head_resp.request.method = 'HEAD'
        mock_head.return_value = mock_head_resp

        # GET returns 404
        mock_get_resp = MagicMock()
        mock_get_resp.status_code = 404
        mock_get.return_value = mock_get_resp

        result = self.tool.link_valid("http://example.com/ghost")
        self.assertEqual(result, "Status: 404 Not Found")

    @patch('sources.tools.searxSearch.requests.Session')
    def test_check_all_links(self, mock_session_cls):
        # Mock Session instance
        mock_session = mock_session_cls.return_value
        mock_session.__enter__.return_value = mock_session

        def head_side_effect(url, headers=None, timeout=None, allow_redirects=True):
            resp = MagicMock()
            resp.request.method = 'HEAD'
            if "ok" in url:
                resp.status_code = 200
            elif "404" in url:
                resp.status_code = 404
            return resp

        mock_session.head.side_effect = head_side_effect

        def get_side_effect(url, headers=None, timeout=None, stream=True):
            resp = MagicMock()
            if "ok" in url:
                resp.status_code = 200
                resp.iter_content.return_value = ["ok"]
            return resp

        mock_session.get.side_effect = get_side_effect

        links = ["http://ok.com", "http://404.com"]
        statuses = self.tool.check_all_links(links)

        # Order should be preserved
        self.assertEqual(statuses, ["Status: OK", "Status: 404 Not Found"])

        # Verify call counts
        self.assertEqual(mock_session.head.call_count, 2)
        # GET is called only for the OK link (to check paywall)
        self.assertEqual(mock_session.get.call_count, 1)

if __name__ == '__main__':
    unittest.main()
