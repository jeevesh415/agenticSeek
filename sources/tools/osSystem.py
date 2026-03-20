import os
import platform
import psutil
import subprocess
from typing import List, Tuple
from sources.tools.tools import Tools

class OSSystemControl(Tools):
    """
    A futuristic AGI tool allowing direct observation and basic control
    of the underlying Operating System kernel, hardware statistics, and processes.
    """
    def __init__(self):
        super().__init__()
        self.name = "os_kernel_control"
        self.description = "Observe system hardware (CPU/RAM/Disk), list running processes, and execute basic OS commands safely."

    def execute(self, blocks: List[str]) -> str:
        """
        Executes a sequence of OS commands passed in the code blocks.
        The agent can request stats like 'cpu', 'memory', 'disk', 'os_info', or 'processes'.
        """
        if not blocks:
            return "No command provided."

        command = blocks[0].strip().lower()

        if command == "cpu":
            return self._get_cpu_stats()
        elif command == "memory":
            return self._get_memory_stats()
        elif command == "disk":
            return self._get_disk_stats()
        elif command == "os_info":
            return self._get_os_info()
        elif command == "processes":
            return self._get_top_processes()
        else:
            return "Error: Unrecognized command. Available commands: cpu, memory, disk, os_info, processes."

    def _get_cpu_stats(self) -> str:
        cpu_percent = psutil.cpu_percent(interval=1)
        cores = psutil.cpu_count(logical=False)
        threads = psutil.cpu_count(logical=True)
        freq = psutil.cpu_freq()
        freq_str = f"{freq.current:.2f}Mhz" if freq else "Unknown"
        return f"CPU Usage: {cpu_percent}%\nCores: {cores} (Threads: {threads})\nFrequency: {freq_str}"

    def _get_memory_stats(self) -> str:
        mem = psutil.virtual_memory()
        total_gb = mem.total / (1024 ** 3)
        used_gb = mem.used / (1024 ** 3)
        return f"Memory: {used_gb:.2f}GB / {total_gb:.2f}GB ({mem.percent}% used)"

    def _get_disk_stats(self) -> str:
        disk = psutil.disk_usage('/')
        total_gb = disk.total / (1024 ** 3)
        used_gb = disk.used / (1024 ** 3)
        return f"Disk '/': {used_gb:.2f}GB / {total_gb:.2f}GB ({disk.percent}% used)"

    def _get_os_info(self) -> str:
        sys_info = f"System: {platform.system()} {platform.release()}\n"
        sys_info += f"Machine: {platform.machine()}\n"
        sys_info += f"Processor: {platform.processor()}"
        return sys_info

    def _get_top_processes(self, limit: int = 5) -> str:
        processes = []
        for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                processes.append(p.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

        # Sort by CPU usage
        processes = sorted(processes, key=lambda p: p['cpu_percent'] or 0.0, reverse=True)

        output = f"Top {limit} Processes by CPU:\n"
        for i, p in enumerate(processes[:limit]):
            output += f"PID: {p['pid']} | Name: {p['name']} | CPU: {p['cpu_percent']}% | RAM: {p['memory_percent']:.1f}%\n"
        return output

    def load_exec_block(self, text: str) -> Tuple[List[str], str]:
        """
        Parses an OS block from the agent's text response.
        OS blocks should be wrapped in ```os ... ```
        """
        blocks = []
        in_block = False
        current_block = []

        for line in text.split('\n'):
            if line.strip().startswith('```os'):
                in_block = True
                current_block = []
            elif line.strip() == '```' and in_block:
                in_block = False
                blocks.append('\n'.join(current_block))
            elif in_block:
                current_block.append(line)

        return blocks if blocks else None, None
