import os
import sys
import subprocess
import logging
import platform
import json
from typing import List, Tuple, Dict, Any

from sources.tools.tools import Tools

logger = logging.getLogger(__name__)

class KernelDominanceTool(Tools):
    """
    Absolute OS Dominance: eBPF Kernel Tracing, Process Control, CPU/GPU Management.
    Provides the AGI with direct observation and tuning of the underlying hardware
    and operating system kernel via system calls, pynvml, and eBPF.
    """
    def __init__(self, dry_run: bool = True):
        super().__init__()
        self.name = "kernel_dominance"
        self.description = "Deep OS kernel control, eBPF tracing, CPU frequency scaling, and GPU power tuning."
        self.dry_run = dry_run

        # Check root privileges required for eBPF and hardware tuning
        self.is_root = os.geteuid() == 0 if platform.system() == "Linux" else False

        if not self.is_root:
            logger.warning("[Kernel Dominance] Warning: Not running as root. Hardware tuning and eBPF tracing will operate in SIMULATION mode.")

    def execute(self, blocks: List[str]) -> str:
        """Executes a parsed kernel or hardware command block."""
        if not blocks:
            return "No command provided."

        command = blocks[0].strip().lower()

        if command.startswith("trace"):
            return self._ebpf_trace_syscalls(command)
        elif command == "thermal":
            return self._get_thermal_zones()
        elif command == "pcie":
            return self._enumerate_pcie()
        elif command.startswith("cpu_tune"):
            return self._tune_cpu(command)
        elif command.startswith("gpu_tune"):
            return self._tune_gpu(command)
        elif command == "status":
            return json.dumps({
                "is_root": self.is_root,
                "dry_run": self.dry_run,
                "os": platform.system()
            }, indent=2)
        else:
            return f"Error: Unknown kernel command '{command}'. Available: trace [pid], thermal, pcie, cpu_tune [freq], gpu_tune [power_limit], status."

    def _ebpf_trace_syscalls(self, command: str) -> str:
        """
        eBPF - Kernel-level hooks for system call monitoring.
        Uses BCC (BPF Compiler Collection) under the hood if available, or simulates it.
        """
        parts = command.split()
        target_pid = parts[1] if len(parts) > 1 else "all"

        if not self.is_root or self.dry_run:
            return f"[SIMULATION: DRY-RUN] eBPF Tracing attached to PID: {target_pid}. Intercepting sys_clone, sys_execve, sys_open. 0 anomalies detected."

        try:
            # In a true deployment, this would import bcc and compile a C program injecting into the kernel.
            # Example: bcc.BPF(text=""" int kprobe__sys_execve(struct pt_regs *ctx) { bpf_trace_printk("Executed\\n"); return 0; } """)
            # Since BCC requires kernel headers and compilation, we simulate the output or use a safe wrapper like strace as a fallback
            res = subprocess.run(["strace", "-c", "-p", target_pid], capture_output=True, text=True, timeout=3)
            return res.stderr if res.stderr else res.stdout
        except Exception as e:
            return f"eBPF Tracing Failed (Is bcc/strace installed?): {e}"

    def _get_thermal_zones(self) -> str:
        """ACPI - Reads thermal zones directly from the sysfs tree (Linux)."""
        if platform.system() != "Linux":
            return "Thermal zone reading is only natively supported on Linux sysfs."

        zones = {}
        base_dir = "/sys/class/thermal/"
        if not os.path.exists(base_dir):
            return "ACPI Thermal zones not found on this system."

        for d in os.listdir(base_dir):
            if d.startswith("thermal_zone"):
                try:
                    with open(os.path.join(base_dir, d, "type"), "r") as f:
                        z_type = f.read().strip()
                    with open(os.path.join(base_dir, d, "temp"), "r") as f:
                        # Millidegrees Celsius to Celsius
                        z_temp = float(f.read().strip()) / 1000.0
                    zones[z_type] = f"{z_temp:.1f}°C"
                except Exception:
                    continue

        return json.dumps(zones, indent=2) if zones else "No readable thermal zones found."

    def _enumerate_pcie(self) -> str:
        """PCIe/ACPI - Device enumeration via lspci."""
        if platform.system() != "Linux":
            return "PCIe enumeration is currently implemented for Linux (lspci)."

        try:
            res = subprocess.run(["lspci", "-nn"], capture_output=True, text=True, check=True)
            # Just return the first 10 devices to avoid flooding the context window
            lines = res.stdout.split('\n')[:10]
            return "PCIe Devices (Top 10):\n" + "\n".join(lines)
        except Exception as e:
            return f"Failed to enumerate PCIe devices: {e}"

    def _tune_cpu(self, command: str) -> str:
        """CPU Control - Frequency scaling, core pinning, real-time scheduling."""
        parts = command.split()
        if len(parts) < 2:
            return "Usage: cpu_tune [performance|powersave|frequency_in_mhz]"

        target = parts[1]

        if not self.is_root or self.dry_run:
            return f"[SIMULATION: DRY-RUN] CPU Governor/Frequency set to: {target}. Real-time scheduling limits updated."

        if platform.system() != "Linux":
            return "CPU tuning is currently implemented for Linux cpufreq."

        try:
            if target in ["performance", "powersave"]:
                subprocess.run(f"cpupower frequency-set -g {target}", shell=True, check=True, capture_output=True)
                return f"Successfully set CPU governor to {target}."
            else:
                freq = int(target)
                subprocess.run(f"cpupower frequency-set -u {freq}MHz", shell=True, check=True, capture_output=True)
                return f"Successfully set CPU max frequency to {freq}MHz."
        except Exception as e:
            return f"CPU Tuning failed (cpupower installed?): {e}"

    def _tune_gpu(self, command: str) -> str:
        """GPU Management - Power limits, clock speeds, memory, via NVIDIA/SMI or AMD/ROCm."""
        parts = command.split()
        if len(parts) < 2:
            return "Usage: gpu_tune [power_limit_watts|reset]"

        target = parts[1]

        if not self.is_root or self.dry_run:
            return f"[SIMULATION: DRY-RUN] NVIDIA NVML: GPU Power Limit adjusted to {target}W. Memory clocks optimized."

        try:
            # Interface via nvidia-smi for NVIDIA GPUs (AMD would use rocm-smi)
            if target == "reset":
                subprocess.run(["nvidia-smi", "-pl", "DEFAULT"], check=True, capture_output=True)
                return "GPU power limit reset to default."
            else:
                limit = int(target)
                subprocess.run(["nvidia-smi", "-pl", str(limit)], check=True, capture_output=True)
                return f"GPU power limit successfully set to {limit} Watts."
        except Exception as e:
            return f"GPU Tuning failed (nvidia-smi installed?): {e}"

    def load_exec_block(self, text: str) -> Tuple[List[str], str]:
        """Parses a kernel block from the agent's text response."""
        blocks = []
        in_block = False
        current_block = []

        for line in text.split('\n'):
            if line.strip().startswith('```kernel'):
                in_block = True
                current_block = []
            elif line.strip() == '```' and in_block:
                in_block = False
                blocks.append('\n'.join(current_block))
            elif in_block:
                current_block.append(line)

        return blocks if blocks else None, None
