# date: 2026-06-27
# dev: myf
"""AegisOS 后端 FastAPI 应用入口。

本模块负责创建并配置 FastAPI 应用实例，包括：日志初始化、CORS 跨域、
Trace ID 中间件、健康检查/网关/WebSocket 路由挂载、统一错误响应格式化，
以及基于 lifespan 的数据库引擎初始化与释放。配置统一从
:mod:`tooling.configs.settings` 读取，支持环境变量 > .env > defaults.yaml
的多级覆盖。
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.core import runtime_mode
from backend.core.composition import get_composition
from backend.core.middleware import TraceMiddleware, get_trace_id
from backend.core.routes import router as gateway_router
from backend.routers.health import router as health_router
from backend.routers.infra import router as infra_router
from backend.routers.stream import router as stream_router
from backend.routers.system import router as system_router
from backend.routers.ws import router as ws_router
from infrastructure.nodes.descriptor import NodeProfile, ProviderKind, Tier
from tooling.configs.settings import settings

if TYPE_CHECKING:
    from infrastructure.nodes.registry import NodeRegistry

# 日志级别与格式从统一配置读取；级别字符串映射到 logging 模块常量。
logging.basicConfig(
    level=getattr(logging, settings.logging.level.upper(), logging.INFO),
    format=settings.logging.format,
)

# CORS 来源从 tooling/configs/settings.py 读取（env > .env > defaults.yaml）。
_CORS_ORIGINS = list(settings.cors.origins)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """应用生命周期：启动时初始化数据库，停止时释放引擎。

    Args:
        app: 当前 FastAPI 应用实例（此处未直接使用，保留参数以符合 lifespan 协议）。

    Yields:
        无返回值；yield 之前的逻辑在启动时执行，之后的逻辑在关闭时执行。
    """
    runtime_mode.init()  # R7: 先解析运行时模式（mock/real），再装配 composition
    comp = get_composition()
    await comp.startup()
    _init_infra_service()
    logging.getLogger("aegis.main").info("AegisOS backend started (version 0.1.0)")
    try:
        yield
    finally:
        await comp.shutdown()
        logging.getLogger("aegis.main").info("AegisOS backend stopped")


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用实例。

    组装中间件（CORS、Trace）、挂载路由（健康检查、网关、WebSocket），
    并注册统一格式的异常处理器。

    Returns:
        配置完成的 :class:`fastapi.FastAPI` 应用实例。
    """
    app = FastAPI(title="AegisOS Backend", version=settings.backend.version, lifespan=lifespan)

    # --- 中间件 ---
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(TraceMiddleware)

    # --- 路由 ---
    # 健康检查为公开接口（无需鉴权），直接挂载到 app 上。
    app.include_router(health_router, prefix="/api/v1")
    # 基础设施端点（端边云节点/派发/历史）
    app.include_router(infra_router, prefix="/api/v1")
    # R7: 运行时模式（mock/真实 LLM 切换）
    app.include_router(system_router, prefix="/api/v1")
    # 网关（/api/v1/*，带鉴权）提供 /sessions、/tasks、/agents 等接口。
    app.include_router(gateway_router)
    # WebSocket 不在 /api/v1 下（规范：ws://host/ws/v1/stream）。
    app.include_router(ws_router)
    # R5.3: SDK 流式 SSE router（/api/v1/stream/*）
    app.include_router(stream_router, prefix="/api/v1")

    # --- 统一错误格式：{"code", "message", "trace_id"} ---
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        """将 HTTPException 转换为统一格式的 JSON 响应。

        Args:
            request: 触发异常的请求对象，用于读取 trace id。
            exc: 捕获的 HTTPException。

        Returns:
            统一格式的 :class:`fastapi.responses.JSONResponse`，包含
            ``code``、``message`` 与 ``trace_id`` 三个字段。
        """
        trace_id = get_trace_id(request)
        # detail 若为 dict，则允许调用方自定义 code/message。
        if isinstance(exc.detail, dict):
            code = exc.detail.get("code", _code_for_status(exc.status_code))
            message = exc.detail.get("message", "")
        else:
            code = _code_for_status(exc.status_code)
            message = str(exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": code, "message": message, "trace_id": trace_id},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """兜底处理所有未捕获异常，返回 500 统一错误响应。

        Args:
            request: 触发异常的请求对象，用于读取 trace id。
            exc: 捕获的未处理异常。

        Returns:
            状态码 500 的统一格式 :class:`fastapi.responses.JSONResponse`。
        """
        logging.getLogger("aegis.main").exception("Unhandled error: %s", exc)
        return JSONResponse(
            status_code=500,
            content={
                "code": "INTERNAL",
                "message": "internal server error",
                "trace_id": get_trace_id(request),
            },
        )

    return app


def _code_for_status(status_code: int) -> str:
    """将 HTTP 状态码映射为业务错误码字符串。

    Args:
        status_code: HTTP 状态码（如 404、422）。

    Returns:
        对应的业务错误码字符串（如 ``NOT_FOUND``）；未匹配时返回
        ``HTTP_<status_code>``。
    """
    return {
        400: "INVALID_REQUEST",
        401: "AUTH_FAILED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
        500: "INTERNAL",
    }.get(status_code, f"HTTP_{status_code}")


# 模块级应用实例，供 uvicorn 通过 backend.main:app 加载。
# 模块级 infra 服务实例，供 router 通过 _get_service() 访问。
_infra_service = None

app = create_app()


def _init_infra_service() -> None:
    """延迟初始化 infra 服务（创建 registry + dispatcher 单例）。"""
    global _infra_service
    if _infra_service is not None:
        return

    from backend.services.infra_service import InfraService
    from infrastructure.nodes.descriptor import NodeProfile, load_node_profiles
    from infrastructure.nodes.dispatcher import ExecutionDispatcher
    from infrastructure.nodes.registry import NodeRegistry

    registry = NodeRegistry()

    # 从配置文件加载节点，未配置的用 mock fallback 补全
    profiles, skipped = load_node_profiles()
    has_device = False
    has_edge = False
    has_cloud = False

    for p in profiles:
        _register_profile(registry, p)
        if p.tier == "device":
            has_device = True
        elif p.tier == "edge":
            has_edge = True
        elif p.tier == "cloud":
            has_cloud = True

    if not has_device:
        _register_profile(registry, NodeProfile(
            node_id="device_local", tier=Tier.DEVICE,
            base_url="http://localhost:11434", provider=ProviderKind.OLLAMA,
            model_id="mock:0.5b", capabilities=["chat"], cost_weight=0.1,
        ))
    if not has_edge:
        _register_profile(registry, NodeProfile(
            node_id="edge_server_01", tier=Tier.EDGE,
            base_url="http://localhost:8900", provider=ProviderKind.AEGIS_EDGE,
            model_id="mock:7b", capabilities=["chat", "reasoning"],
            cost_weight=1.0,
        ))
    if not has_cloud:
        _register_profile(registry, NodeProfile(
            node_id="cloud_api", tier=Tier.CLOUD,
            base_url="http://localhost:8001", provider=ProviderKind.OPENAI_API,
            model_id="mock:gpt-4o", capabilities=["chat", "reasoning", "long_context"],
            cost_weight=10.0,
        ))

    dispatcher = ExecutionDispatcher(
        registry,
        enable_cascade=True,
        confidence_threshold=0.6,
    )
    _infra_service = InfraService(registry=registry, dispatcher=dispatcher)

    # 启动时立即探活一轮——真实 ping 每个节点，不通的标记 offline
    import logging as _logging
    import threading as _threading
    _log = _logging.getLogger("aegis.main")
    registry.tick()
    for snap in registry.snapshot():
        _log.info(
            "节点探活: %s (%s) → %s",
            snap["node_id"], snap["tier"], snap["status"],
        )

    # 后台定时探活（每 15 秒），让前端看到实时状态
    # 附带：监视 infrastructure.yaml / .env 的修改时间——配置变了自动热重载节点
    # （换 API 厂商 / 换 Key / 换模型，无需重启后端，前端 5 秒内自动刷新显示）
    def _bg_tick() -> None:
        import os
        import time as _t

        _cfg_path = Path("tooling/configs/infrastructure.yaml")
        _env_path = Path("tooling/configs/.env")
        _last_cfg = _cfg_path.stat().st_mtime if _cfg_path.exists() else 0.0
        _last_env = _env_path.stat().st_mtime if _env_path.exists() else 0.0

        def _reload_nodes() -> None:
            """重新加载 .env + 节点档案并注册（覆盖同名节点，新增节点直接注册）。"""
            nonlocal _last_cfg, _last_env
            try:
                # 先把 .env 的新值刷进 os.environ（支持换厂商/换 Key 不重启）
                if _env_path.exists():
                    for line in _env_path.read_text(encoding="utf-8").splitlines():
                        line = line.strip()
                        if not line or line.startswith("#") or "=" not in line:
                            continue
                        key, _, val = line.partition("=")
                        key, val = key.strip(), val.strip().strip("'\"")
                        if key:
                            os.environ[key] = val

                profiles, skipped = load_node_profiles()
                _log.info(
                    "检测到配置变更，热重载节点: %d 个加载, %d 个跳过 %s",
                    len(profiles), len(skipped), skipped or "",
                )
                for p in profiles:
                    try:
                        _register_profile(registry, p)
                    except Exception as exc:  # noqa: BLE001
                        _log.warning("热重载注册 %s 失败: %s", p.node_id, exc)
                registry.tick()
                for snap in registry.snapshot():
                    _log.info(
                        "热重载探活: %s (%s) → %s [%s]",
                        snap["node_id"], snap["tier"], snap["status"],
                        snap.get("vendor", "?"),
                    )
            except Exception as exc:  # noqa: BLE001
                _log.warning("热重载失败: %s", exc)

        while True:
            try:
                registry.tick()
                # 配置文件 mtime 检查——3 秒轮询（只 stat 两个文件，开销可忽略；
                # 探活仍是 15s 一轮，换厂商最多 3 秒生效）
                cfg_m = _cfg_path.stat().st_mtime if _cfg_path.exists() else 0.0
                env_m = _env_path.stat().st_mtime if _env_path.exists() else 0.0
                if cfg_m != _last_cfg or env_m != _last_env:
                    _last_cfg, _last_env = cfg_m, env_m
                    _reload_nodes()
            except Exception:
                pass
            _t.sleep(3)

    _t = _threading.Thread(target=_bg_tick, daemon=True)
    _t.start()


def _register_profile(registry: NodeRegistry, profile: NodeProfile) -> None:
    """用 NodeProfile 注册一个节点到 registry。

    根据 provider+tier 选择合适的节点实现：
    - device + ollama → DeviceNode（真实 Ollama 推理）
    - 其他 → _MockNode（mock 回退，保证无环境下可演示）
    """
    def _make(prof: NodeProfile) -> object:
        # 端侧：真实 Ollama 推理
        if str(prof.tier) == "device" and prof.provider == "ollama":
            try:
                from infrastructure.nodes.device.device_node import DeviceNode
                return DeviceNode(prof)
            except Exception:
                pass  # 构造失败，回退 mock

        # 云侧：真实 OpenAI 兼容 API（DeepSeek/OpenAI 等）
        if str(prof.tier) == "cloud" and prof.provider == "openai_api":
            try:
                from infrastructure.nodes.cloud.cloud_node import CloudNode
                return CloudNode(prof)
            except Exception:
                pass  # 构造失败，回退 mock

        # 其余回退 mock（但 health 做真实 HTTP 探活）
        class _MockNode:
            profile: NodeProfile = prof
            health: Any = None
            infer: Any = None

        def _health(self: object, timeout_s: float = 3.0) -> bool:
            """真实探活：去 ping 节点的 base_url，通才在线。"""
            import urllib.error
            import urllib.request
            try:
                req = urllib.request.Request(
                    f"{prof.base_url}/health",
                    method="GET",
                )
                urllib.request.urlopen(req, timeout=timeout_s)
                return True
            except Exception:
                # base_url/health 不通，试试 base_url 本身（如 Ollama /api/tags）
                try:
                    req = urllib.request.Request(prof.base_url, method="GET")
                    urllib.request.urlopen(req, timeout=timeout_s)
                    return True
                except Exception:
                    return False

        _MockNode.health = _health
        def _infer(self: object, prompt: str, system: str = "") -> object:
            from infrastructure.nodes.descriptor import InferenceResult
            tier_name = prof.tier.value if hasattr(prof.tier, "value") else str(prof.tier)
            reply = f"[{tier_name} mock] 收到: {prompt[:60]}"
            return InferenceResult(
                ok=True, text=reply, node_id=prof.node_id,
                tier=tier_name, model_id=prof.model_id,
                latency_ms=12,
                usage={"prompt_tokens": len(prompt), "completion_tokens": len(reply)},
            )
        _MockNode.infer = _infer
        return _MockNode()
    registry.register_node(_make(profile))
