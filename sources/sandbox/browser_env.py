import logging
import json
from typing import Dict, Any, Optional
from sources.sandbox.docker_manager import DockerEnvironmentManager

logger = logging.getLogger(__name__)

class ScalableBrowserEnvironment:
    """
    Layer 3: Browser Automation at Scale.
    Orchestrates headless browser instances (Playwright/Selenium) inside
    dynamic Docker containers. Enables massive parallel web scraping, automated testing,
    and visual-motor interaction without polluting the host or being detected.
    """
    def __init__(self, docker_manager: DockerEnvironmentManager):
        self.docker = docker_manager
        # We use an image with Playwright and browsers pre-installed
        self.browser_image = "mcr.microsoft.com/playwright/python:v1.44.0-jammy"

    def spawn_browser_env(self, env_id: str, proxy: Optional[str] = None) -> Dict[str, Any]:
        """
        Spawns a specialized Docker container pre-configured for headless browsing.
        """
        logger.info(f"[BrowserEnv] Spawning Playwright container '{env_id}'...")

        # We allow internet access for browsers
        res = self.docker.spawn_environment(
            env_id=f"browser_{env_id}",
            image=self.browser_image,
            cpu_limit=1.0,
            mem_limit="1g",
            network_disabled=False
        )

        if res.get("status") == "running":
            logger.info(f"[BrowserEnv] Successfully started Playwright container {res['name']}.")
            # Install necessary python dependencies if the base image lacks them
            # playwright install is already handled in the mcr image
            self.docker.execute_code(env_id=f"browser_{env_id}", code="import os; os.system('pip install beautifulsoup4 pytest-playwright')")

        return res

    def scrape_url(self, env_id: str, url: str, extract_selector: str = "body") -> str:
        """
        Generates Playwright Python code, executes it inside the remote container,
        and returns the extracted text/HTML.
        """
        playwright_script = f"""
import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto('{url}', timeout=30000)
            # Wait for network idle or domcontentloaded
            await page.wait_for_load_state('domcontentloaded')
            element = await page.query_selector('{extract_selector}')
            if element:
                text = await element.inner_text()
                print(text[:2000]) # Truncate to avoid massive outputs
            else:
                print('Error: Selector not found.')
        except Exception as e:
            print(f'Playwright Error: {{e}}')
        finally:
            await browser.close()

asyncio.run(run())
"""
        logger.info(f"[BrowserEnv] Executing Playwright script in '{env_id}' to scrape '{url}'")
        output = self.docker.execute_code(env_id=f"browser_{env_id}", code=playwright_script, timeout=60)
        return output

    def destroy_browser_env(self, env_id: str) -> bool:
        """Tears down the headless browser container."""
        return self.docker.destroy_environment(env_id=f"browser_{env_id}")
