import unittest
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))  # Add project root to Python path
from sources.tools.searxSearch import searxSearch
from dotenv import load_dotenv
import requests  # Import the requests module
from unittest.mock import patch, MagicMock

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

    @patch('requests.post')
    def test_execute_valid_query(self, mock_post):
        # Mock the response
        mock_response = MagicMock()
        # The tool parses HTML response using BeautifulSoup
        mock_response.text = """
        <html>
            <body>
                <article class="result">
                    <h3>Test Result 1</h3>
                    <a class="url_header" href="http://example.com/1">Link 1</a>
                    <p class="content">Content 1</p>
                </article>
                <article class="result">
                    <h3>Test Result 2</h3>
                    <a class="url_header" href="http://example.com/2">Link 2</a>
                    <p class="content">Content 2</p>
                </article>
            </body>
        </html>
        """
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        # Execute the search and verify the result
        result = self.search_tool.execute([self.valid_query])
        print(f"Output from test_execute_valid_query: {result}")
        self.assertTrue(isinstance(result, str), "Result should be a string.")
        self.assertNotEqual(result, "", "Result should not be empty.")
        self.assertIn("Test Result 1", result)

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

    def test_execute_request_exception(self):
        # Test a request exception by temporarily modifying the base_url to an invalid one
        original_base_url = self.search_tool.base_url
        self.search_tool.base_url = "http://invalid_url"
        try:
            with self.assertRaises(Exception) as cm:
                self.search_tool.execute([self.valid_query])
            self.assertIn("Searxng search failed", str(cm.exception))
        finally:
            self.search_tool.base_url = original_base_url  # Restore the original base_url

    @patch('requests.post')
    def test_execute_no_results(self, mock_post):
        # Mock the response with empty results
        mock_response = MagicMock()
        mock_response.text = "<html><body></body></html>"
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        # Execute the search and verify that an empty string is handled correctly
        result = self.search_tool.execute(["nonexistent query that should return no results"])
        print(f"Output from test_execute_no_results: {result}")
        self.assertTrue(isinstance(result, str), "Result should be a string.")
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
