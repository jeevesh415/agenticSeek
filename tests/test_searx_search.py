import unittest
import os
import sys
from unittest.mock import patch, MagicMock
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))  # Add project root to Python path
from sources.tools.searxSearch import searxSearch
from dotenv import load_dotenv
import requests  # Import the requests module

load_dotenv()

class TestSearxSearch(unittest.TestCase):

    def setUp(self):
        os.environ['SEARXNG_BASE_URL'] = "http://127.0.0.1:8080"  # Set the environment variable
        self.base_url = os.getenv("SEARXNG_BASE_URL")
        self.search_tool = searxSearch(base_url=self.base_url)
        self.valid_query = "test query"
        self.invalid_query = ""

    def test_initialization_with_env_variable(self):
        # Ensure the tool initializes correctly with the base URL from the environment variable
        os.environ['SEARXNG_BASE_URL'] = "http://test.example.com"
        search_tool = searxSearch()
        self.assertEqual(search_tool.base_url, "http://test.example.com")
        del os.environ['SEARXNG_BASE_URL']

    def test_initialization_no_base_url(self):
        # Ensure the tool raises an error if no base URL is provided
        # Remove the environment variable to ensure the ValueError is raised
        if 'SEARXNG_BASE_URL' in os.environ:
            del os.environ['SEARXNG_BASE_URL']
        with self.assertRaises(ValueError):
            searxSearch(base_url=None)
        # Restore the environment variable after the test
        os.environ['SEARXNG_BASE_URL'] = "http://searx.lan"

    @patch('sources.tools.searxSearch.requests.post')
    def test_execute_valid_query(self, mock_post):
        # Mock the response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '<html><article class="result"><a class="url_header" href="http://example.com"></a><h3>Test Title</h3><p class="content">Test Snippet</p></article></html>'
        mock_post.return_value = mock_response

        # Execute the search and verify the result
        result = self.search_tool.execute([self.valid_query])
        print(f"Output from test_execute_valid_query: {result}")
        self.assertTrue(isinstance(result, str), "Result should be a string.")
        self.assertIn("Test Title", result)
        self.assertNotEqual(result, "", "Result should not be empty.")

    def test_execute_empty_query(self):
        # Test with an empty query
        result = self.search_tool.execute([""])
        print(f"Output from test_execute_empty_query: {result}")
        self.assertEqual(result, "Error: Empty search query provided.")

    def test_execute_no_query(self):
        # Test with no query provided
        result = self.search_tool.execute([])
        print(f"Output from test_execute_no_query: {result}")
        self.assertEqual(result, "Error: No search query provided.")

    @patch('sources.tools.searxSearch.requests.post')
    def test_execute_request_exception(self, mock_post):
        # Test a request exception
        mock_post.side_effect = requests.exceptions.RequestException("Connection error")

        with self.assertRaises(Exception) as cm:
            self.search_tool.execute([self.valid_query])

        self.assertIn("Searxng search failed", str(cm.exception))

    @patch('sources.tools.searxSearch.requests.post')
    def test_execute_no_results(self, mock_post):
        # Mock response with no results
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '<html><body>No results</body></html>'
        mock_post.return_value = mock_response

        # Execute the search and verify that an empty string is handled correctly
        result = self.search_tool.execute(["nonexistent query that should return no results"])
        print(f"Output from test_execute_no_results: {result}")
        self.assertEqual(result, "No search results, web search failed.")

    def test_execution_failure_check_error(self):
        # Test when the output contains an error
        output = "Error: Something went wrong"
        self.assertTrue(self.search_tool.execution_failure_check(output))

    def test_execution_failure_check_no_error(self):
        # Test when the output does not contain an error
        output = "Search completed successfully"
        self.assertFalse(self.search_tool.execution_failure_check(output))

if __name__ == '__main__':
    unittest.main()
