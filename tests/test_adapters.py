from unittest.mock import MagicMock

import pytest

from installer.adapters.ubuntu import UbuntuAdapter
from installer.adapters.docker import DockerAdapter
from installer.adapters.windows import WindowsAdapter


UBUNTU_OS_RELEASE = """
NAME="Ubuntu"
ID=ubuntu
ID_LIKE=debian
VERSION_ID="22.04"
""".strip()


def make_runner(outputs: dict[str, str]):
    runner = MagicMock()

    def run_side_effect(cmd: str) -> str:
        for key, val in outputs.items():
            if key in cmd:
                return val
        return ""

    runner.run.side_effect = run_side_effect
    return runner


# ---------------------------------------------------------------------------
# UbuntuAdapter
# ---------------------------------------------------------------------------

def test_ubuntu_detect_true():
    runner = make_runner({
        "ver": "",
        "/.dockerenv": "no",
        "/proc/1/cgroup": "",
        "/etc/os-release": UBUNTU_OS_RELEASE,
    })
    adapter = UbuntuAdapter(runner)
    assert adapter.detect() is True
    assert adapter.get_info()["os"] == "Ubuntu"


def test_ubuntu_detect_false_on_windows():
    runner = make_runner({"ver": "Microsoft Windows [Version 10.0]"})
    adapter = UbuntuAdapter(runner)
    assert adapter.detect() is False


def test_ubuntu_install_packages_calls_apt():
    runner = MagicMock()
    adapter = UbuntuAdapter(runner)
    adapter.install_packages(["nginx", "php8.2"])
    calls = [c.args[0] for c in runner.run.call_args_list]
    assert any("apt-get update" in c for c in calls)
    assert any("apt-get install -y nginx php8.2" in c for c in calls)


def test_ubuntu_install_packages_empty_noop():
    runner = MagicMock()
    adapter = UbuntuAdapter(runner)
    adapter.install_packages([])
    runner.run.assert_not_called()


def test_ubuntu_start_service():
    runner = MagicMock()
    adapter = UbuntuAdapter(runner)
    adapter.start_service("nginx")
    runner.run.assert_called_with("systemctl start nginx")


def test_ubuntu_open_port():
    runner = MagicMock()
    adapter = UbuntuAdapter(runner)
    adapter.open_port(443, "tcp")
    runner.run.assert_called_with("ufw allow 443/tcp")


def test_ubuntu_write_file_uses_runner_write_file_if_present():
    runner = MagicMock()
    runner.write_file = MagicMock()
    adapter = UbuntuAdapter(runner)
    adapter.write_file("/etc/test.conf", "hello")
    runner.write_file.assert_called_with("/etc/test.conf", "hello")


def test_ubuntu_run_delegates():
    runner = MagicMock()
    runner.run.return_value = "output"
    adapter = UbuntuAdapter(runner)
    assert adapter.run("ls") == "output"


# ---------------------------------------------------------------------------
# DockerAdapter
# ---------------------------------------------------------------------------

def test_docker_detect_true():
    client = MagicMock()
    client.connect.return_value = None
    adapter = DockerAdapter(client)
    assert adapter.detect() is True


def test_docker_detect_false_on_exception():
    client = MagicMock()
    client.connect.side_effect = Exception("daemon unreachable")
    adapter = DockerAdapter(client)
    assert adapter.detect() is False


def test_docker_install_packages_runs_combined_cmd():
    client = MagicMock()
    adapter = DockerAdapter(client)
    adapter.install_packages(["curl"])
    client.run.assert_called_once()
    cmd = client.run.call_args.args[0]
    assert "apt-get install -y curl" in cmd
    assert "apk add" in cmd


def test_docker_open_port_is_noop():
    client = MagicMock()
    adapter = DockerAdapter(client)
    adapter.open_port(80)
    client.run.assert_not_called()


def test_docker_generate_dockerfile():
    client = MagicMock()
    adapter = DockerAdapter(client)
    content = adapter.generate_dockerfile("node:20", ["npm install", "npm run build"])
    assert content.startswith("FROM node:20\n")
    assert "RUN npm install" in content
    assert "RUN npm run build" in content


def test_docker_write_file_delegates():
    client = MagicMock()
    adapter = DockerAdapter(client)
    adapter.write_file("/app/.env", "KEY=value")
    client.write_file.assert_called_with("/app/.env", "KEY=value")


def test_docker_get_info_delegates():
    client = MagicMock()
    client.info.return_value = {"ServerVersion": "24.0"}
    adapter = DockerAdapter(client)
    assert adapter.get_info() == {"ServerVersion": "24.0"}


# ---------------------------------------------------------------------------
# WindowsAdapter
# ---------------------------------------------------------------------------

def test_windows_detect_true():
    runner = make_runner({"ver": "Microsoft Windows [Version 10.0.19041]"})
    adapter = WindowsAdapter(runner)
    assert adapter.detect() is True


def test_windows_detect_false_on_ubuntu():
    runner = make_runner({
        "ver": "",
        "/.dockerenv": "no",
        "/proc/1/cgroup": "",
        "/etc/os-release": UBUNTU_OS_RELEASE,
    })
    adapter = WindowsAdapter(runner)
    assert adapter.detect() is False


def test_windows_install_packages_uses_choco():
    runner = MagicMock()
    adapter = WindowsAdapter(runner)
    adapter.install_packages(["nodejs", "iis"])
    calls = [c.args[0] for c in runner.run.call_args_list]
    assert "choco install nodejs -y" in calls
    assert "choco install iis -y" in calls


def test_windows_start_service():
    runner = MagicMock()
    adapter = WindowsAdapter(runner)
    adapter.start_service("W3SVC")
    runner.run.assert_called_with("Start-Service -Name 'W3SVC'")


def test_windows_open_port():
    runner = MagicMock()
    adapter = WindowsAdapter(runner)
    adapter.open_port(8080, "tcp")
    cmd = runner.run.call_args.args[0]
    assert "New-NetFirewallRule" in cmd
    assert "LocalPort 8080" in cmd


def test_windows_write_file_delegates():
    runner = MagicMock()
    adapter = WindowsAdapter(runner)
    adapter.write_file("C:\\app\\.env", "KEY=value")
    runner.write_file.assert_called_with("C:\\app\\.env", "KEY=value")
