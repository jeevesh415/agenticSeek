import asyncio
from typing import List, Tuple
from sources.utility import pretty_print, animate_thinking
from sources.agents.agent import Agent
from sources.agents.browser_agent import BrowserAgent
from sources.tools.searxSearch import searxSearch
from sources.memory import Memory
from sources.logger import Logger

class ResearchAgent(Agent):
    """
    Research Agent: Designed for deep, autonomous internet research.
    It can perform multiple searches, refine its queries, and synthesize a comprehensive report.
    It is more persistent and detail-oriented than the standard BrowserAgent.
    """
    def __init__(self, name, prompt_path, provider, verbose=False, browser=None):
        super().__init__(name, prompt_path, provider, verbose, browser)
        self.tools = {
            "web_search": searxSearch(),
        }
        self.role = "research"
        self.type = "research_agent"
        self.browser = browser
        self.logger = Logger("research_agent.log")
        # Use a specific prompt if available, otherwise fallback to browser agent prompt
        actual_prompt_path = prompt_path if prompt_path else "prompts/base/research_agent.txt"

        # If the research prompt doesn't exist, we'll create a default one in memory or use browser's
        try:
            prompt_content = self.load_prompt(actual_prompt_path)
        except Exception:
            # Fallback to a hardcoded prompt if file not found
            prompt_content = self.get_default_prompt()

        self.memory = Memory(prompt_content,
                        recover_last_session=False,
                        memory_compression=False,
                        model_provider=provider.get_model_name() if provider else None)
        self.search_history = []
        self.findings = []

    def get_default_prompt(self):
        return """
        You are a Deep Research AI Agent.
        Your goal is to conduct comprehensive, multi-step research on the internet to answer complex user queries.
        You are autonomous, thorough, and objective.

        You have access to:
        1. Web Search: To find information.
        2. Browser: To read webpages (if available).

        Process:
        1. Analyze the user's request.
        2. Formulate a search plan.
        3. Execute searches and gather data.
        4. Read relevant pages to get details.
        5. Refine your search based on findings.
        6. Synthesize all information into a detailed final report.

        Output Format:
        When you need to search, output: SEARCH: <query>
        When you need to read a page (if using browser agent logic): NAVIGATE: <url>
        When you have enough information, output your final report.
        """

    async def process(self, prompt, speech_module) -> str:
        """
        Conducts deep research.
        """
        self.memory.push('user', prompt)
        max_steps = 10
        step = 0

        # We reuse the browser agent logic for navigation if needed,
        # but here we implement a high-level research loop.

        # This is a simplified version of the loop.
        # Ideally, we would delegate to the BrowserAgent for actual navigation,
        # but the ResearchAgent orchestrates the "Deep" part (multiple searches, synthesis).

        # For now, we will wrap the BrowserAgent's capability or implement a loop that uses web_search tool directly
        # and synthesizes.

        research_context = f"Research Task: {prompt}\n\n"

        while step < max_steps and not self.stop:
            await self.wait_message(speech_module)
            animate_thinking(f"Researching (Step {step+1}/{max_steps})...", color="status")

            # Decide next action
            answer, reasoning = await self.llm_request()
            self.last_reasoning = reasoning

            # Check for termination
            if "FINAL REPORT" in answer or "REPORT:" in answer:
                self.last_answer = answer
                return answer, reasoning

            # Check for search command
            if "SEARCH:" in answer:
                query = answer.split("SEARCH:")[1].split("\n")[0].strip()
                pretty_print(f"Deep Research Search: {query}", color="status")

                search_results = self.tools["web_search"].execute([query], False)

                # Add results to memory
                self.memory.push('user', f"Search Results for '{query}':\n{search_results[:2000]}") # Truncate to avoid context overflow

                # Update context
                research_context += f"Search '{query}': Found {len(search_results)} chars of data.\n"
                step += 1
                continue

            # Check for navigation command
            if "NAVIGATE:" in answer:
                url = answer.split("NAVIGATE:")[1].split("\n")[0].strip()
                if self.browser:
                    pretty_print(f"Deep Research Navigation: {url}", color="status")
                    if speech_module: speech_module.speak(f"Navigating to {url}")

                    nav_ok = self.browser.go_to(url)
                    if nav_ok:
                        page_text = self.browser.get_text()
                        # Compress text to avoid context overflow
                        page_text = self.memory.trim_text_to_max_ctx(page_text) if hasattr(self.memory, 'trim_text_to_max_ctx') else page_text[:4000]
                        self.memory.push('user', f"Content of {url}:\n{page_text}")
                        research_context += f"Read {url}.\n"
                    else:
                        self.memory.push('user', f"Failed to navigate to {url}.")
                else:
                    self.memory.push('user', f"Browser tool is not available to navigate to {url}.")
                step += 1
                continue

            # If the model just talks or provides partial info without a clear command, we encourage it to continue or finalize.
            # But if it looks like a final answer, we return it.
            if len(answer) > 500: # detailed answer
                 return answer, reasoning

            step += 1

        return answer, reasoning
