import os
import platform
import socket
import subprocess
import time
import json
from urllib.parse import urlparse

import httpx
import requests
from dotenv import load_dotenv
from ollama import Client as OllamaClient
from openai import OpenAI

from sources.logger import Logger
from sources.utility import pretty_print, animate_thinking

class Provider:
    METRICS_CACHE_PATH = os.path.join(".logs", "provider_metrics.json")

    def __init__(self, provider_name, model, server_address="127.0.0.1:5000", is_local=False):
        self.provider_name = provider_name.lower()
        self.model = model
        self.is_local = is_local
        self.server_ip = server_address
        self.server_address = server_address
        self.available_providers = {
            "ollama": self.ollama_fn,
            "server": self.server_fn,
            "openai": self.openai_fn,
            "lm-studio": self.lm_studio_fn,
            "huggingface": self.huggingface_fn,
            "google": self.google_fn,
            "deepseek": self.deepseek_fn,
            "together": self.together_fn,
            "dsk_deepseek": self.dsk_deepseek,
            "openrouter": self.openrouter_fn,
            "sapient_hrm": self.sapient_hrm_fn,
            "colab": self.colab_fn,
            "auto": self.auto_fn,
            "test": self.test_fn
        }
        self.logger = Logger("provider.log")
        self.api_key = None
        self.internal_url, self.in_docker = self.get_internal_url()
        self.unsafe_providers = ["openai", "deepseek", "dsk_deepseek", "together", "google", "openrouter", "sapient_hrm"]
        self.provider_profiles = {
            "ollama": {"task_types": ["coding", "analysis", "chat"], "context_window": 32768, "priority": 1.0},
            "lm-studio": {"task_types": ["coding", "analysis", "chat"], "context_window": 32768, "priority": 0.9},
            "server": {"task_types": ["coding", "analysis", "chat"], "context_window": 65536, "priority": 1.0},
            "openai": {"task_types": ["coding", "analysis", "chat"], "context_window": 128000, "priority": 0.85},
            "huggingface": {"task_types": ["chat", "analysis"], "context_window": 8192, "priority": 0.65},
            "google": {"task_types": ["analysis", "chat"], "context_window": 32000, "priority": 0.8},
            "deepseek": {"task_types": ["coding", "analysis"], "context_window": 64000, "priority": 0.8},
            "together": {"task_types": ["coding", "analysis", "chat"], "context_window": 32000, "priority": 0.75},
            "dsk_deepseek": {"task_types": ["coding", "analysis", "chat"], "context_window": 16000, "priority": 0.6},
            "openrouter": {"task_types": ["coding", "analysis", "chat"], "context_window": 128000, "priority": 0.8},
            "sapient_hrm": {"task_types": ["analysis", "chat"], "context_window": 16000, "priority": 0.6},
            "colab": {"task_types": ["coding", "analysis"], "context_window": 32000, "priority": 0.7},
            "test": {"task_types": ["chat"], "context_window": 2048, "priority": 0.1},
        }
        self.circuit_breaker = {
            "failure_threshold": 3,
            "cooldown_seconds": 45,
            "base_backoff_seconds": 1.0,
            "max_backoff_seconds": 16.0,
        }
        self.routing_weights = {
            "success_rate": 0.45,
            "latency": 0.30,
            "task_fit": 0.15,
            "context_fit": 0.10,
        }
        self.metrics_cache = self.load_metrics_cache()
        if self.provider_name not in self.available_providers:
            raise ValueError(f"Unknown provider: {provider_name}")
        if self.provider_name in self.unsafe_providers and self.is_local == False:
            pretty_print("Warning: you are using an API provider. You data will be sent to the cloud.", color="warning")
            self.api_key = self.get_api_key(self.provider_name)
        elif self.provider_name != "ollama":
            pretty_print(f"Provider: {provider_name} initialized at {self.server_ip}", color="success")

    def get_model_name(self) -> str:
        return self.model

    def get_api_key(self, provider):
        load_dotenv()
        api_key_var = f"{provider.upper()}_API_KEY"
        api_key = os.getenv(api_key_var)
        if not api_key:
            pretty_print(f"API key {api_key_var} not found in .env file. Please add it", color="warning")
            exit(1)
        return api_key
    
    def get_internal_url(self):
        load_dotenv()
        url = os.getenv("DOCKER_INTERNAL_URL")
        if not url: # running on host
            return "http://localhost", False
        return url, True

    def load_metrics_cache(self):
        default_metrics = {}
        for provider in self.available_providers:
            if provider == "auto":
                continue
            default_metrics[provider] = {
                "attempts": 0,
                "successes": 0,
                "errors": 0,
                "total_latency": 0.0,
                "avg_latency": 0.0,
                "consecutive_failures": 0,
                "circuit_open_until": 0.0,
            }

        try:
            if os.path.exists(self.METRICS_CACHE_PATH):
                with open(self.METRICS_CACHE_PATH, "r", encoding="utf-8") as metrics_file:
                    cached_metrics = json.load(metrics_file)
                if isinstance(cached_metrics, dict):
                    for provider, defaults in default_metrics.items():
                        defaults.update(cached_metrics.get(provider, {}))
            else:
                self.logger.info(f"Metrics cache not found at {self.METRICS_CACHE_PATH}; creating new cache")
        except Exception as cache_error:
            self.logger.warning(f"Failed to load metrics cache: {cache_error}. Using default metrics")
        self.persist_metrics_cache(default_metrics)
        return default_metrics

    def persist_metrics_cache(self, metrics=None):
        to_persist = metrics if metrics is not None else self.metrics_cache
        try:
            os.makedirs(os.path.dirname(self.METRICS_CACHE_PATH), exist_ok=True)
            with open(self.METRICS_CACHE_PATH, "w", encoding="utf-8") as metrics_file:
                json.dump(to_persist, metrics_file, indent=2)
        except Exception as cache_error:
            self.logger.warning(f"Failed to persist metrics cache: {cache_error}")

    def estimate_context_tokens(self, history):
        total_chars = sum(len(msg.get("content", "")) for msg in history if isinstance(msg, dict))
        return max(1, total_chars // 4)

    def infer_task_type(self, history):
        text = " ".join(msg.get("content", "").lower() for msg in history if isinstance(msg, dict))
        if any(keyword in text for keyword in ["code", "python", "debug", "function", "test", "bug"]):
            return "coding"
        if any(keyword in text for keyword in ["analyze", "summarize", "compare", "research", "plan"]):
            return "analysis"
        return "chat"

    def is_circuit_open(self, provider_name):
        provider_metrics = self.metrics_cache.get(provider_name, {})
        return time.time() < provider_metrics.get("circuit_open_until", 0.0)

    def update_metrics(self, provider_name, success, latency, error_message=None):
        provider_metrics = self.metrics_cache.get(provider_name)
        if provider_metrics is None:
            return

        provider_metrics["attempts"] += 1
        provider_metrics["total_latency"] += max(latency, 0)
        provider_metrics["avg_latency"] = provider_metrics["total_latency"] / max(provider_metrics["attempts"], 1)

        if success:
            provider_metrics["successes"] += 1
            provider_metrics["consecutive_failures"] = 0
            provider_metrics["circuit_open_until"] = 0.0
        else:
            provider_metrics["errors"] += 1
            provider_metrics["consecutive_failures"] += 1
            failures = provider_metrics["consecutive_failures"]
            if failures >= self.circuit_breaker["failure_threshold"]:
                backoff = min(
                    self.circuit_breaker["base_backoff_seconds"] * (2 ** (failures - self.circuit_breaker["failure_threshold"])),
                    self.circuit_breaker["max_backoff_seconds"],
                )
                provider_metrics["circuit_open_until"] = time.time() + self.circuit_breaker["cooldown_seconds"] + backoff
                self.logger.warning(
                    f"Circuit opened for provider {provider_name} for {self.circuit_breaker['cooldown_seconds'] + backoff:.1f}s"
                )
            if error_message:
                self.logger.warning(f"Provider {provider_name} failed: {error_message}")

        self.persist_metrics_cache()

    def compute_provider_score(self, provider_name, task_type, required_context_tokens):
        profile = self.provider_profiles.get(provider_name, {})
        metrics = self.metrics_cache.get(provider_name, {})
        attempts = max(metrics.get("attempts", 0), 1)
        success_rate = metrics.get("successes", 0) / attempts
        avg_latency = metrics.get("avg_latency", 0.0)
        latency_score = 1 / (1 + avg_latency) if avg_latency > 0 else 1.0

        task_score = 1.0 if task_type in profile.get("task_types", []) else 0.35
        context_window = profile.get("context_window", 4096)
        if context_window >= required_context_tokens:
            context_score = 1.0
        else:
            context_score = max(context_window / max(required_context_tokens, 1), 0.1)

        weighted_score = (
            self.routing_weights["success_rate"] * success_rate
            + self.routing_weights["latency"] * latency_score
            + self.routing_weights["task_fit"] * task_score
            + self.routing_weights["context_fit"] * context_score
        )
        weighted_score *= profile.get("priority", 0.5)
        return weighted_score

    def rank_providers(self, providers, task_type, required_context_tokens):
        scored = []
        for provider_name in providers:
            if self.is_circuit_open(provider_name):
                self.logger.info(f"Routing skip: provider={provider_name}, reason=circuit_open")
                continue
            score = self.compute_provider_score(provider_name, task_type, required_context_tokens)
            self.logger.info(
                f"Routing score: provider={provider_name}, score={score:.4f}, task={task_type}, context={required_context_tokens}"
            )
            scored.append((provider_name, score))
        scored.sort(key=lambda item: item[1], reverse=True)
        return [provider for provider, _ in scored]

    def execute_with_backoff(self, provider_name, history, verbose=False):
        max_attempts = 3
        base_backoff = self.circuit_breaker["base_backoff_seconds"]
        for attempt in range(1, max_attempts + 1):
            start_time = time.perf_counter()
            try:
                response = self.available_providers[provider_name](history, verbose)
                latency = time.perf_counter() - start_time
                self.update_metrics(provider_name, success=True, latency=latency)
                self.logger.info(
                    f"Routing success: provider={provider_name}, attempt={attempt}, latency={latency:.3f}s"
                )
                return response
            except Exception as provider_error:
                latency = time.perf_counter() - start_time
                self.update_metrics(provider_name, success=False, latency=latency, error_message=str(provider_error))
                if attempt >= max_attempts:
                    raise
                sleep_seconds = min(base_backoff * (2 ** (attempt - 1)), self.circuit_breaker["max_backoff_seconds"])
                self.logger.warning(
                    f"Routing retry: provider={provider_name}, attempt={attempt}, backoff={sleep_seconds:.1f}s"
                )
                time.sleep(sleep_seconds)

    def route_provider(self, history):
        task_type = self.infer_task_type(history)
        context_tokens = self.estimate_context_tokens(history)
        candidates = [
            provider_name
            for provider_name in self.available_providers
            if provider_name not in {"auto", "test"}
        ]

        if self.is_local:
            local_first = ["ollama", "lm-studio", "server", "colab"]
            candidates = [provider for provider in local_first if provider in candidates] + [
                provider for provider in candidates if provider not in local_first
            ]

        ranked = self.rank_providers(candidates, task_type, context_tokens)
        self.logger.info(
            f"Routing decision: task={task_type}, context_tokens={context_tokens}, ranked={ranked}"
        )
        return ranked

    def respond(self, history, verbose=True):
        """
        Use the choosen provider to generate text.
        """
        self.logger.info(f"Using provider: {self.provider_name} at {self.server_ip}")
        try:
            if self.provider_name == "auto":
                thought = self.auto_fn(history, verbose)
            else:
                thought = self.execute_with_backoff(self.provider_name, history, verbose)
        except KeyboardInterrupt:
            self.logger.warning("User interrupted the operation with Ctrl+C")
            return "Operation interrupted by user. REQUEST_EXIT"
        except ConnectionError as e:
            raise ConnectionError(f"{str(e)}\nConnection to {self.server_ip} failed.")
        except AttributeError as e:
            raise NotImplementedError(f"{str(e)}\nIs {self.provider_name} implemented ?")
        except ModuleNotFoundError as e:
            raise ModuleNotFoundError(
                f"{str(e)}\nA import related to provider {self.provider_name} was not found. Is it installed ?")
        except Exception as e:
            if "try again later" in str(e).lower():
                return f"{self.provider_name} server is overloaded. Please try again later."
            if "refused" in str(e):
                return f"Server {self.server_ip} seem offline. Unable to answer."
            raise Exception(f"Provider {self.provider_name} failed: {str(e)}") from e
        return thought

    def is_ip_online(self, address: str, timeout: int = 10) -> bool:
        """
        Check if an address is online by sending a ping request.
        """
        if not address:
            return False
        parsed = urlparse(address if address.startswith(('http://', 'https://')) else f'http://{address}')

        hostname = parsed.hostname or address
        if "127.0.0.1" in address or "localhost" in address:
            return True
        try:
            ip_address = socket.gethostbyname(hostname)
        except socket.gaierror:
            self.logger.error(f"Cannot resolve: {hostname}")
            return False
        param = '-n' if platform.system().lower() == 'windows' else '-c'
        command = ['ping', param, '1', ip_address]
        try:
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
            return False

    def server_fn(self, history, verbose=False):
        """
        Use a remote server with LLM to generate text.
        """
        thought = ""
        route_setup = f"{self.server_ip}/setup"
        route_gen = f"{self.server_ip}/generate"

        if not self.is_ip_online(self.server_ip):
            pretty_print(f"Server is offline at {self.server_ip}", color="failure")

        try:
            requests.post(route_setup, json={"model": self.model})
            requests.post(route_gen, json={"messages": history})
            is_complete = False
            while not is_complete:
                try:
                    response = requests.get(f"{self.server_ip}/get_updated_sentence")
                    if "error" in response.json():
                        pretty_print(response.json()["error"], color="failure")
                        break
                    thought = response.json()["sentence"]
                    is_complete = bool(response.json()["is_complete"])
                    time.sleep(2)
                except requests.exceptions.RequestException as e:
                    pretty_print(f"HTTP request failed: {str(e)}", color="failure")
                    break
                except ValueError as e:
                    pretty_print(f"Failed to parse JSON response: {str(e)}", color="failure")
                    break
                except Exception as e:
                    pretty_print(f"An error occurred: {str(e)}", color="failure")
                    break
        except KeyError as e:
            raise Exception(
                f"{str(e)}\nError occured with server route. Are you using the correct address for the config.ini provider?") from e
        except Exception as e:
            raise e
        return thought

    def ollama_fn(self, history, verbose=False):
        """
        Use local or remote Ollama server to generate text.
        """
        thought = ""
        host = f"{self.internal_url}:11434" if self.is_local else f"http://{self.server_address}"
        client = OllamaClient(host=host)

        try:
            stream = client.chat(
                model=self.model,
                messages=history,
                stream=True,
            )
            for chunk in stream:
                if verbose:
                    print(chunk["message"]["content"], end="", flush=True)
                thought += chunk["message"]["content"]
        except httpx.ConnectError as e:
            raise Exception(
                f"\nOllama connection failed at {host}. Check if the server is running."
            ) from e
        except Exception as e:
            if hasattr(e, 'status_code') and e.status_code == 404:
                animate_thinking(f"Downloading {self.model}...")
                client.pull(self.model)
                self.ollama_fn(history, verbose)
            if "refused" in str(e).lower():
                raise Exception(
                    f"Ollama connection refused at {host}. Is the server running?"
                ) from e
            raise e

        return thought

    def huggingface_fn(self, history, verbose=False):
        """
        Use huggingface to generate text.
        """
        from huggingface_hub import InferenceClient
        client = InferenceClient(
            api_key=self.get_api_key("huggingface")
        )
        completion = client.chat.completions.create(
            model=self.model,
            messages=history,
            max_tokens=1024,
        )
        thought = completion.choices[0].message
        return thought.content

    def openai_fn(self, history, verbose=False):
        """
        Use openai to generate text.
        """
        base_url = self.server_ip
        if self.is_local and self.in_docker:
            try:
                host, port = base_url.split(':')
            except Exception as e:
                port = "8000"
            client = OpenAI(api_key=self.api_key, base_url=f"{self.internal_url}:{port}")
        elif self.is_local:
            client = OpenAI(api_key=self.api_key, base_url=f"http://{base_url}")
        else:
            client = OpenAI(api_key=self.api_key)

        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=history,
            )
            if response is None:
                raise Exception("OpenAI response is empty.")
            thought = response.choices[0].message.content
            if verbose:
                print(thought)
            return thought
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}") from e

    def anthropic_fn(self, history, verbose=False):
        """
        Use Anthropic to generate text.
        """
        from anthropic import Anthropic

        client = Anthropic(api_key=self.api_key)
        system_message = None
        messages = []
        for message in history:
            clean_message = {'role': message['role'], 'content': message['content']}
            if message['role'] == 'system':
                system_message = message['content']
            else:
                messages.append(clean_message)

        try:
            response = client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=messages,
                system=system_message
            )
            if response is None:
                raise Exception("Anthropic response is empty.")
            thought = response.content[0].text
            if verbose:
                print(thought)
            return thought
        except Exception as e:
            raise Exception(f"Anthropic API error: {str(e)}") from e

    def google_fn(self, history, verbose=False):
        """
        Use google gemini to generate text.
        """
        base_url = self.server_ip
        if self.is_local:
            raise Exception("Google Gemini is not available for local use. Change config.ini")

        client = OpenAI(api_key=self.api_key, base_url="https://generativelanguage.googleapis.com/v1beta/openai/")
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=history,
            )
            if response is None:
                raise Exception("Google response is empty.")
            thought = response.choices[0].message.content
            if verbose:
                print(thought)
            return thought
        except Exception as e:
            raise Exception(f"GOOGLE API error: {str(e)}") from e

    def together_fn(self, history, verbose=False):
        """
        Use together AI for completion
        """
        from together import Together
        client = Together(api_key=self.api_key)
        if self.is_local:
            raise Exception("Together AI is not available for local use. Change config.ini")

        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=history,
            )
            if response is None:
                raise Exception("Together AI response is empty.")
            thought = response.choices[0].message.content
            if verbose:
                print(thought)
            return thought
        except Exception as e:
            raise Exception(f"Together AI API error: {str(e)}") from e

    def deepseek_fn(self, history, verbose=False):
        """
        Use deepseek api to generate text.
        """
        client = OpenAI(api_key=self.api_key, base_url="https://api.deepseek.com")
        if self.is_local:
            raise Exception("Deepseek (API) is not available for local use. Change config.ini")
        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=history,
                stream=False
            )
            thought = response.choices[0].message.content
            if verbose:
                print(thought)
            return thought
        except Exception as e:
            raise Exception(f"Deepseek API error: {str(e)}") from e

    def lm_studio_fn(self, history, verbose=False):
        """
        Use local lm-studio server to generate text.
        """
        if self.in_docker:
            # Extract port from server_address if present
            port = "1234"  # default
            if ":" in self.server_address:
                port = self.server_address.split(":")[1]
            url = f"{self.internal_url}:{port}"
        else:
            url = f"http://{self.server_ip}"
        route_start = f"{url}/v1/chat/completions"
        payload = {
            "messages": history,
            "temperature": 0.7,
            "max_tokens": 4096,
            "model": self.model
        }

        try:
            response = requests.post(route_start, json=payload, timeout=30)
            if response.status_code != 200:
                raise Exception(f"LM Studio returned status {response.status_code}: {response.text}")
            if not response.text.strip():
                raise Exception("LM Studio returned empty response")
            try:
                result = response.json()
            except ValueError as json_err:
                raise Exception(f"Invalid JSON from LM Studio: {response.text[:200]}") from json_err

            if verbose:
                print("Response from LM Studio:", result)
            choices = result.get("choices", [])
            if not choices:
                raise Exception(f"No choices in LM Studio response: {result}")

            message = choices[0].get("message", {})
            content = message.get("content", "")
            if not content:
                raise Exception(f"Empty content in LM Studio response: {result}")
            return content

        except requests.exceptions.Timeout:
            raise Exception("LM Studio request timed out - check if server is responsive")
        except requests.exceptions.ConnectionError:
            raise Exception(f"Cannot connect to LM Studio at {route_start} - check if server is running")
        except requests.exceptions.RequestException as e:
            raise Exception(f"HTTP request failed: {str(e)}") from e
        except Exception as e:
            if "LM Studio" in str(e):
                raise  # Re-raise our custom exceptions
            raise Exception(f"Unexpected error: {str(e)}") from e
        return thought

    def openrouter_fn(self, history, verbose=False):
        """
        Use OpenRouter API to generate text.
        """
        client = OpenAI(api_key=self.api_key, base_url="https://openrouter.ai/api/v1")
        if self.is_local:
            # This case should ideally not be reached if unsafe_providers is set correctly
            # and is_local is False in config for openrouter
            raise Exception("OpenRouter is not available for local use. Change config.ini")
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=history,
            )
            if response is None:
                raise Exception("OpenRouter response is empty.")
            thought = response.choices[0].message.content
            if verbose:
                print(thought)
            return thought
        except Exception as e:
            raise Exception(f"OpenRouter API error: {str(e)}") from e

    def dsk_deepseek(self, history, verbose=False):
        """
        Use: xtekky/deepseek4free
        For free api. Api key should be set to DSK_DEEPSEEK_API_KEY
        This is an unofficial provider, you'll have to find how to set it up yourself.
        """
        from dsk.api import (
            DeepSeekAPI,
            AuthenticationError,
            RateLimitError,
            NetworkError,
            CloudflareError,
            APIError
        )
        thought = ""
        message = '\n---\n'.join([f"{msg['role']}: {msg['content']}" for msg in history])

        try:
            api = DeepSeekAPI(self.api_key)
            chat_id = api.create_chat_session()
            for chunk in api.chat_completion(chat_id, message):
                if chunk['type'] == 'text':
                    thought += chunk['content']
            return thought
        except AuthenticationError:
            raise AuthenticationError("Authentication failed. Please check your token.") from e
        except RateLimitError:
            raise RateLimitError("Rate limit exceeded. Please wait before making more requests.") from e
        except CloudflareError as e:
            raise CloudflareError(f"Cloudflare protection encountered: {str(e)}") from e
        except NetworkError:
            raise NetworkError("Network error occurred. Check your internet connection.") from e
        except APIError as e:
            raise APIError(f"API error occurred: {str(e)}") from e
        return None

    def sapient_hrm_fn(self, history, verbose=False):
        """
        Use Sapient HRM AI.
        Since there is no public API documentation yet, this serves as a integration point.
        It assumes an OpenAI-compatible interface or requires a specific base URL.
        """
        pretty_print("Using Sapient HRM AI Integration (Experimental)", color="status")

        # If the user has provided a custom server address for HRM, we use it.
        # Otherwise, we might default to a placeholder or a known endpoint if one existed.
        base_url = self.server_ip if self.server_ip and "127.0.0.1" not in self.server_ip else "https://api.sapient.inc/v1"

        client = OpenAI(api_key=self.api_key, base_url=base_url)
        try:
            response = client.chat.completions.create(
                model=self.model, # e.g., "hrm-1"
                messages=history,
            )
            thought = response.choices[0].message.content
            if verbose:
                print(thought)
            return thought
        except Exception as e:
             raise Exception(f"Sapient HRM AI Error: {str(e)}\nEnsure you have the correct API Key and Endpoint if available.") from e

    def colab_fn(self, history, verbose=False):
        """
        Use a Google Colab instance as backend (usually via ngrok).
        Expects server_address to be the ngrok URL.
        """
        pretty_print(f"Connecting to Colab/Cloud instance at {self.server_ip}", color="status")

        # Colab backends (like text-generation-webui or ollama-colab) usually provide an OpenAI compatible API
        client = OpenAI(api_key="dummy", base_url=f"{self.server_ip}/v1")

        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=history,
            )
            thought = response.choices[0].message.content
            if verbose:
                print(thought)
            return thought
        except Exception as e:
            raise Exception(f"Colab Connection Error: {str(e)}\nCheck if your Colab instance is running and the URL is correct.") from e

    def auto_fn(self, history, verbose=False):
        """
        Autonomous Mode: Tries to find the best available free resource.
        It iterates through a list of likely free or local providers.
        """
        ranked_providers = self.route_provider(history)
        pretty_print("AUTO MODE: Attempting ranked provider routing...", color="status")

        for p_name in ranked_providers:
            if p_name == "huggingface" and not os.getenv("HUGGINGFACE_API_KEY"):
                self.logger.info("Routing skip: provider=huggingface, reason=missing_api_key")
                continue

            if p_name in ["lm-studio", "server", "colab"] and not self.is_ip_online(self.server_ip, timeout=2):
                self.logger.info(f"Routing skip: provider={p_name}, reason=endpoint_offline")
                continue

            if p_name == "colab" and ("127.0.0.1" in self.server_ip or "localhost" in self.server_ip):
                self.logger.info("Routing skip: provider=colab, reason=local_address")
                continue

            try:
                response = self.execute_with_backoff(p_name, history, verbose)
                pretty_print(f"Successfully used {p_name}", color="success")
                return response
            except Exception as e:
                self.logger.warning(f"Auto provider {p_name} failed after retries: {e}")
                continue

        raise Exception("Auto Mode: All providers failed. Please check your configuration and available resources.")

    def test_fn(self, history, verbose=True):
        """
        This function is used to conduct tests.
        """
        thought = """
\n\n```json\n{\n  \"plan\": [\n    {\n      \"agent\": \"Web\",\n      \"id\": \"1\",\n      \"need\": null,\n      \"task\": \"Conduct a comprehensive web search to identify at least five AI startups located in Osaka. Use reliable sources and websites such as Crunchbase, TechCrunch, or local Japanese business directories. Capture the company names, their websites, areas of expertise, and any other relevant details.\"\n    },\n    {\n      \"agent\": \"Web\",\n      \"id\": \"2\",\n      \"need\": null,\n      \"task\": \"Perform a similar search to find at least five AI startups in Tokyo. Again, use trusted sources like Crunchbase, TechCrunch, or Japanese business news websites. Gather the same details as for Osaka: company names, websites, areas of focus, and additional information.\"\n    },\n    {\n      \"agent\": \"File\",\n      \"id\": \"3\",\n      \"need\": [\"1\", \"2\"],\n      \"task\": \"Create a new text file named research_japan.txt in the user's home directory. Organize the data collected from both searches into this file, ensuring it is well-structured and formatted for readability. Include headers for Osaka and Tokyo sections, followed by the details of each startup found.\"\n    }\n  ]\n}\n```
        """
        return thought


if __name__ == "__main__":
    provider = Provider("server", "deepseek-r1:32b", " x.x.x.x:8080")
    res = provider.respond(["user", "Hello, how are you?"])
    print("Response:", res)
