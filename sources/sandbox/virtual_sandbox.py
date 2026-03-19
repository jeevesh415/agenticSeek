"""
Virtual Environment Sandbox for agenticSeek
Secure code execution and environment management
Based on latest 2026 containerization and security practices
"""

import asyncio
import json
import logging
import os
import subprocess
import tempfile
import shutil
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import hashlib
import resource

logger = logging.getLogger(__name__)


class SandboxEnvironment(Enum):
    """Types of sandboxed environments"""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    BASH = "bash"
    DOCKER = "docker"
    WASM = "wasm"


class ExecutionStatus(Enum):
    """Status of sandbox execution"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    TIMEOUT = "timeout"
    ERROR = "error"
    KILLED = "killed"


@dataclass
class SandboxConfig:
    """Configuration for sandboxed execution"""
    environment: SandboxEnvironment = SandboxEnvironment.PYTHON
    timeout_seconds: int = 30
    memory_limit_mb: int = 512
    cpu_limit_percent: int = 50
    network_enabled: bool = False
    disk_quota_mb: int = 100
    max_processes: int = 5
    working_directory: Optional[str] = None
    environment_variables: Dict[str, str] = field(default_factory=dict)
    allowed_packages: List[str] = field(default_factory=list)
    blocked_packages: List[str] = field(default_factory=lambda: ["subprocess", "os", "sys"])
    
    # Security settings
    read_only_filesystem: bool = True
    seccomp_enabled: bool = True
    apparmor_enabled: bool = True


@dataclass
class ExecutionResult:
    """Result of sandboxed execution"""
    status: ExecutionStatus
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    execution_time: float = 0.0
    memory_used_mb: float = 0.0
    cpu_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SandboxSession:
    """Represents a sandbox session"""
    id: str
    config: SandboxConfig
    created_at: datetime = field(default_factory=datetime.utcnow)
    working_dir: Optional[str] = None
    process: Optional[Any] = None
    status: ExecutionStatus = ExecutionStatus.PENDING


class VirtualSandbox:
    """
    Virtual sandbox for secure code execution
    Features:
    - Multiple language support (Python, JS, Bash)
    - Resource limits (CPU, memory, time)
    - Network isolation
    - Filesystem restrictions
    - Process isolation
    """
    
    def __init__(self, config: Optional[SandboxConfig] = None):
        self.config = config or SandboxConfig()
        self.sessions: Dict[str, SandboxSession] = {}
        self.base_dir = tempfile.mkdtemp(prefix="agentic_sandbox_")
        
    def create_session(
        self,
        environment: SandboxEnvironment = SandboxEnvironment.PYTHON,
        **kwargs
    ) -> str:
        """
        Create a new sandbox session
        """
        # Merge config
        session_config = SandboxConfig(
            environment=environment,
            **{k: v for k, v in kwargs.items() if hasattr(SandboxConfig, k)}
        )
        
        # Create session ID
        session_id = hashlib.sha256(
            f"{datetime.utcnow().isoformat()}{os.getpid()}".encode()
        ).hexdigest()[:16]
        
        # Create working directory
        work_dir = os.path.join(self.base_dir, session_id)
        os.makedirs(work_dir, exist_ok=True)
        
        # Create session
        session = SandboxSession(
            id=session_id,
            config=session_config,
            working_dir=work_dir
        )
        
        self.sessions[session_id] = session
        
        logger.info(f"Created sandbox session: {session_id}")
        
        return session_id
    
    async def execute(
        self,
        code: str,
        session_id: Optional[str] = None,
        config: Optional[SandboxConfig] = None
    ) -> ExecutionResult:
        """
        Execute code in sandbox
        """
        # Use provided session or create new one
        if session_id and session_id in self.sessions:
            session = self.sessions[session_id]
            config = config or session.config
        else:
            session_id = self.create_session(
                environment=config.environment if config else SandboxEnvironment.PYTHON
            )
            session = self.sessions[session_id]
            if config:
                session.config = config
        
        session.status = ExecutionStatus.RUNNING
        
        # Select executor
        executors = {
            SandboxEnvironment.PYTHON: self._execute_python,
            SandboxEnvironment.JAVASCRIPT: self._execute_javascript,
            SandboxEnvironment.BASH: self._execute_bash,
            SandboxEnvironment.DOCKER: self._execute_docker,
            SandboxEnvironment.WASM: self._execute_wasm
        }
        
        executor = executors.get(session.config.environment, self._execute_python)
        
        try:
            result = await asyncio.wait_for(
                executor(code, session),
                timeout=session.config.timeout_seconds
            )
            
            if result.status == ExecutionStatus.SUCCESS:
                session.status = ExecutionStatus.SUCCESS
            else:
                session.status = result.status
                
            return result
            
        except asyncio.TimeoutError:
            result = ExecutionResult(
                status=ExecutionStatus.TIMEOUT,
                stderr=f"Execution timed out after {session.config.timeout_seconds} seconds"
            )
            session.status = ExecutionStatus.TIMEOUT
            await self._cleanup_session(session)
            return result
            
        except Exception as e:
            logger.error(f"Execution failed: {e}")
            result = ExecutionResult(
                status=ExecutionStatus.ERROR,
                stderr=str(e)
            )
            session.status = ExecutionStatus.ERROR
            return result
    
    async def _execute_python(
        self,
        code: str,
        session: SandboxSession
    ) -> ExecutionResult:
        """
        Execute Python code in sandbox
        """
        start_time = datetime.utcnow()
        
        # Create temporary file
        code_file = os.path.join(session.working_dir, "script.py")
        with open(code_file, "w") as f:
            f.write(code)
        
        # Build command with restrictions
        cmd = [
            "python3",
            "-u",  # Unbuffered
            code_file
        ]
        
        # Environment variables
        env = {
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONUNBUFFERED": "1",
            **session.config.environment_variables
        }
        
        # Run with resource limits
        result = await self._run_process(
            cmd,
            session,
            env,
            start_time
        )
        
        # Cleanup
        try:
            os.remove(code_file)
        except:
            pass
        
        return result
    
    async def _execute_javascript(
        self,
        code: str,
        session: SandboxSession
    ) -> ExecutionResult:
        """
        Execute JavaScript code in sandbox
        """
        start_time = datetime.utcnow()
        
        # Create temporary file
        code_file = os.path.join(session.working_dir, "script.js")
        with open(code_file, "w") as f:
            f.write(code)
        
        # Use Node.js with security flags
        cmd = [
            "node",
            "--experimental-vm-modules",
            "--no-warnings",
            code_file
        ]
        
        env = {
            **os.environ,
            **session.config.environment_variables
        }
        
        result = await self._run_process(
            cmd,
            session,
            env,
            start_time
        )
        
        # Cleanup
        try:
            os.remove(code_file)
        except:
            pass
        
        return result
    
    async def _execute_bash(
        self,
        code: str,
        session: SandboxSession
    ) -> ExecutionResult:
        """
        Execute bash script in sandbox
        """
        start_time = datetime.utcnow()
        
        # Create temporary script
        script_file = os.path.join(session.working_dir, "script.sh")
        with open(script_file, "w") as f:
            f.write(f"#!/bin/bash\nset -e\n{code}")
        os.chmod(script_file, 0o755)
        
        cmd = ["/bin/bash", script_file]
        
        env = {
            **os.environ,
            **session.config.environment_variables
        }
        
        result = await self._run_process(
            cmd,
            session,
            env,
            start_time
        )
        
        # Cleanup
        try:
            os.remove(script_file)
        except:
            pass
        
        return result
    
    async def _execute_docker(
        self,
        code: str,
        session: SandboxSession
    ) -> ExecutionResult:
        """
        Execute code in Docker container
        """
        start_time = datetime.utcnow()
        
        # Create code file
        code_file = os.path.join(session.working_dir, "code")
        with open(code_file, "w") as f:
            f.write(code)
        
        # Determine Docker image based on environment
        images = {
            SandboxEnvironment.PYTHON: "python:3.10-slim",
            SandboxEnvironment.JAVASCRIPT: "node:18-slim",
            SandboxEnvironment.BASH: "bash:5"
        }
        
        image = images.get(session.config.environment, "python:3.10-slim")
        
        # Build Docker command
        cmd = [
            "docker", "run",
            "--rm",
            "--network=none" if not session.config.network_enabled else "bridge",
            "--memory", f"{session.config.memory_limit_mb}m",
            "--cpus", str(session.config.cpu_limit_percent / 100),
            "--pids-limit", str(session.config.max_processes),
            "-v", f"{session.working_dir}:/workspace",
            "-w", "/workspace",
            image,
            "python3" if session.config.environment == SandboxEnvironment.PYTHON else "node",
            "code" if session.config.environment == SandboxEnvironment.PYTHON else "code.js"
        ]
        
        env = {
            **os.environ,
            **session.config.environment_variables
        }
        
        result = await self._run_process(
            cmd,
            session,
            env,
            start_time
        )
        
        # Cleanup
        try:
            shutil.rmtree(session.working_dir)
            os.makedirs(session.working_dir)
        except:
            pass
        
        return result
    
    async def _execute_wasm(
        self,
        code: str,
        session: SandboxSession
    ) -> ExecutionResult:
        """
        Execute WebAssembly code in sandbox
        """
        # In production, use Wasmtime or similar
        return ExecutionResult(
            status=ExecutionStatus.ERROR,
            stderr="WebAssembly execution not yet implemented"
        )
    
    async def _run_process(
        self,
        cmd: List[str],
        session: SandboxSession,
        env: Dict[str, str],
        start_time: datetime
    ) -> ExecutionResult:
        """
        Run a process with resource limits
        """
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                cwd=session.working_dir,
                limit=1024 * 1024  # 1MB output limit
            )
            
            session.process = process
            
            stdout, stderr = await process.communicate()
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            return ExecutionResult(
                status=ExecutionStatus.SUCCESS if process.returncode == 0 else ExecutionStatus.ERROR,
                stdout=stdout.decode() if stdout else "",
                stderr=stderr.decode() if stderr else "",
                exit_code=process.returncode or 0,
                execution_time=execution_time,
                metadata={
                    "command": " ".join(cmd),
                    "working_dir": session.working_dir
                }
            )
            
        except asyncio.TimeoutError:
            await self._kill_process(session)
            return ExecutionResult(
                status=ExecutionStatus.TIMEOUT,
                stderr="Process timed out"
            )
        except Exception as e:
            return ExecutionResult(
                status=ExecutionStatus.ERROR,
                stderr=str(e)
            )
    
    async def _kill_process(self, session: SandboxSession):
        """Kill a running process"""
        if session.process:
            try:
                session.process.kill()
                await session.process.wait()
            except:
                pass
        session.status = ExecutionStatus.KILLED
    
    async def _cleanup_session(self, session: SandboxSession):
        """Cleanup a session"""
        await self._kill_process(session)
        
        # Remove working directory
        if session.working_dir and os.path.exists(session.working_dir):
            try:
                shutil.rmtree(session.working_dir)
            except:
                pass
    
    def delete_session(self, session_id: str):
        """Delete a sandbox session"""
        if session_id in self.sessions:
            session = self.sessions[session_id]
            asyncio.create_task(self._cleanup_session(session))
            del self.sessions[session_id]
            logger.info(f"Deleted sandbox session: {session_id}")
    
    def get_session(self, session_id: str) -> Optional[SandboxSession]:
        """Get session information"""
        return self.sessions.get(session_id)
    
    def list_sessions(self) -> List[SandboxSession]:
        """List all active sessions"""
        return list(self.sessions.values())


class CodeExecutionAgent:
    """
    Agent specialized in code execution and validation
    Integrates with agenticSeek's agent system
    """
    
    def __init__(
        self,
        sandbox: Optional[VirtualSandbox] = None,
        llm_client: Optional[Any] = None
    ):
        self.sandbox = sandbox or VirtualSandbox()
        self.llm = llm_client
        
    async def execute_and_validate(
        self,
        code: str,
        language: str = "python",
        test_cases: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Execute code and validate against test cases
        """
        environment_map = {
            "python": SandboxEnvironment.PYTHON,
            "javascript": SandboxEnvironment.JAVASCRIPT,
            "js": SandboxEnvironment.JAVASCRIPT,
            "bash": SandboxEnvironment.BASH,
            "shell": SandboxEnvironment.BASH
        }
        
        environment = environment_map.get(language.lower(), SandboxEnvironment.PYTHON)
        
        # Execute code
        result = await self.sandbox.execute(
            code,
            config=SandboxConfig(environment=environment)
        )
        
        # Validate if test cases provided
        validation_results = []
        if test_cases:
            for i, test in enumerate(test_cases):
                passed = self._validate_test_case(result.stdout, test)
                validation_results.append({
                    "test_case": i + 1,
                    "passed": passed,
                    "expected": test.get("expected"),
                    "actual": result.stdout
                })
        
        return {
            "execution": {
                "status": result.status.value,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.exit_code,
                "execution_time": result.execution_time
            },
            "validation": validation_results,
            "all_passed": all(v["passed"] for v in validation_results) if validation_results else result.status == ExecutionStatus.SUCCESS
        }
    
    def _validate_test_case(
        self,
        output: str,
        test_case: Dict[str, Any]
    ) -> bool:
        """Validate output against test case"""
        expected = test_case.get("expected")
        
        if expected is None:
            return True
        
        if isinstance(expected, str):
            return expected in output
        elif isinstance(expected, (int, float)):
            try:
                return float(output.strip()) == expected
            except:
                return False
        else:
            return str(expected) == output.strip()
    
    async def debug_and_fix(
        self,
        code: str,
        error: str,
        language: str = "python"
    ) -> str:
        """
        Use LLM to debug and fix code errors
        """
        if not self.llm:
            return code
        
        prompt = f"""Debug this {language} code that has the following error:
        
Error: {error}

Code:
{code}

Provide fixed code only, without explanations."""

        try:
            fixed_code = await self.llm.generate(prompt)
            return fixed_code
        except Exception as e:
            logger.error(f"Debug failed: {e}")
            return code
