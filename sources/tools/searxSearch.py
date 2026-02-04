import requests
from bs4 import BeautifulSoup
import os
import concurrent.futures
from urllib.parse import urlparse
import sys

if __name__ == "__main__": # if running as a script for individual testing
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sources.tools.tools import Tools

class searxSearch(Tools):
    def __init__(self, base_url: str = None):
        """
        A tool for searching a SearxNG instance and extracting URLs and titles.
        """
        super().__init__()
        self.tag = "web_search"
        self.name = "searxSearch"
        self.description = "A tool for searching a SearxNG for web search"
        self.base_url = base_url or os.getenv("SEARXNG_BASE_URL")  # Requires a SearxNG base URL
        self.user_agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
        self.paywall_keywords = [
            "Member-only", "access denied", "restricted content", "404", "this page is not working"
        ]
        if not self.base_url:
            raise ValueError("SearxNG base URL must be provided either as an argument or via the SEARXNG_BASE_URL environment variable.")

    def link_valid(self, link, session=None):
        """check if a link is valid."""
        try:
            parsed = urlparse(link)
            if not parsed.scheme or not parsed.netloc or parsed.scheme not in ['http', 'https']:
                 return "Status: Invalid URL"
        except Exception:
            return "Status: Invalid URL"
        
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        requester = session if session else requests

        try:
            # Try HEAD first to check status efficiently
            try:
                response = requester.head(link, headers=headers, timeout=5, allow_redirects=True)
                status = response.status_code
            except requests.exceptions.RequestException:
                # If HEAD fails, it might be a connection issue or timeout.
                # In some cases, servers block HEAD but allow GET.
                # We can try GET as a fallback.
                response = requester.get(link, headers=headers, timeout=5, stream=True)
                status = response.status_code

            # Handle 405 Method Not Allowed (some servers block HEAD)
            if status == 405:
                response = requester.get(link, headers=headers, timeout=5, stream=True)
                status = response.status_code

            if status == 200:
                # If the successful request was a HEAD request, we need to GET the body to check for paywalls.
                if response.request.method == 'HEAD':
                     response = requester.get(link, headers=headers, timeout=5, stream=True)
                     status = response.status_code
                     if status != 200:
                        if status == 404:
                            return "Status: 404 Not Found"
                        elif status == 403:
                            return "Status: 403 Forbidden"
                        else:
                            return f"Status: {status} {response.reason}"

                # Check for paywall keywords in the first 4KB of content
                content = ""
                try:
                    for chunk in response.iter_content(chunk_size=1024, decode_unicode=True):
                        if chunk:
                            content += chunk
                        if len(content) > 4096:
                            break
                except Exception:
                    # Ignore decoding errors, process what we have
                    pass

                content = content.lower()
                if any(keyword in content for keyword in self.paywall_keywords):
                    return "Status: Possible Paywall"
                return "Status: OK"
            elif status == 404:
                return "Status: 404 Not Found"
            elif status == 403:
                return "Status: 403 Forbidden"
            else:
                return f"Status: {status} {response.reason}"
        except requests.exceptions.RequestException as e:
            return f"Error: {str(e)}"

    def check_all_links(self, links):
        """Check all links, one by one."""
        with requests.Session() as session:
            # Set headers for session to look like a browser
            session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})

            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                # Use executor.map to preserve order
                results = executor.map(lambda l: self.link_valid(l, session), links)
                return list(results)
    
    def execute(self, blocks: list, safety: bool = False) -> str:
        """Executes a search query against a SearxNG instance using POST and extracts URLs and titles."""
        if not blocks:
            return "Error: No search query provided."

        query = blocks[0].strip()
        if not query:
            return "Error: Empty search query provided."

        search_url = f"{self.base_url}/search"
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Pragma': 'no-cache',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': self.user_agent
        }
        data = f"q={query}&categories=general&language=auto&time_range=&safesearch=0&theme=simple".encode('utf-8')
        try:
            response = requests.post(search_url, headers=headers, data=data, verify=False)
            response.raise_for_status()
            html_content = response.text
            soup = BeautifulSoup(html_content, 'html.parser')
            results = []
            for article in soup.find_all('article', class_='result'):
                url_header = article.find('a', class_='url_header')
                if url_header:
                    url = url_header['href']
                    title = article.find('h3').text.strip() if article.find('h3') else "No Title"
                    description = article.find('p', class_='content').text.strip() if article.find('p', class_='content') else "No Description"
                    results.append(f"Title:{title}\nSnippet:{description}\nLink:{url}")
            if len(results) == 0:
                return "No search results, web search failed."
            return "\n\n".join(results)  # Return results as a single string, separated by newlines
        except requests.exceptions.RequestException as e:
            raise Exception("\nSearxng search failed. did you run start_services.sh? is docker still running?") from e

    def execution_failure_check(self, output: str) -> bool:
        """
        Checks if the execution failed based on the output.
        """
        return "Error" in output

    def interpreter_feedback(self, output: str) -> str:
        """
        Feedback of web search to agent.
        """
        if self.execution_failure_check(output):
            return f"Web search failed: {output}"
        return f"Web search result:\n{output}"

if __name__ == "__main__":
    search_tool = searxSearch(base_url="http://127.0.0.1:8080")
    result = search_tool.execute(["are dog better than cat?"])
    print(result)
