import os
import dotenv
import asyncio
import httpx
import threading

dotenv.load_dotenv()

from sources.tools.tools import Tools
from sources.utility import animate_thinking, pretty_print

"""
WARNING
webSearch is fully deprecated and is being replaced by searxSearch for web search.
"""

class webSearch(Tools):
    def __init__(self, api_key: str = None):
        """
        A tool to perform a Google search and return information from the first result.
        """
        super().__init__()
        self.tag = "web_search"
        self.api_key = api_key or os.getenv("SERPAPI_KEY")  # Requires a SerpApi key
        self.paywall_keywords = [
            "subscribe", "login to continue", "access denied", "restricted content", "404", "this page is not working"
        ]

    async def link_valid_async(self, client, link):
        """check if a link is valid asynchronously."""
        if not link.startswith("http"):
            return "Status: Invalid URL"
        
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        try:
            # Follow redirects to match requests behavior
            response = await client.get(link, headers=headers, timeout=5, follow_redirects=True)
            status = response.status_code
            if status == 200:
                content = response.text[:1000].lower()
                if any(keyword in content for keyword in self.paywall_keywords):
                    return "Status: Possible Paywall"
                return "Status: OK"
            elif status == 404:
                return "Status: 404 Not Found"
            elif status == 403:
                return "Status: 403 Forbidden"
            else:
                return f"Status: {status} {response.reason_phrase}"
        except Exception as e:
            return f"Error: {str(e)}"

    async def check_all_links_async(self, links):
        """Async implementation of checking all links."""
        async with httpx.AsyncClient(verify=True) as client:
            tasks = [self.link_valid_async(client, link) for link in links]
            return await asyncio.gather(*tasks)

    def _run_async(self, coro):
        """Helper to run async code from a sync context."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # If we are in a running loop, we must run the new loop in a separate thread
            result = []
            def run_in_thread():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    res = new_loop.run_until_complete(coro)
                    result.append(res)
                finally:
                    new_loop.close()

            t = threading.Thread(target=run_in_thread)
            t.start()
            t.join()
            return result[0]
        else:
            return asyncio.run(coro)

    def check_all_links(self, links):
        """Check all links, one by one (asynchronously)."""
        return self._run_async(self.check_all_links_async(links))

    def execute(self, blocks: str, safety: bool = True) -> str:
        if self.api_key is None:
            return "Error: No SerpApi key provided."
        for block in blocks:
            query = block.strip()
            pretty_print(f"Searching for: {query}", color="status")
            if not query:
                return "Error: No search query provided."

            try:
                url = "https://serpapi.com/search"
                params = {
                    "q": query,
                    "api_key": self.api_key,
                    "num": 50,
                    "output": "json"
                }

                async def fetch_search_results():
                    async with httpx.AsyncClient(http2=True, verify=True) as client:
                        resp = await client.get(url, params=params, timeout=10.0)
                        resp.raise_for_status()
                        return resp.json()

                data = self._run_async(fetch_search_results())
                results = []
                if "organic_results" in data and len(data["organic_results"]) > 0:
                    organic_results = data["organic_results"][:50]
                    links = [result.get("link", "No link available") for result in organic_results]
                    statuses = self.check_all_links(links)
                    for result, status in zip(organic_results, statuses):
                        if not "OK" in status:
                            continue
                        title = result.get("title", "No title")
                        snippet = result.get("snippet", "No snippet available")
                        link = result.get("link", "No link available")
                        results.append(f"Title:{title}\nSnippet:{snippet}\nLink:{link}")
                    return "\n\n".join(results)
                else:
                    return "No results found for the query."
            except httpx.HTTPError as e:
                return f"Error during web search: {str(e)}"
            except Exception as e:
                return f"Unexpected error: {str(e)}"
        return "No search performed"

    def execution_failure_check(self, output: str) -> bool:
        return output.startswith("Error") or "No results found" in output

    def interpreter_feedback(self, output: str) -> str:
        if self.execution_failure_check(output):
            return f"Web search failed: {output}"
        return f"Web search result:\n{output}"


if __name__ == "__main__":
    search_tool = webSearch(api_key=os.getenv("SERPAPI_KEY"))
    query = "when did covid start"
    result = search_tool.execute([query], safety=True)
    output = search_tool.interpreter_feedback(result)
    print(output)
