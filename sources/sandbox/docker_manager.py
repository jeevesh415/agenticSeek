import logging
import time
import subprocess
import json
from typing import Dict, Any, Optional

try:
    import docker
except ImportError:
    docker = None

logger = logging.getLogger(__name__)

class DockerEnvironmentManager:
    """
    Layer 1: Containerization (Docker) MVP.
    Allows the AGI Swarm to dynamically spin up isolated, resource-constrained
    virtual environments for executing untrusted code, parallel scraping, or hosting micro-services.
    """
    def __init__(self):
        self.client = None
        self.use_cli_fallback = False

        try:
            if docker:
                self.client = docker.from_env()
                self.client.ping()
                logger.info("[VirtualEnvironment] Docker Daemon connected via API.")
            else:
                raise ImportError("docker-py not installed.")
        except Exception as e:
            logger.warning(f"[VirtualEnvironment] Docker API failed ({e}). Falling back to CLI or Simulation mode.")
            self.use_cli_fallback = True

    def spawn_environment(self, env_id: str, image: str = "python:3.10-slim",
                          cpu_limit: float = 0.5, mem_limit: str = "512m",
                          network_disabled: bool = False) -> Dict[str, Any]:
        """
        Spawns a new isolated Docker container.
        cpu_limit: Number of CPUs (e.g., 0.5 is half a core)
        mem_limit: Memory limit (e.g., '512m', '1g')
        """
        logger.info(f"[VirtualEnvironment] Spawning env '{env_id}' using image '{image}'...")

        if not self.use_cli_fallback and self.client:
            try:
                # Ensure image exists
                try:
                    self.client.images.get(image)
                except docker.errors.ImageNotFound:
                    logger.info(f"Pulling image {image}...")
                    self.client.images.pull(image)

                container = self.client.containers.run(
                    image,
                    command="tail -f /dev/null", # Keep alive
                    name=f"agi_sandbox_{env_id}",
                    detach=True,
                    nano_cpus=int(cpu_limit * 1e9),
                    mem_limit=mem_limit,
                    network_disabled=network_disabled,
                    remove=True # Auto-remove when stopped
                )
                return {"status": "running", "id": container.id, "name": container.name}
            except Exception as e:
                logger.error(f"Failed to spawn Docker container via API: {e}")
                return {"status": "error", "message": str(e)}
        else:
            # Fallback to CLI or Simulation
            return self._spawn_cli_fallback(env_id, image, mem_limit, network_disabled)

    def execute_code(self, env_id: str, code: str, timeout: int = 30) -> str:
        """
        Executes arbitrary code inside the specific container.
        """
        container_name = f"agi_sandbox_{env_id}"

        if not self.use_cli_fallback and self.client:
            try:
                container = self.client.containers.get(container_name)
                # We pipe the code into python -c
                exec_cmd = ["python", "-c", code]
                exit_code, output = container.exec_run(exec_cmd, workdir="/tmp")
                return output.decode('utf-8')
            except docker.errors.NotFound:
                return f"Error: Environment {env_id} not found."
            except Exception as e:
                return f"Error executing code: {e}"
        else:
            return self._execute_cli_fallback(container_name, code, timeout)

    def destroy_environment(self, env_id: str) -> bool:
        """Kills and removes the container."""
        container_name = f"agi_sandbox_{env_id}"
        logger.info(f"[VirtualEnvironment] Destroying env '{env_id}'...")

        if not self.use_cli_fallback and self.client:
            try:
                container = self.client.containers.get(container_name)
                container.stop(timeout=2)
                return True
            except Exception as e:
                logger.error(f"Failed to destroy {env_id}: {e}")
                return False
        else:
            try:
                subprocess.run(["docker", "rm", "-f", container_name], capture_output=True, check=True)
                return True
            except Exception:
                return False

    def _spawn_cli_fallback(self, env_id: str, image: str, mem_limit: str, network_disabled: bool) -> Dict[str, Any]:
        """Uses the `docker` CLI directly if the python SDK fails, or simulates if no docker."""
        container_name = f"agi_sandbox_{env_id}"
        try:
            cmd = ["docker", "run", "-d", "--name", container_name, "--memory", mem_limit]
            if network_disabled:
                cmd.extend(["--network", "none"])
            cmd.extend([image, "tail", "-f", "/dev/null"])

            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return {"status": "running", "id": res.stdout.strip(), "name": container_name}
        except FileNotFoundError:
            logger.warning("Docker CLI not found. Simulating Virtual Environment spawn.")
            return {"status": "simulated", "id": f"sim_{env_id}", "name": container_name}
        except subprocess.CalledProcessError as e:
            return {"status": "error", "message": e.stderr}

    def _execute_cli_fallback(self, container_name: str, code: str, timeout: int) -> str:
        """Executes code via docker exec CLI, or simulates if docker is missing."""
        try:
            # Check if Docker is installed at all
            subprocess.run(["docker", "--version"], capture_output=True, check=True)

            # Write code to a temporary file, docker cp it, then run it.
            # For simplicity in fallback, we use bash -c
            # (Note: proper escaping of `code` is required for production shell use)
            escaped_code = code.replace("'", "'\\''")
            cmd = ["docker", "exec", container_name, "sh", "-c", f"python -c '{escaped_code}'"]

            res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            return res.stdout if res.returncode == 0 else res.stderr
        except FileNotFoundError:
            return f"[SIMULATED ENV {container_name}] Executed code:\n{code}\n(Docker is not installed on this host)"
        except subprocess.TimeoutExpired:
            return "Error: Execution timed out."
        except Exception as e:
            return f"Error: {str(e)}"
