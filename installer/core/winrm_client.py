from __future__ import annotations

import base64
from typing import Optional

import winrm


class WinRMError(RuntimeError):
    """Raised when a WinRM command fails or the connection cannot be established."""


class WinRMClient:
    """Thin wrapper around pywinrm satisfying the CommandRunner protocol."""

    def __init__(
        self,
        host: str,
        user: str,
        password: str,
        transport: str = "ntlm",
        use_ssl: bool = False,
        port: Optional[int] = None,
    ) -> None:
        self.host = host
        self.user = user
        self.password = password
        self.transport = transport
        self.use_ssl = use_ssl
        self.port = port or (5986 if use_ssl else 5985)
        self._session: Optional[winrm.Session] = None

    def connect(self) -> None:
        scheme = "https" if self.use_ssl else "http"
        endpoint = f"{scheme}://{self.host}:{self.port}/wsman"
        try:
            self._session = winrm.Session(
                endpoint,
                auth=(self.user, self.password),
                transport=self.transport,
            )
        except Exception as exc:
            raise WinRMError(f"Failed to create WinRM session for {self.host}: {exc}") from exc

    @property
    def session(self) -> winrm.Session:
        if self._session is None:
            self.connect()
        assert self._session is not None
        return self._session

    def run(self, command: str) -> str:
        """Execute a PowerShell command and return stdout."""
        try:
            result = self.session.run_ps(command)
        except Exception as exc:
            raise WinRMError(f"WinRM command failed: {command}: {exc}") from exc
        if result.status_code != 0:
            err = result.std_err.decode("utf-8", errors="replace") if isinstance(result.std_err, bytes) else str(result.std_err)
            raise WinRMError(f"Command failed (exit {result.status_code}): {command}\n{err}")
        out = result.std_out.decode("utf-8", errors="replace") if isinstance(result.std_out, bytes) else str(result.std_out)
        return out

    def write_file(self, path: str, content: str) -> None:
        """Write content to a remote file via base64-encoded PowerShell command."""
        encoded = base64.b64encode(content.encode("utf-8")).decode("ascii")
        ps_cmd = (
            f"[IO.File]::WriteAllBytes('{path}', "
            f"[Convert]::FromBase64String('{encoded}'))"
        )
        self.run(ps_cmd)
