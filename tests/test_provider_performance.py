
import unittest
from unittest.mock import patch, MagicMock
import os, sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sources.llm_provider import Provider

class TestProviderPerformance(unittest.TestCase):
    def setUp(self):
        self.provider = Provider("server", "test-model", server_address="127.0.0.1:5000", is_local=False)

    @patch('sources.llm_provider.requests')
    @patch('sources.llm_provider.time.sleep')
    @patch.object(Provider, 'is_ip_online', return_value=True)
    def test_server_fn_no_sleep_when_complete(self, mock_is_ip_online, mock_sleep, mock_requests):
        """Test that sleep is skipped if the response is already complete."""
        # Setup mocks
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "sentence": "Hello world",
            "is_complete": True
        }
        mock_requests.get.return_value = mock_response

        # Call the function
        self.provider.server_fn(["user", "hi"])

        # Verification
        mock_sleep.assert_not_called()
        print("\nVerified: time.sleep was NOT called for immediate completion.")

    @patch('sources.llm_provider.requests')
    @patch('sources.llm_provider.time.sleep')
    @patch.object(Provider, 'is_ip_online', return_value=True)
    def test_server_fn_reduced_sleep_when_incomplete(self, mock_is_ip_online, mock_sleep, mock_requests):
        """Test that sleep is 0.1s if the response is incomplete."""
        # Setup mocks
        mock_response_incomplete = MagicMock()
        mock_response_incomplete.json.return_value = {
            "sentence": "Hello",
            "is_complete": False
        }
        mock_response_complete = MagicMock()
        mock_response_complete.json.return_value = {
            "sentence": "Hello world",
            "is_complete": True
        }

        # Sequence of side effects: incomplete, then complete
        mock_requests.get.side_effect = [mock_response_incomplete, mock_response_complete]

        # Call the function
        self.provider.server_fn(["user", "hi"])

        # Verification
        mock_sleep.assert_called_with(0.1)
        self.assertEqual(mock_sleep.call_count, 1)
        print("\nVerified: time.sleep(0.1) was called for incomplete response.")

if __name__ == '__main__':
    unittest.main()
