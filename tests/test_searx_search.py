import unittest
import unittest.mock
import os
import sys
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

    def test_execute_valid_query(self):
        # Execute the search and verify the result
        with unittest.mock.patch('requests.post') as mock_post:
            mock_response = unittest.mock.Mock()
            mock_response.status_code = 200
            mock_response.text = '<html><body><article class="result"><a class="url_header" href="http://example.com"></a><h3>Title</h3><p class="content">Snippet</p></article></body></html>'
            mock_post.return_value = mock_response

            result = self.search_tool.execute([self.valid_query])
            print(f"Output from test_execute_valid_query: {result}")
            self.assertTrue(isinstance(result, str), "Result should be a string.")
            self.assertIn("Title:Title", result)
            self.assertNotEqual(result, "", "Result should not be empty. Check SearxNG instance.")

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
            with unittest.mock.patch('requests.post') as mock_post:
                mock_post.side_effect = requests.exceptions.ConnectionError("Connection error")

                # We expect an Exception to be raised by execute
                with self.assertRaises(Exception) as cm:
                    self.search_tool.execute([self.valid_query])

                self.assertIn("Searxng search failed", str(cm.exception))
        finally:
            self.search_tool.base_url = original_base_url  # Restore the original base_url

    def test_execute_no_results(self):
        # Execute the search and verify that an empty string is handled correctly
        with unittest.mock.patch('requests.post') as mock_post:
            mock_response = unittest.mock.Mock()
            mock_response.status_code = 200
            mock_response.text = '<html><body></body></html>' # No articles
            mock_post.return_value = mock_response

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

    def test_check_all_links(self):
        # Mock requests.get to return specific statuses for different URLs
        with unittest.mock.patch('requests.get') as mock_get:
            def side_effect(url, headers=None, timeout=None):
                mock_response = unittest.mock.Mock()
                mock_response.text = "content"
                if "200" in url:
                    mock_response.status_code = 200
                    return mock_response
                elif "404" in url:
                    mock_response.status_code = 404
                    return mock_response
                elif "error" in url:
                    raise requests.exceptions.RequestException("Connection error")
                else:
                    mock_response.status_code = 500
                    mock_response.reason = "Internal Server Error"
                    return mock_response

            mock_get.side_effect = side_effect

            links = [
                "http://example.com/200",
                "http://example.com/404",
                "http://example.com/error",
                "http://example.com/500",
                "invalid_url"
            ]

            statuses = self.search_tool.check_all_links(links)

            expected_statuses = [
                "Status: OK",
                "Status: 404 Not Found",
                "Error: Connection error",
                "Status: 500 Internal Server Error",
                "Status: Invalid URL"
            ]

            self.assertEqual(statuses, expected_statuses)

if __name__ == '__main__':
    unittest.main()
