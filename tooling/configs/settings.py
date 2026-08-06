# date: 2026-07-04
# dev: myf
"""
AegisOS 统一配置加载器。

优先级（高 → 低）:
  1. 环境变量（AEGIS_* / VITE_*）
  2. tooling/configs/.env
  3. tooling/configs/defaults.yaml
  4. 代码内置默认值

用法::

    from tooling.configs.settings import settings

    settings.backend.host          # "0.0.0.0"
    settings.backend.port          # 8000
    settings.cors.origins          # ["http://localhost:5173", ...]
    settings.auth.default_key      # "aegis-dev-key"
    settings.database.url          # "sqlite+aiosqlite:///./data/aegisos.db"
    settings.frontend_env.VITE_API_BASE_URL  # "http://localhost:8000/api/v1"
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# --- 内部工具 ----------------------------------------------------------------

_CONFIGS_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _CONFIGS_DIR.parents[1]


def _load_dotenv() -> None:
    """Load ``.env`` file into ``os.environ`` if it exists (does not override)."""
    env_path = _CONFIGS_DIR / ".env"
    if not env_path.exists():
        return
    try:
        from dotenv import dotenv_values
    except ImportError:
        # python-dotenv 未安装时手动解析
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip("'\"")
            if key and key not in os.environ:
                os.environ[key] = val
        return
    for key, val in dotenv_values(env_path).items():
        if key and val is not None and key not in os.environ:
            os.environ[key] = val


def _load_yaml_defaults() -> dict:
    """Load ``defaults.yaml`` as a plain dict (PyYAML optional)."""
    yaml_path = _CONFIGS_DIR / "defaults.yaml"
    if not yaml_path.exists():
        return {}
    try:
        import yaml
    except ImportError:
        return {}
    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def _env(key: str, default: str | None = None) -> str | None:
    """Read env var, return *default* when unset / empty."""
    val = os.environ.get(key)
    return val if val else default


def _env_int(key: str, default: int) -> int:
    val = _env(key)
    if val is None:
        return default
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


def _env_bool(key: str, default: bool) -> bool:
    val = _env(key)
    if val is None:
        return default
    return val.lower() in ("1", "true", "yes", "on")


def _env_list(key: str, default: list[str]) -> list[str]:
    """逗号分隔的列表。"""
    val = _env(key)
    if val is None:
        return default
    return [item.strip() for item in val.split(",") if item.strip()]


# --- 配置 dataclass ----------------------------------------------------------


@dataclass(frozen=True)
class BackendConfig:
    host: str = "0.0.0.0"
    port: int = 8000
    version: str = "0.1.0"


@dataclass(frozen=True)
class FrontendConfig:
    host: str = "localhost"
    port: int = 5173


@dataclass(frozen=True)
class CorsConfig:
    enabled: bool = True
    origins: tuple[str, ...] = (
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    )


@dataclass(frozen=True)
class AuthConfig:
    enabled: bool = True
    mode: str = "api-key"
    api_key_header: str = "X-API-Key"
    default_key: str = "aegis-dev-key"


@dataclass(frozen=True)
class DatabaseConfig:
    url: str = "sqlite+aiosqlite:///./data/aegisos.db"
    echo: bool = False


@dataclass(frozen=True)
class LoggingConfig:
    level: str = "INFO"
    format: str = "%(asctime)s %(levelname)s %(name)s %(message)s"


@dataclass(frozen=True)
class RateLimitConfig:
    enabled: bool = True
    rpm: int = 120


@dataclass(frozen=True)
class TraceConfig:
    enabled: bool = True
    header: str = "X-Trace-Id"


@dataclass(frozen=True)
class FrontendEnvConfig:
    """前端构建时注入的环境变量（Vite import.meta.env）。"""

    VITE_API_BASE_URL: str = "http://localhost:8000/api/v1"
    VITE_WS_URL: str = "ws://localhost:8000/ws/v1/stream"


@dataclass(frozen=True)
class StorageConfig:
    """数据层存储后端配置。

    Attributes:
        graph_mode: 图存储模式（in_memory / neo4j）。
        vector_mode: 向量存储模式（in_memory / qdrant）。
        neo4j_uri: Neo4j bolt 地址。
        neo4j_user: Neo4j 用户名。
        neo4j_password: Neo4j 密码。
        qdrant_url: Qdrant 服务地址。
        qdrant_api_key: Qdrant API Key。
        qdrant_collection: Qdrant 集合名。
    """

    graph_mode: str = "in_memory"
    vector_mode: str = "in_memory"
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = ""
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    qdrant_collection: str = "memory_vectors"


@dataclass(frozen=True)
class Settings:
    """全局配置根。所有模块统一从此读取，禁直接 ``os.environ`` / 硬编码。"""

    backend: BackendConfig = field(default_factory=BackendConfig)
    frontend: FrontendConfig = field(default_factory=FrontendConfig)
    cors: CorsConfig = field(default_factory=CorsConfig)
    auth: AuthConfig = field(default_factory=AuthConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig)
    trace: TraceConfig = field(default_factory=TraceConfig)
    frontend_env: FrontendEnvConfig = field(default_factory=FrontendEnvConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)


# --- 单例构建 ----------------------------------------------------------------


def _build_settings() -> Settings:
    """合并 defaults.yaml + .env + 环境变量，返回不可变 ``Settings``。"""
    _load_dotenv()
    defaults = _load_yaml_defaults()

    # --- 从 defaults.yaml 提取默认值 ---
    be = defaults.get("backend", {})
    fe = defaults.get("frontend", {})
    cors = defaults.get("cors", {})
    auth = defaults.get("auth", {})
    db = defaults.get("database", {})
    log = defaults.get("logging", {})
    rl = defaults.get("rate_limit", {})
    tr = defaults.get("trace", {})
    fe_env = defaults.get("frontend_env", {})
    st = defaults.get("storage", {})

    cors_origins_default = list(
        cors.get("origins", ["http://localhost:5173", "http://127.0.0.1:5173"])
    )

    return Settings(
        backend=BackendConfig(
            host=_env("AEGIS_BACKEND_HOST", be.get("host", "0.0.0.0")) or "0.0.0.0",
            port=_env_int("AEGIS_BACKEND_PORT", int(be.get("port", 8000))),
            version=_env("AEGIS_BACKEND_VERSION", be.get("version", "0.1.0")) or "0.1.0",
        ),
        frontend=FrontendConfig(
            host=_env("AEGIS_FRONTEND_HOST", fe.get("host", "localhost")) or "localhost",
            port=_env_int("AEGIS_FRONTEND_PORT", int(fe.get("port", 5173))),
        ),
        cors=CorsConfig(
            enabled=_env_bool("AEGIS_CORS_ENABLED", bool(cors.get("enabled", True))),
            origins=tuple(_env_list("AEGIS_CORS_ORIGINS", cors_origins_default)),
        ),
        auth=AuthConfig(
            enabled=_env_bool("AEGIS_AUTH_ENABLED", bool(auth.get("enabled", True))),
            mode=_env("AEGIS_AUTH_MODE", auth.get("mode", "api-key")) or "api-key",
            api_key_header=_env(
                "AEGIS_AUTH_API_KEY_HEADER", auth.get("api_key_header", "X-API-Key")
            )
            or "X-API-Key",
            default_key=_env("AEGIS_AUTH_DEFAULT_KEY", auth.get("default_key", "aegis-dev-key"))
            or "aegis-dev-key",
        ),
        database=DatabaseConfig(
            url=_env("AEGIS_DATABASE_URL", db.get("url", "sqlite+aiosqlite:///./data/aegisos.db"))
            or "sqlite+aiosqlite:///./data/aegisos.db",
            echo=_env_bool("AEGIS_DATABASE_ECHO", bool(db.get("echo", False))),
        ),
        logging=LoggingConfig(
            level=_env("AEGIS_LOG_LEVEL", log.get("level", "INFO")) or "INFO",
            format=_env(
                "AEGIS_LOG_FORMAT",
                log.get("format", "%(asctime)s %(levelname)s %(name)s %(message)s"),
            )
            or "%(asctime)s %(levelname)s %(name)s %(message)s",
        ),
        rate_limit=RateLimitConfig(
            enabled=_env_bool("AEGIS_RATE_LIMIT_ENABLED", bool(rl.get("enabled", True))),
            rpm=_env_int("AEGIS_RATE_LIMIT_RPM", int(rl.get("rpm", 120))),
        ),
        trace=TraceConfig(
            enabled=_env_bool("AEGIS_TRACE_ENABLED", bool(tr.get("enabled", True))),
            header=_env("AEGIS_TRACE_HEADER", tr.get("header", "X-Trace-Id")) or "X-Trace-Id",
        ),
        frontend_env=FrontendEnvConfig(
            VITE_API_BASE_URL=_env(
                "VITE_API_BASE_URL", fe_env.get("VITE_API_BASE_URL", "http://localhost:8000/api/v1")
            )
            or "http://localhost:8000/api/v1",
            VITE_WS_URL=_env(
                "VITE_WS_URL", fe_env.get("VITE_WS_URL", "ws://localhost:8000/ws/v1/stream")
            )
            or "ws://localhost:8000/ws/v1/stream",
        ),
        storage=StorageConfig(
            graph_mode=_env("AEGIS_STORAGE_GRAPH_MODE", st.get("graph_mode", "in_memory"))
            or "in_memory",
            vector_mode=_env("AEGIS_STORAGE_VECTOR_MODE", st.get("vector_mode", "in_memory"))
            or "in_memory",
            neo4j_uri=_env("AEGIS_STORAGE_NEO4J_URI", st.get("neo4j_uri", "bolt://localhost:7687"))
            or "bolt://localhost:7687",
            neo4j_user=_env("AEGIS_STORAGE_NEO4J_USER", st.get("neo4j_user", "neo4j")) or "neo4j",
            neo4j_password=_env("AEGIS_STORAGE_NEO4J_PASSWORD", st.get("neo4j_password", "")) or "",
            qdrant_url=_env(
                "AEGIS_STORAGE_QDRANT_URL", st.get("qdrant_url", "http://localhost:6333")
            )
            or "http://localhost:6333",
            qdrant_api_key=_env("AEGIS_STORAGE_QDRANT_API_KEY", st.get("qdrant_api_key", "")) or "",
            qdrant_collection=_env(
                "AEGIS_STORAGE_QDRANT_COLLECTION", st.get("qdrant_collection", "memory_vectors")
            )
            or "memory_vectors",
        ),
    )


# 模块级单例——import 即用
settings: Settings = _build_settings()
