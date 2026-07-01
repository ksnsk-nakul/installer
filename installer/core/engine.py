from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from installer.core.config import InstallerConfig
from installer.core.detector import Environment, detect_environment
from installer.core.logger import get_logger
from installer.core.progress import StepProgress
from installer.adapters.base import BaseAdapter
from installer.adapters.ubuntu import UbuntuAdapter
from installer.adapters.docker import DockerAdapter
from installer.adapters.windows import WindowsAdapter
from installer.core.docker_client import DockerClientWrapper
from installer.stacks.presets import resolve_stack
from installer.verifier.api_check import APICheck, probe_project_stack
from installer.verifier.system_check import SystemCheck

logger = get_logger("installer.engine")


class EngineError(RuntimeError):
    """Raised when the engine cannot proceed with the installation."""


# Signature: (db_config: dict) -> dict  — returns updated db config with credentials
DBConfigCallback = Callable[[dict], dict]


class Engine:
    """Orchestrates the 5-step install flow."""

    def __init__(
        self,
        config: InstallerConfig,
        runner: Any,
        db_config_callback: Optional[DBConfigCallback] = None,
    ) -> None:
        self.config = config
        self.runner = runner
        self.db_config_callback = db_config_callback
        self._report: dict[str, Any] = {}

    def run(self) -> dict[str, Any]:
        """Execute the full 5-step install flow and return a deployment report."""
        progress = StepProgress()
        progress.start()
        start_time = datetime.now(timezone.utc)

        steps: list[dict] = []

        try:
            # ----------------------------------------------------------------
            # Step 1: OS / Environment Detection
            # ----------------------------------------------------------------
            with progress.step(1):
                logger.info("[step]Step 1: OS / Environment Detection[/step]")
                env, info = detect_environment(self.runner)
                if env == Environment.UNKNOWN:
                    raise EngineError(f"Unsupported environment: {info}")
                steps.append({"step": 1, "name": "OS Detection", "status": "pass", "info": info})
                logger.info(f"Detected: {env.value} — {info.get('os', '')}")

            # ----------------------------------------------------------------
            # Step 2: Load Environment Adapter
            # ----------------------------------------------------------------
            with progress.step(2):
                logger.info("[step]Step 2: Environment Adapter Load[/step]")
                adapter = self._load_adapter(env)
                steps.append({"step": 2, "name": "Adapter Load", "status": "pass", "adapter": env.value})
                logger.info(f"Adapter loaded: {type(adapter).__name__}")

            # ----------------------------------------------------------------
            # Step 3: API Verification → Stack Auto-Selection
            # ----------------------------------------------------------------
            with progress.step(3):
                logger.info("[step]Step 3: API Verification & Stack Selection[/step]")
                stack_config = self.config.stack
                api_info: dict = {}

                if self.config.verify_api:
                    api_info = probe_project_stack(
                        self.config.verify_api.url,
                        timeout=self.config.verify_api.timeout,
                    )
                    logger.info(f"API probe: reachable={api_info['reachable']}, framework={api_info['framework']}")

                # Invoke DB config callback if provided (Web UI dialog hook)
                if self.db_config_callback:
                    updated_db = self.db_config_callback(stack_config.database.model_dump())
                    from installer.core.config import DatabaseConfig
                    stack_config = stack_config.model_copy(
                        update={"database": DatabaseConfig.model_validate(updated_db)}
                    )

                steps.append({
                    "step": 3,
                    "name": "API Verification",
                    "status": "pass",
                    "api_info": api_info,
                })

            # ----------------------------------------------------------------
            # Step 4: Stack Installation
            # ----------------------------------------------------------------
            with progress.step(4):
                logger.info("[step]Step 4: Stack Installation[/step]")
                resolved = resolve_stack(stack_config, adapter)

                # 4a: Database
                logger.info("  4a: Database layer")
                resolved.db.setup()

                # 4b: Backend
                logger.info("  4b: Backend layer")
                resolved.backend.run_all(self.config.project_path)

                # 4c: Frontend
                logger.info("  4c: Frontend layer")
                resolved.frontend.run_all(self.config.project_path)

                steps.append({"step": 4, "name": "Installation", "status": "pass"})

            # ----------------------------------------------------------------
            # Step 5: Post-Install Checks
            # ----------------------------------------------------------------
            with progress.step(5):
                logger.info("[step]Step 5: Post-Install Checks[/step]")
                sys_check = SystemCheck()
                check_results = sys_check.run(
                    self.runner,
                    domain=self.config.domain if self.config.domain else None,
                    db_engine=stack_config.database.engine,
                    db_config=stack_config.database.model_dump(),
                )

                if self.config.verify_api:
                    api_result = APICheck().probe(
                        url=self.config.verify_api.url,
                        method=self.config.verify_api.method,
                        expect_status=self.config.verify_api.expect_status,
                        expect_json=self.config.verify_api.expect_json,
                        timeout=self.config.verify_api.timeout,
                        retries=self.config.verify_api.retries,
                    )
                    check_results.append(
                        type("R", (), {
                            "name": "api_health",
                            "status": api_result.status,
                            "detail": api_result.detail,
                            "fix_hint": None,
                        })()
                    )

                summary = SystemCheck.summary(check_results)
                overall_status = "pass" if summary.get("fail", 0) == 0 else "warn"
                steps.append({
                    "step": 5,
                    "name": "Post Checks",
                    "status": overall_status,
                    "summary": summary,
                })

            progress.finish(success=True)

        except Exception as exc:
            logger.error(f"Engine failed: {exc}")
            progress.finish(success=False)
            steps.append({"step": -1, "name": "Error", "status": "fail", "error": str(exc)})
            raise

        return self._build_report(start_time, steps, stack_config)

    def _load_adapter(self, env: Environment) -> BaseAdapter:
        if env in (Environment.UBUNTU, Environment.DEBIAN):
            return UbuntuAdapter(self.runner)
        if env == Environment.DOCKER:
            client = DockerClientWrapper()
            client._client = getattr(self.runner, "_docker_client", None)
            return DockerAdapter(client)
        if env == Environment.WINDOWS:
            return WindowsAdapter(self.runner)
        raise EngineError(f"No adapter for environment: {env}")

    def _build_report(
        self, start_time: datetime, steps: list[dict], stack_config: Any
    ) -> dict[str, Any]:
        report: dict[str, Any] = {
            "project": self.config.domain,
            "timestamp": start_time.isoformat(),
            "stack": {
                "database": {
                    "engine": stack_config.database.engine,
                    "mode": stack_config.database.mode,
                },
                "backend": {"framework": stack_config.backend.framework},
                "frontend": {"framework": stack_config.frontend.framework},
            },
            "steps": steps,
            "issues": [
                s for s in steps
                if s.get("status") in ("fail", "warn")
            ],
        }
        return report
