from __future__ import annotations

from dataclasses import dataclass

from installer.adapters.base import BaseAdapter
from installer.core.config import StackConfig

from installer.stacks.db.base import BaseDBLayer
from installer.stacks.db.mysql import MySQLLayer
from installer.stacks.db.postgres import PostgresLayer
from installer.stacks.db.mongodb import MongoDBLayer
from installer.stacks.db.external import ExternalDBLayer

from installer.stacks.backend.base import BaseBackend
from installer.stacks.backend.laravel import LaravelBackend
from installer.stacks.backend.node import NodeBackend
from installer.stacks.backend.python_app import PythonBackend
from installer.stacks.backend.java import JavaBackend

from installer.stacks.frontend.base import BaseFrontend, NoneFrontend
from installer.stacks.frontend.react import ReactFrontend
from installer.stacks.frontend.vue import VueFrontend
from installer.stacks.frontend.angular import AngularFrontend
from installer.stacks.frontend.ssr import SSRFrontend


DB_ENGINES: dict[str, type[BaseDBLayer]] = {
    "mysql": MySQLLayer,
    "postgresql": PostgresLayer,
    "mongodb": MongoDBLayer,
}

BACKEND_FRAMEWORKS: dict[str, type[BaseBackend]] = {
    "laravel": LaravelBackend,
    "node": NodeBackend,
    "django": PythonBackend,
    "fastapi": PythonBackend,
    "flask": PythonBackend,
    "java": JavaBackend,
}

FRONTEND_FRAMEWORKS: dict[str, type[BaseFrontend]] = {
    "react": ReactFrontend,
    "vue": VueFrontend,
    "angular": AngularFrontend,
    "next": SSRFrontend,
    "nuxt": SSRFrontend,
    "blade": SSRFrontend,
    "jinja2": SSRFrontend,
}


class UnknownStackComponentError(ValueError):
    """Raised when a stack config references an unsupported engine/framework."""


@dataclass
class ResolvedStack:
    db: BaseDBLayer
    backend: BaseBackend
    frontend: BaseFrontend


def resolve_stack(stack_config: StackConfig, adapter: BaseAdapter) -> ResolvedStack:
    """Instantiate the concrete db/backend/frontend layer classes for a StackConfig."""
    db_engine = stack_config.database.engine
    if stack_config.database.mode == "external":
        db_cls: type[BaseDBLayer] = ExternalDBLayer
    elif db_engine in DB_ENGINES:
        db_cls = DB_ENGINES[db_engine]
    else:
        raise UnknownStackComponentError(f"Unsupported database engine: {db_engine!r}")

    backend_framework = stack_config.backend.framework
    if backend_framework not in BACKEND_FRAMEWORKS:
        raise UnknownStackComponentError(f"Unsupported backend framework: {backend_framework!r}")
    backend_cls = BACKEND_FRAMEWORKS[backend_framework]

    frontend_framework = stack_config.frontend.framework
    if frontend_framework is None:
        frontend_cls: type[BaseFrontend] = NoneFrontend
    elif frontend_framework in FRONTEND_FRAMEWORKS:
        frontend_cls = FRONTEND_FRAMEWORKS[frontend_framework]
    else:
        raise UnknownStackComponentError(f"Unsupported frontend framework: {frontend_framework!r}")

    db = db_cls(adapter, stack_config.database.model_dump())
    backend = backend_cls(adapter, stack_config.backend.model_dump())
    frontend = frontend_cls(adapter, stack_config.frontend.model_dump())

    return ResolvedStack(db=db, backend=backend, frontend=frontend)
