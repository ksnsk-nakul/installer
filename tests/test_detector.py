import pytest
from unittest.mock import MagicMock

from installer.core.detector import detect_environment, Environment, DetectionError


def make_runner(outputs: dict[str, str]):
    """Create a mock runner that returns preset outputs per command."""
    runner = MagicMock()

    def run_side_effect(cmd: str) -> str:
        for key, val in outputs.items():
            if key in cmd:
                return val
        raise RuntimeError(f"Command not mocked: {cmd}")

    runner.run.side_effect = run_side_effect
    return runner


UBUNTU_OS_RELEASE = """
NAME="Ubuntu"
VERSION="22.04.3 LTS (Jammy Jellyfish)"
ID=ubuntu
ID_LIKE=debian
VERSION_ID="22.04"
""".strip()

DEBIAN_OS_RELEASE = """
NAME="Debian GNU/Linux"
ID=debian
VERSION_ID="12"
""".strip()


def test_detects_ubuntu(tmp_path):
    runner = make_runner({
        "ver": "",
        "/.dockerenv": "no",
        "/proc/1/cgroup": "",
        "/etc/os-release": UBUNTU_OS_RELEASE,
    })
    env, info = detect_environment(runner)
    assert env == Environment.UBUNTU
    assert info["os"] == "Ubuntu"
    assert info["version"] == "22.04"


def test_detects_debian():
    runner = make_runner({
        "ver": "",
        "/.dockerenv": "no",
        "/proc/1/cgroup": "",
        "/etc/os-release": DEBIAN_OS_RELEASE,
    })
    env, info = detect_environment(runner)
    assert env == Environment.DEBIAN
    assert info["os"] == "Debian"


def test_detects_docker_via_dockerenv():
    runner = make_runner({
        "ver": "",
        "/.dockerenv": "yes",
    })
    env, info = detect_environment(runner)
    assert env == Environment.DOCKER


def test_detects_docker_via_cgroup():
    runner = make_runner({
        "ver": "",
        "/.dockerenv": "no",
        "/proc/1/cgroup": "12:blkio:/docker/abc123",
    })
    env, info = detect_environment(runner)
    assert env == Environment.DOCKER


def test_detects_windows():
    runner = make_runner({
        "ver": "Microsoft Windows [Version 10.0.19041.0]",
    })
    env, info = detect_environment(runner)
    assert env == Environment.WINDOWS
    assert info["os"] == "Windows"


def test_unknown_when_no_match():
    runner = MagicMock()
    runner.run.side_effect = RuntimeError("connection refused")
    env, info = detect_environment(runner)
    assert env == Environment.UNKNOWN


def test_unknown_on_macos():
    runner = make_runner({
        "ver": "",
        "/.dockerenv": "no",
        "/proc/1/cgroup": "",
        "/etc/os-release": "",
        "uname": "Darwin",
    })
    env, info = detect_environment(runner)
    assert env == Environment.UNKNOWN
    assert info.get("os") == "macOS"
