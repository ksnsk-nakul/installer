from unittest.mock import MagicMock, patch

import pytest

from installer.core.ssh import SSHClient, SSHError
from installer.core.docker_client import DockerClientWrapper, DockerClientError
from installer.core.winrm_client import WinRMClient, WinRMError
from installer.adapters.base import BaseAdapter


# ---------------------------------------------------------------------------
# SSHClient
# ---------------------------------------------------------------------------

def test_ssh_run_success():
    client = SSHClient(host="1.2.3.4", user="ubuntu")
    fake_paramiko = MagicMock()
    stdout = MagicMock()
    stdout.channel.recv_exit_status.return_value = 0
    stdout.read.return_value = b"hello\n"
    stderr = MagicMock()
    stderr.read.return_value = b""
    fake_paramiko.exec_command.return_value = (MagicMock(), stdout, stderr)
    client._client = fake_paramiko

    result = client.run("echo hello")
    assert result == "hello\n"


def test_ssh_run_nonzero_exit_raises():
    client = SSHClient(host="1.2.3.4", user="ubuntu")
    fake_paramiko = MagicMock()
    stdout = MagicMock()
    stdout.channel.recv_exit_status.return_value = 1
    stdout.read.return_value = b""
    stderr = MagicMock()
    stderr.read.return_value = b"command not found\n"
    fake_paramiko.exec_command.return_value = (MagicMock(), stdout, stderr)
    client._client = fake_paramiko

    with pytest.raises(SSHError, match="exit 1"):
        client.run("bogus")


def test_ssh_connect_failure_raises():
    client = SSHClient(host="bad-host", user="ubuntu", timeout=1)
    with patch("paramiko.SSHClient") as mock_ssh_cls:
        instance = mock_ssh_cls.return_value
        instance.connect.side_effect = Exception("unreachable")
        with pytest.raises(SSHError, match="Failed to connect"):
            client.connect()


# ---------------------------------------------------------------------------
# DockerClientWrapper
# ---------------------------------------------------------------------------

def test_docker_run_success():
    wrapper = DockerClientWrapper(container_name="myapp")
    fake_client = MagicMock()
    fake_container = MagicMock()
    fake_container.exec_run.return_value = (0, b"ok\n")
    fake_client.containers.get.return_value = fake_container
    wrapper._client = fake_client

    result = wrapper.run("echo ok")
    assert result == "ok\n"


def test_docker_run_no_container_raises():
    wrapper = DockerClientWrapper()
    with pytest.raises(DockerClientError, match="No container_name"):
        wrapper.run("echo hi")


def test_docker_run_nonzero_exit_raises():
    wrapper = DockerClientWrapper(container_name="myapp")
    fake_client = MagicMock()
    fake_container = MagicMock()
    fake_container.exec_run.return_value = (1, b"fail\n")
    fake_client.containers.get.return_value = fake_container
    wrapper._client = fake_client

    with pytest.raises(DockerClientError, match="exit 1"):
        wrapper.run("bogus")


# ---------------------------------------------------------------------------
# WinRMClient
# ---------------------------------------------------------------------------

def test_winrm_run_success():
    client = WinRMClient(host="1.2.3.4", user="Administrator", password="secret")
    fake_session = MagicMock()
    fake_result = MagicMock()
    fake_result.status_code = 0
    fake_result.std_out = b"done\n"
    fake_result.std_err = b""
    fake_session.run_ps.return_value = fake_result
    client._session = fake_session

    result = client.run("Get-Service")
    assert result == "done\n"


def test_winrm_run_nonzero_exit_raises():
    client = WinRMClient(host="1.2.3.4", user="Administrator", password="secret")
    fake_session = MagicMock()
    fake_result = MagicMock()
    fake_result.status_code = 1
    fake_result.std_out = b""
    fake_result.std_err = b"error occurred\n"
    fake_session.run_ps.return_value = fake_result
    client._session = fake_session

    with pytest.raises(WinRMError, match="exit 1"):
        client.run("Bad-Command")


# ---------------------------------------------------------------------------
# BaseAdapter
# ---------------------------------------------------------------------------

def test_base_adapter_is_abstract():
    with pytest.raises(TypeError):
        BaseAdapter()


def test_base_adapter_subclass_must_implement_all():
    class IncompleteAdapter(BaseAdapter):
        def detect(self) -> bool:
            return True

    with pytest.raises(TypeError):
        IncompleteAdapter()


def test_base_adapter_full_subclass_instantiates():
    class FullAdapter(BaseAdapter):
        def detect(self) -> bool:
            return True

        def install_packages(self, packages):
            pass

        def start_service(self, name):
            pass

        def enable_service(self, name):
            pass

        def open_port(self, port, protocol="tcp"):
            pass

        def write_file(self, path, content):
            pass

        def run(self, command):
            return ""

        def get_info(self):
            return {}

    adapter = FullAdapter()
    assert adapter.detect() is True
