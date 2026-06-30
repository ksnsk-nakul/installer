from __future__ import annotations

import re
from enum import Enum
from typing import Protocol, runtime_checkable


class Environment(str, Enum):
    UBUNTU = "ubuntu"
    DEBIAN = "debian"
    DOCKER = "docker"
    WINDOWS = "windows"
    UNKNOWN = "unknown"


class DetectionError(RuntimeError):
    """Raised when OS/environment detection fails unrecoverably."""


@runtime_checkable
class CommandRunner(Protocol):
    """Minimal interface used by detect_environment — satisfied by SSH/local runners."""

    def run(self, command: str) -> str:
        """Execute command and return stdout. Raise on non-zero exit."""
        ...


def _run_safe(runner: CommandRunner, cmd: str) -> str:
    """Run cmd, return stdout stripped; return '' on any error."""
    try:
        return (runner.run(cmd) or "").strip()
    except Exception:
        return ""


def detect_environment(runner: CommandRunner) -> tuple[Environment, dict]:
    """
    Probe the target via runner and return (Environment, info_dict).

    Detection order:
      1. WinRM / Windows — check for cmd.exe / PowerShell artefacts
      2. Docker — check /.dockerenv or cgroup marker
      3. Linux distro — parse /etc/os-release
      4. Fallback → UNKNOWN
    """
    info: dict = {}

    # --- Windows ---
    win_out = _run_safe(runner, "ver")
    if "windows" in win_out.lower() or "microsoft" in win_out.lower():
        info["os"] = "Windows"
        info["raw"] = win_out
        return Environment.WINDOWS, info

    # --- Docker ---
    docker_env = _run_safe(runner, "test -f /.dockerenv && echo yes || echo no")
    if docker_env == "yes":
        info["os"] = "Docker"
        return Environment.DOCKER, info
    cgroup = _run_safe(runner, "cat /proc/1/cgroup 2>/dev/null | head -1")
    if "docker" in cgroup or "containerd" in cgroup or "lxc" in cgroup:
        info["os"] = "Docker"
        return Environment.DOCKER, info

    # --- Linux via /etc/os-release ---
    os_release = _run_safe(runner, "cat /etc/os-release 2>/dev/null")
    if os_release:
        fields = _parse_os_release(os_release)
        info.update(fields)
        distro_id = fields.get("ID", "").lower()
        distro_like = fields.get("ID_LIKE", "").lower()

        if distro_id == "ubuntu" or "ubuntu" in distro_like:
            info["os"] = "Ubuntu"
            info["version"] = fields.get("VERSION_ID", "")
            return Environment.UBUNTU, info

        if distro_id == "debian" or "debian" in distro_like:
            info["os"] = "Debian"
            info["version"] = fields.get("VERSION_ID", "")
            return Environment.DEBIAN, info

    # --- uname fallback ---
    uname = _run_safe(runner, "uname -s")
    if uname:
        info["uname"] = uname
        if "linux" in uname.lower():
            return Environment.UNKNOWN, info
        if "darwin" in uname.lower():
            info["os"] = "macOS"
            return Environment.UNKNOWN, info

    return Environment.UNKNOWN, info


def _parse_os_release(text: str) -> dict[str, str]:
    """Parse KEY=VALUE or KEY="VALUE" lines from /etc/os-release."""
    result: dict[str, str] = {}
    for line in text.splitlines():
        m = re.match(r'^([A-Z_]+)=["\']?([^"\']*)["\']?$', line.strip())
        if m:
            result[m.group(1)] = m.group(2)
    return result
