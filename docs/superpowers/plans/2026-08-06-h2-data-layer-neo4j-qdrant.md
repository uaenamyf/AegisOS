# H2 数据层接入（Neo4j + Qdrant + 记忆子系统对接）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 AegisOS 接入 Neo4j 拓扑/ATT&CK 图与 Qdrant 向量库（双实现适配层），并对接记忆子系统 `memory/vector` 与 `memory/semantic`，默认 in_memory 零依赖可运行。

**Architecture:** `data/models/` 提供 `VectorStore`/`GraphStore` 双实现（InMemory 默认 + Neo4j/Qdrant 真实适配器惰性加载）；`data/api` 暴露 Protocol + 工厂（`create_graph_store`/`create_vector_store`/`load_attck_dataset`）；记忆模块 `VectorMemory`/`SemanticMemory`/`MemoryStore` 接受可选后端注入（默认 None 行为保持）；`backend/composition` 按 settings 装配。

**Tech Stack:** Python ≥3.11 · protocol dataclass · `neo4j>=5` 与 `qdrant-client>=1.8`（可选 extra，惰性加载）· pytest · mypy · ruff

## Global Constraints

- **Import 铁律（03_IMPORT_SPEC）**：跨域只 `from data.api import ...`；禁止 `data.models` / `data.datasets` 被 `data/` 外 import；`data/` 只依赖 `protocol/`；`neo4j`/`qdrant-client` 惰性加载。
- **AI 编码规范（11_AI_CODING_SPEC）**：单次 ≤1 域；新文件头 `# date: YYYY-MM-DD` + `# dev: czy` + docstring（仅一次）；增改函数上方写 `# date`/`# dev`/`# changelog` 注释；类/公开函数必须有 Google 风格 docstring。
- **数据契约**：只用 `protocol/` 类型（`cyber.Asset` / `memory.MemoryPacket`），禁自造并行结构。
- **质量门禁（12_TECH_STACK §6）**：`ruff format && ruff check --fix && mypy && pytest` 全绿方可提交。本机：pytest+mypy 可用；ruff 需先 `pip install ruff`。
- **兼容性**：`data/api/__init__.py` 既有 `DatasetAPI`/`ModelSchemaAPI` 签名不变（新增是增量，非破坏）；现有 memory 测试必须保持通过（默认行为不变）。
- **mypy 严格模式**：惰性客户端（`_driver`/`_client`）标注为 `Any`（未安装三方包时无法类型化）；实例字段始终在 `__init__` 初始化。
- **commit 规范（00 §13）**：`<type>(<scope>): <subject>`，commit 只含相关文件。

---

# R1 — data 域（第 1 个域）

## Task 1: data 包结构初始化

**Files:**
- Create: `data/__init__.py`
- Create: `data/models/__init__.py`
- Create: `data/datasets/__init__.py`

**Interfaces:**
- Produces: 使 `data.models` / `data.datasets` 成为可 import 的包（供后续任务使用）。

- [ ] **Step 1: 创建 3 个 `__init__.py`**

`data/__init__.py`:
```python
# date: 2026-08-06
# dev: czy
"""数据层 —— 数据集与数据模型/存储后端。"""
```

`data/models/__init__.py`:
```python
# date: 2026-08-06
# dev: czy
"""数据模型与存储后端实现（图存储 / 向量存储 / 注册表）。"""
```

`data/datasets/__init__.py`:
```python
# date: 2026-08-06
# dev: czy
"""数据集 —— ATT&CK 知识库等结构化数据。"""
```

- [ ] **Step 2: 验证 import 不报错**

Run: `python -c "import data; import data.models; import data.datasets; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add data/__init__.py data/models/__init__.py data/datasets/__init__.py
git commit -m "feat(data): init data/models and data/datasets packages"
```

## Task 2: ATT&CK 数据集（~36 条 + 关系边）

**Files:**
- Create: `data/datasets/attck/__init__.py`
- Create: `data/datasets/attck/knowledge.py`
- Test: `tests/data/test_attck_knowledge.py`

**Interfaces:**
- Produces: `ATTACK_TECHNIQUES: dict[str, dict]`、`ATTACK_RELATIONS: list[tuple[str, str, str]]`、`load_attck_dataset() -> list[MemoryPacket]`（Task 5/8 消费）。

- [ ] **Step 1: 创建 attck 子包 `__init__.py`**

`data/datasets/attck/__init__.py`:
```python
# date: 2026-08-06
# dev: czy
"""ATT&CK 知识数据集。"""
```

- [ ] **Step 2: 写失败测试**

`tests/data/test_attck_knowledge.py`:
```python
from data.datasets.attck.knowledge import ATTACK_RELATIONS, ATTACK_TECHNIQUES, load_attck_dataset


def test_dataset_has_original_8_seed():
    """扩充数据集必须保留原 8 条种子（兼容现有语义测试）。"""
    for tid in ["T1595", "T1592", "T1210", "T1059", "T1078", "T1046", "T1021", "T1053"]:
        assert tid in ATTACK_TECHNIQUES
        assert ATTACK_TECHNIQUES[tid]["tactic"] is not None


def test_dataset_size_between_30_and_40():
    """数据集规模约 30-40 条。"""
    assert 30 <= len(ATTACK_TECHNIQUES) <= 40


def test_relations_reference_known_techniques():
    """关系边的两端必须引用已知技战术或合法 tactic 节点。"""
    known = set(ATTACK_TECHNIQUES)
    for src, rel, dst in ATTACK_RELATIONS:
        assert rel in ("contains", "precedes", "uses", "targets")
        assert src in known or dst in known


def test_load_attck_dataset_returns_memory_packets():
    """load_attck_dataset 返回 MemoryPacket 列表，语义字段完整。"""
    packets = load_attck_dataset()
    assert len(packets) == len(ATTACK_TECHNIQUES)
    p = next(x for x in packets if x.task_id == "T1210")
    assert p.semantic["technique_id"] == "T1210"
    assert p.semantic["tactic"] == "lateral-movement"
```

- [ ] **Step 3: 运行测试确认失败**

Run: `python -m pytest tests/data/test_attck_knowledge.py -v`
Expected: FAIL（ModuleNotFoundError）

- [ ] **Step 4: 写数据集实现**

`data/datasets/attck/knowledge.py`:
```python
# date: 2026-08-06
# dev: czy
"""ATT&CK 知识数据集 —— 技战术 + 关系边。

覆盖赛事 3 场景（侦察 / 横向移动 / 检测响应）所需技战术集合，
保留原始 8 条种子（T1595/T1592/T1210/T1059/T1078/T1046/T1021/T1053），
提供 :func:`load_attck_dataset` 供数据层与记忆子系统共享单一知识源。
"""

from __future__ import annotations

from protocol.memory import MemoryPacket

# technique_id -> {name, tactic, platform, description}
ATTACK_TECHNIQUES: dict[str, dict] = {
    # ---- reconnaissance（侦察）----
    "T1595": {"name": "Active Scanning", "tactic": "reconnaissance", "platform": "network", "description": "主动扫描目标收集可利用信息"},
    "T1592": {"name": "Gather Victim Host Info", "tactic": "reconnaissance", "platform": "network", "description": "收集目标主机配置/操作系统/软件信息"},
    "T1589": {"name": "Gather Victim Identity Info", "tactic": "reconnaissance", "platform": "identity", "description": "收集受害者身份信息（账号/组织）"},
    "T1590": {"name": "Gather Victim Network Info", "tactic": "reconnaissance", "platform": "network", "description": "收集目标网络拓扑/网段信息"},
    "T1598": {"name": "Phishing for Information", "tactic": "reconnaissance", "platform": "social", "description": "通过钓鱼收集目标情报"},
    "T1597": {"name": "Search Open Technical Databases", "tactic": "reconnaissance", "platform": "osint", "description": "在公开技术库中检索目标信息"},
    # ---- initial-access（初始访问）----
    "T1133": {"name": "External Remote Services", "tactic": "initial-access", "platform": "network", "description": "通过外部远程服务（VPN/RDP）进入内网"},
    "T1190": {"name": "Exploit Public-Facing Application", "tactic": "initial-access", "platform": "application", "description": "利用暴露在公网的应用程序漏洞获取访问"},
    "T1566": {"name": "Phishing", "tactic": "initial-access", "platform": "social", "description": "通过钓鱼邮件/链接诱导用户执行"},
    # ---- execution（执行）----
    "T1059": {"name": "Command and Scripting Interpreter", "tactic": "execution", "platform": "os", "description": "通过命令脚本解释器执行恶意代码"},
    "T1053": {"name": "Scheduled Task/Job", "tactic": "execution", "platform": "os", "description": "通过计划任务定时执行"},
    "T1204": {"name": "User Execution", "tactic": "execution", "platform": "user", "description": "诱导用户执行恶意文件"},
    "T1047": {"name": "Windows Management Instrumentation", "tactic": "execution", "platform": "windows", "description": "利用 WMI 执行远程命令"},
    "T1106": {"name": "Native API", "tactic": "execution", "platform": "os", "description": "直接调用系统原生 API 执行"},
    # ---- persistence（持久化）----
    "T1136": {"name": "Create Account", "tactic": "persistence", "platform": "os", "description": "创建本地/域账户维持访问"},
    "T1547": {"name": "Boot or Logon Autostart", "tactic": "persistence", "platform": "windows", "description": "利用开机/登录自启维持持久化"},
    "T1505": {"name": "Server Software Component", "tactic": "persistence", "platform": "server", "description": "在服务端软件注入后门组件"},
    # ---- defense-evasion（防御绕过）----
    "T1078": {"name": "Valid Accounts", "tactic": "defense-evasion", "platform": "identity", "description": "利用合法账户凭证规避检测"},
    "T1070": {"name": "Indicator Removal on Host", "tactic": "defense-evasion", "platform": "host", "description": "清除主机上的攻击痕迹与日志"},
    "T1036": {"name": "Masquerading", "tactic": "defense-evasion", "platform": "host", "description": "伪装成合法进程/文件名规避检测"},
    "T1027": {"name": "Obfuscated Files or Information", "tactic": "defense-evasion", "platform": "host", "description": "混淆恶意载荷与通信内容"},
    "T1562": {"name": "Impair Defenses", "tactic": "defense-evasion", "platform": "host", "description": "禁用或降低安全防护能力"},
    "T1140": {"name": "Deobfuscate/Decode Files or Information", "tactic": "defense-evasion", "platform": "host", "description": "解混淆/解码恶意文件还原载荷"},
    # ---- discovery（发现）----
    "T1046": {"name": "Network Service Discovery", "tactic": "discovery", "platform": "network", "description": "发现网络中可用的服务"},
    "T1016": {"name": "System Network Configuration Discovery", "tactic": "discovery", "platform": "host", "description": "获取本机网络配置信息"},
    "T1082": {"name": "System Information Discovery", "tactic": "discovery", "platform": "host", "description": "收集主机系统信息"},
    "T1087": {"name": "Account Discovery", "tactic": "discovery", "platform": "identity", "description": "枚举系统账户信息"},
    # ---- lateral-movement（横向移动）----
    "T1210": {"name": "Exploitation of Remote Services", "tactic": "lateral-movement", "platform": "network", "description": "利用远程服务漏洞进行横向移动"},
    "T1021": {"name": "Remote Services", "tactic": "lateral-movement", "platform": "network", "description": "通过远程服务（SSH/SMB/RDP）横向移动"},
    "T1550": {"name": "Use Alternate Authentication Material", "tactic": "lateral-movement", "platform": "identity", "description": "使用票据/哈希等替代认证材料横向移动"},
    "T1080": {"name": "Taint Shared Content", "tactic": "lateral-movement", "platform": "network", "description": "污染共享资源诱导横向执行"},
    # ---- collection（收集 / 蓝队关联）----
    "T1005": {"name": "Data from Local System", "tactic": "collection", "platform": "host", "description": "从本地系统收集敏感数据（检测重点）"},
}

# 关系边：(src, rel, dst)；rel ∈ contains/precedes/uses/targets
ATTACK_RELATIONS: list[tuple[str, str, str]] = [
    # tactic 包含
    ("reconnaissance", "contains", "T1595"),
    ("reconnaissance", "contains", "T1592"),
    ("reconnaissance", "contains", "T1589"),
    ("reconnaissance", "contains", "T1590"),
    ("reconnaissance", "contains", "T1598"),
    ("reconnaissance", "contains", "T1597"),
    ("initial-access", "contains", "T1133"),
    ("initial-access", "contains", "T1190"),
    ("initial-access", "contains", "T1566"),
    ("execution", "contains", "T1059"),
    ("execution", "contains", "T1053"),
    ("execution", "contains", "T1204"),
    ("execution", "contains", "T1047"),
    ("execution", "contains", "T1106"),
    ("persistence", "contains", "T1136"),
    ("persistence", "contains", "T1547"),
    ("persistence", "contains", "T1505"),
    ("defense-evasion", "contains", "T1078"),
    ("defense-evasion", "contains", "T1070"),
    ("defense-evasion", "contains", "T1036"),
    ("defense-evasion", "contains", "T1027"),
    ("defense-evasion", "contains", "T1562"),
    ("defense-evasion", "contains", "T1140"),
    ("discovery", "contains", "T1046"),
    ("discovery", "contains", "T1016"),
    ("discovery", "contains", "T1082"),
    ("discovery", "contains", "T1087"),
    ("lateral-movement", "contains", "T1210"),
    ("lateral-movement", "contains", "T1021"),
    ("lateral-movement", "contains", "T1550"),
    ("lateral-movement", "contains", "T1080"),
    ("collection", "contains", "T1005"),
    # 攻击链前置/使用关系
    ("T1595", "precedes", "T1592"),
    ("T1592", "precedes", "T1046"),
    ("T1046", "precedes", "T1190"),
    ("T1190", "precedes", "T1210"),
    ("T1210", "uses", "T1059"),
    ("T1566", "precedes", "T1204"),
    ("T1078", "uses", "T1021"),
    ("T1070", "targets", "T1005"),
]


def load_attck_dataset() -> list[MemoryPacket]:
    """将 ATT&CK 数据集转为 MemoryPacket 列表（供图存储 seed 与记忆子系统预载）。

    Returns:
        每条含 semantic 字段 technique_id/name/tactic/platform/description 的列表。
    """
    packets: list[MemoryPacket] = []
    for tid, info in ATTACK_TECHNIQUES.items():
        packets.append(
            MemoryPacket(
                task_id=tid,
                summary=f"{tid} {info['name']}",
                semantic={
                    "technique_id": tid,
                    "name": info["name"],
                    "tactic": info["tactic"],
                    "platform": info["platform"],
                    "description": info["description"],
                },
                kind="decision",
            )
        )
    return packets
```

- [ ] **Step 5: 运行测试确认通过**

Run: `python -m pytest tests/data/test_attck_knowledge.py -v`
Expected: PASS（4 passed）

- [ ] **Step 6: Commit**

```bash
git add data/datasets/attck/ tests/data/
git commit -m "feat(data): add ATT&CK knowledge dataset (~36 techniques + relations)"
```

## Task 3: InMemoryVectorStore + 余弦检索

**Files:**
- Create: `data/models/vector_store.py`
- Test: `tests/data/test_vector_store.py`

**Interfaces:**
- Produces: `InMemoryVectorStore`（`add/search/delete/count/all`，语义对齐 Task 7 的 `VectorStoreAPI`）。
- Consumes: 无（仅标准库）。

- [ ] **Step 1: 写失败测试**

`tests/data/test_vector_store.py`:
```python
from data.models.vector_store import InMemoryVectorStore


def test_add_and_search_ranked():
    vs = InMemoryVectorStore()
    vs.add("v1", [1.0, 0.0], {"task_id": "t1"})
    vs.add("v2", [0.0, 1.0], {"task_id": "t2"})
    hits = vs.search([1.0, 0.0], top_k=2)
    assert [h[0] for h in hits] == ["v1", "v2"]
    assert hits[0][2] > hits[1][2]
    assert hits[0][1] == {"task_id": "t1"}


def test_search_respects_top_k_and_empty_query():
    vs = InMemoryVectorStore()
    vs.add("v1", [1.0, 0.0])
    vs.add("v2", [0.9, 0.1])
    assert len(vs.search([1.0, 0.0], top_k=1)) == 1
    assert vs.search([]) == []


def test_delete_and_count_and_all():
    vs = InMemoryVectorStore()
    vs.add("v1", [1.0, 0.0], {"task_id": "t1"})
    vs.add("v2", [0.0, 1.0], {"task_id": "t2"})
    assert vs.count() == 2
    vs.delete("v1")
    assert vs.count() == 1
    assert [x[0] for x in vs.all()] == ["v2"]
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/data/test_vector_store.py -v`
Expected: FAIL（ImportError）

- [ ] **Step 3: 写实现**

`data/models/vector_store.py`:
```python
# date: 2026-08-06
# dev: czy
"""向量存储实现 —— InMemory + Qdrant 双实现适配层。

提供 :class:`InMemoryVectorStore`（默认，纯内存余弦检索）与
:class:`QdrantVectorStore`（真实 Qdrant 客户端，惰性加载）。
两实现均满足 ``data.api.VectorStoreAPI`` 语义：add/search/delete/count/all。
"""

from __future__ import annotations

from dataclasses import dataclass, field


def _cosine(a: list[float], b: list[float]) -> float:
    """计算两个向量的余弦相似度。

    Args:
        a: 向量 A。
        b: 向量 B。

    Returns:
        值域 [-1, 1]；任一向量范数为 0 时返回 0.0。
    """
    n = min(len(a), len(b))
    if n == 0:
        return 0.0
    dot = float(sum(a[i] * b[i] for i in range(n)))
    norm_a = float(sum(x * x for x in a)) ** 0.5
    norm_b = float(sum(x * x for x in b)) ** 0.5
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return float(dot / (norm_a * norm_b))


@dataclass
class _VectorItem:
    """内存向量条目。

    Attributes:
        vector_id: 向量唯一标识。
        vector: 向量本体。
        payload: 附加元数据（如序列化后的 MemoryPacket 字段）。
    """

    vector_id: str
    vector: list[float]
    payload: dict = field(default_factory=dict)


class InMemoryVectorStore:
    """内存向量存储 —— 默认零依赖实现。

    Attributes:
        _items: 已索引向量列表（保持写入顺序，同分检索稳定）。
    """

    def __init__(self) -> None:
        """初始化空的内存向量存储。"""
        self._items: list[_VectorItem] = []

    def add(self, vector_id: str, vector: list[float], payload: dict | None = None) -> None:
        """写入/覆盖一条向量（幂等，按 vector_id）。

        Args:
            vector_id: 向量唯一标识。
            vector: 向量本体；为空时跳过。
            payload: 附加元数据，默认空 dict。
        """
        if not vector:
            return
        # 先移除同 id 旧条目，保证幂等
        self._items = [it for it in self._items if it.vector_id != vector_id]
        self._items.append(_VectorItem(vector_id, vector, payload or {}))

    def search(self, query: list[float], top_k: int = 5) -> list[tuple[str, dict, float]]:
        """按查询向量余弦相似度检索 Top-K。

        Args:
            query: 查询向量；为空时返回空列表。
            top_k: 返回条数上限。

        Returns:
            ``[(vector_id, payload, score)]`` 按相似度降序，同分保写入序。
        """
        if not query or not self._items or top_k <= 0:
            return []
        scored = [(it.vector_id, it.payload, _cosine(query, it.vector)) for it in self._items]
        scored.sort(key=lambda x: x[2], reverse=True)
        return scored[:top_k]

    def delete(self, vector_id: str) -> None:
        """删除指定向量（不存在则静默）。"""
        self._items = [it for it in self._items if it.vector_id != vector_id]

    def count(self) -> int:
        """返回已索引向量条数。"""
        return len(self._items)

    def all(self) -> list[tuple[str, dict]]:
        """返回全部 ``(vector_id, payload)``（按写入顺序）。"""
        return [(it.vector_id, it.payload) for it in self._items]
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python -m pytest tests/data/test_vector_store.py -v`
Expected: PASS（3 passed）

- [ ] **Step 5: Commit**

```bash
git add data/models/vector_store.py tests/data/test_vector_store.py
git commit -m "feat(data): add InMemoryVectorStore with cosine search"
```

## Task 4: QdrantVectorStore（惰性加载）

**Files:**
- Modify: `data/models/vector_store.py`（追加 `QdrantVectorStore`）
- Test: `tests/data/test_vector_store.py`（追加 1 个测试）

**Interfaces:**
- Consumes: `InMemoryVectorStore`（Task 3）。
- Produces: `QdrantVectorStore`（Task 6 的 registry 与 Task 7 工厂消费）。

- [ ] **Step 1: 追加失败测试**

在 `tests/data/test_vector_store.py` 末尾追加：
```python
import pytest

from data.models.vector_store import QdrantVectorStore


def test_qdrant_store_missing_client_raises():
    """未安装 qdrant-client 时应抛 RuntimeError（惰性加载）。"""
    vs = QdrantVectorStore(url="http://localhost:6333")
    with pytest.raises(RuntimeError, match="qdrant-client"):
        vs.search([1.0], top_k=1)
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/data/test_vector_store.py::test_qdrant_store_missing_client_raises -v`
Expected: FAIL（ImportError）

- [ ] **Step 3: 在 `vector_store.py` 末尾追加 `QdrantVectorStore`**

```python
class QdrantVectorStore:
    """Qdrant 向量存储 —— 真实客户端适配器（惰性加载）。

    首次方法调用时 ``import qdrant_client``；未安装或连接失败时抛错，
    不做静默降级（由装配方决定是否回退内存实现）。
    """

    def __init__(
        self,
        url: str = "http://localhost:6333",
        api_key: str = "",
        collection: str = "memory_vectors",
        timeout: float = 10.0,
    ) -> None:
        """初始化 Qdrant 客户端参数（不建立连接）。

        Args:
            url: Qdrant 服务地址。
            api_key: 可选 API Key。
            collection: 集合名。
            timeout: 连接超时（秒）。
        """
        self._url = url
        self._api_key = api_key
        self._collection = collection
        self._timeout = timeout
        self._client: Any | None = None  # 惰性：构造不导入三方包

    def _get_client(self) -> Any:
        """惰性获取 Qdrant 客户端（首次调用导入驱动并连接）。

        Raises:
            RuntimeError: 未安装 qdrant-client 时。
            ConnectionError: 连接失败时。
        """
        if self._client is not None:
            return self._client
        try:
            from qdrant_client import QdrantClient  # noqa: PLC0415
        except ImportError as exc:  # pragma: no cover - 依赖缺失路径
            raise RuntimeError("qdrant-client 未安装，请 pip install aegisos[storage]") from exc
        try:
            client = QdrantClient(url=self._url, api_key=self._api_key, timeout=self._timeout)
        except Exception as exc:  # pragma: no cover - 网络路径
            raise ConnectionError(f"无法连接 Qdrant: {exc}") from exc
        self._client = client
        return client

    def add(self, vector_id: str, vector: list[float], payload: dict | None = None) -> None:
        """upsert 一条向量到 Qdrant（首次调用创建集合）。

        Args:
            vector_id: 向量唯一标识（Qdrant point id）。
            vector: 向量本体。
            payload: 附加元数据。
        """
        if not vector:
            return
        client = self._get_client()
        try:
            from qdrant_client.models import Distance, PointStruct, VectorParams  # noqa: PLC0415
            from qdrant_client.http.exceptions import UnexpectedResponse  # noqa: PLC0415

            try:
                client.get_collection(self._collection)
            except (UnexpectedResponse, ValueError):
                client.create_collection(
                    collection_name=self._collection,
                    vectors_config=VectorParams(size=len(vector), distance=Distance.COSINE),
                )
            client.upsert(
                collection_name=self._collection,
                points=[PointStruct(id=vector_id, vector=vector, payload=payload or {})],
            )
        except Exception as exc:  # pragma: no cover - 网络路径
            raise ConnectionError(f"Qdrant upsert 失败: {exc}") from exc

    def search(self, query: list[float], top_k: int = 5) -> list[tuple[str, dict, float]]:
        """按查询向量检索 Top-K（返回 id/payload/score）。

        Args:
            query: 查询向量；为空时返回空列表。
            top_k: 返回条数上限。
        """
        if not query:
            return []
        client = self._get_client()
        hits = client.search(
            collection_name=self._collection,
            query_vector=query,
            limit=top_k,
            with_payload=True,
            with_vectors=False,
        )
        return [(str(h.id), dict(h.payload or {}), float(h.score)) for h in hits]

    def delete(self, vector_id: str) -> None:
        """删除指定向量（不存在则静默）。"""
        client = self._get_client()
        client.delete(collection_name=self._collection, points_selector=[vector_id])

    def count(self) -> int:
        """返回集合内向量条数。"""
        client = self._get_client()
        info = client.count(collection_name=self._collection, exact=True)
        return int(info.count or 0)

    def all(self) -> list[tuple[str, dict]]:
        """滚动返回全部 ``(id, payload)``（演示规模足够，取前 1000 条）。"""
        client = self._get_client()
        points, _ = client.scroll(
            collection_name=self._collection, limit=1000, with_payload=True, with_vectors=False
        )
        return [(str(p.id), dict(p.payload or {})) for p in points]
```

同时在该文件 import 区追加 `from typing import Any`。

- [ ] **Step 4: 运行测试确认通过**

Run: `python -m pytest tests/data/test_vector_store.py -v`
Expected: PASS（3 旧 + 1 新）

- [ ] **Step 5: Commit**

```bash
git add data/models/vector_store.py tests/data/test_vector_store.py
git commit -m "feat(data): add QdrantVectorStore with lazy client loading"
```

## Task 5: InMemoryGraphStore（拓扑 + ATT&CK）

**Files:**
- Create: `data/models/graph_store.py`
- Test: `tests/data/test_graph_store.py`

**Interfaces:**
- Consumes: `data.datasets.attck.knowledge.load_attck_dataset`（Task 2）、`protocol.cyber.Asset`。
- Produces: `InMemoryGraphStore`（Task 7 的 `GraphStoreAPI` 语义）。

- [ ] **Step 1: 写失败测试**

`tests/data/test_graph_store.py`:
```python
from protocol.cyber import Asset
from data.models.graph_store import InMemoryGraphStore


def test_seed_attck_default_loaded():
    """默认构造应预载 ATT&CK 数据集。"""
    gs = InMemoryGraphStore()
    assert 30 <= len(gs.all_techniques()) <= 40
    assert gs.get_technique("T1210") is not None


def test_upsert_get_search_techniques():
    gs = InMemoryGraphStore(seed_attck=False)
    from protocol.memory import MemoryPacket

    gs.upsert_technique(
        "T0000",
        MemoryPacket(task_id="T0000", semantic={"technique_id": "T0000", "name": "Test Tech", "tactic": "test"}),
    )
    assert gs.get_technique("T0000").semantic["name"] == "Test Tech"
    assert len(gs.search_techniques("Test")) == 1


def test_relations_and_related():
    gs = InMemoryGraphStore(seed_attck=True)
    gs.add_relation("T1595", "precedes", "T1592")
    related = gs.related_techniques("T1595")
    assert any(r.task_id == "T1592" for r in related)
    only = gs.related_techniques("T1595", relation="precedes")
    assert all(r.task_id == "T1592" for r in only)


def test_topology_save_get_list():
    gs = InMemoryGraphStore(seed_attck=False)
    assets = [Asset(asset_id="host-a", host="10.0.0.1"), Asset(asset_id="host-b", host="10.0.0.2")]
    gs.save_topology("range-1", assets, [("host-a", "reaches", "host-b")])
    got_assets, got_links = gs.get_topology("range-1")
    assert [a.asset_id for a in got_assets] == ["host-a", "host-b"]
    assert got_links == [("host-a", "reaches", "host-b")]
    assert gs.list_topologies() == ["range-1"]
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/data/test_graph_store.py -v`
Expected: FAIL（ImportError）

- [ ] **Step 3: 写实现**

`data/models/graph_store.py`:
```python
# date: 2026-08-06
# dev: czy
"""图存储实现 —— InMemory + Neo4j 双实现适配层。

提供 :class:`InMemoryGraphStore`（默认，dict 参考实现）与
:class:`Neo4jGraphStore`（真实 Neo4j 客户端，惰性加载）。
两能力：网络拓扑（Asset 节点 + 带标签关系）与 ATT&CK 知识（Technique 节点 + 关系）。
"""

from __future__ import annotations

from data.datasets.attck.knowledge import load_attck_dataset
from protocol.cyber import Asset
from protocol.memory import MemoryPacket

# 合法关系标签集合（防御脏数据）
_ALLOWED_RELS = {"contains", "precedes", "uses", "targets"}


class InMemoryGraphStore:
    """内存图存储 —— 默认零依赖实现。

    Attributes:
        _topologies: scope -> (assets, links)。
        _attck: technique_id -> MemoryPacket。
        _attck_edges: (src, rel, dst) 列表。
    """

    def __init__(self, seed_attck: bool = True) -> None:
        """初始化图存储，可选预载 ATT&CK 数据集。

        Args:
            seed_attck: 是否在构造时预载 ATT&CK 数据集，默认 ``True``。
        """
        self._topologies: dict[str, tuple[list[Asset], list[tuple[str, str, str]]]] = {}
        self._attck: dict[str, MemoryPacket] = {}
        self._attck_edges: list[tuple[str, str, str]] = []
        if seed_attck:
            self.seed_attck(load_attck_dataset())

    # ---- ATT&CK 知识 ----

    def seed_attck(self, entries: list[MemoryPacket]) -> int:
        """批量写入 ATT&CK 技战术条目。

        Args:
            entries: MemoryPacket 列表（含 semantic.technique_id）。

        Returns:
            写入条数。
        """
        for p in entries:
            tid = str(p.semantic.get("technique_id") or p.task_id)
            self._attck[tid] = p
        return len(entries)

    def upsert_technique(self, technique_id: str, packet: MemoryPacket) -> None:
        """按 ID 单条写入/覆盖一条技战术。

        Args:
            technique_id: 技战术唯一标识。
            packet: 知识记忆包。
        """
        self._attck[technique_id] = packet

    def get_technique(self, technique_id: str) -> MemoryPacket | None:
        """按 ID 查询技战术。

        Args:
            technique_id: 目标技战术 ID。

        Returns:
            匹配的知识包；未找到返回 None。
        """
        return self._attck.get(technique_id)

    def search_techniques(self, keyword: str) -> list[MemoryPacket]:
        """关键词检索技战术（ID/名称/战术阶段/描述，大小写不敏感）。

        Args:
            keyword: 检索关键词。

        Returns:
            命中的知识包列表。
        """
        kw = keyword.lower()
        hits: list[MemoryPacket] = []
        for p in self._attck.values():
            text = " ".join(str(v) for v in p.semantic.values())
            if kw in text.lower() or kw in (p.summary or "").lower():
                hits.append(p)
        return hits

    def all_techniques(self) -> list[MemoryPacket]:
        """返回全部技战术（按写入顺序）。"""
        return list(self._attck.values())

    def add_relation(self, src: str, rel: str, dst: str) -> None:
        """添加一条关系边（src/rel/dst）。

        Args:
            src: 源节点（tactic 或 technique_id）。
            rel: 关系标签（contains/precedes/uses/targets）。
            dst: 目标节点（tactic 或 technique_id）。

        Raises:
            ValueError: rel 不在合法标签集合时。
        """
        if rel not in _ALLOWED_RELS:
            raise ValueError(f"非法关系标签: {rel}")
        self._attck_edges.append((src, rel, dst))

    def related_techniques(self, technique_id: str, relation: str | None = None) -> list[MemoryPacket]:
        """返回与指定技战术关联的其他技战术（双向可达）。

        Args:
            technique_id: 源技战术 ID。
            relation: 可选关系标签过滤。

        Returns:
            关联的技战术 MemoryPacket 列表。
        """
        targets: list[str] = []
        for src, rel, dst in self._attck_edges:
            if relation is not None and rel != relation:
                continue
            if src == technique_id and dst in self._attck:
                targets.append(dst)
            elif dst == technique_id and src in self._attck:
                targets.append(src)
        seen: set[str] = set()
        result: list[MemoryPacket] = []
        for tid in targets:
            if tid not in seen:
                seen.add(tid)
                p = self._attck.get(tid)
                if p is not None:
                    result.append(p)
        return result

    # ---- 网络拓扑 ----

    def save_topology(self, scope: str, assets: list[Asset], links: list[tuple[str, str, str]]) -> None:
        """保存一个拓扑（按 scope 归组，覆盖写）。

        Args:
            scope: 拓扑作用域标识（如 range_id）。
            assets: 资产节点列表。
            links: (src, rel, dst) 关系列表。
        """
        self._topologies[scope] = (assets, links)

    def get_topology(self, scope: str) -> tuple[list[Asset], list[tuple[str, str, str]]]:
        """读取指定作用域的拓扑。

        Args:
            scope: 拓扑作用域标识。

        Returns:
            ``(assets, links)``；不存在时返回 ``([], [])``。
        """
        return self._topologies.get(scope, ([], []))

    def list_topologies(self) -> list[str]:
        """返回全部已保存的拓扑作用域。"""
        return list(self._topologies.keys())
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python -m pytest tests/data/test_graph_store.py -v`
Expected: PASS（4 passed）

## Task 6: Neo4jGraphStore（惰性加载）+ registry

**Files:**
- Modify: `data/models/graph_store.py`（追加 `Neo4jGraphStore`）
- Create: `data/models/registry.py`
- Test: `tests/data/test_graph_store.py`（追加 1 个测试）、`tests/data/test_registry.py`

**Interfaces:**
- Consumes: `InMemoryGraphStore`（Task 5）、`InMemoryVectorStore`/`QdrantVectorStore`（Task 3/4）。
- Produces: `Neo4jGraphStore`；`create_graph_store(mode, **kwargs)` / `create_vector_store(mode, **kwargs)`（Task 7 经 data.api 再导出）。

- [ ] **Step 1: 追加失败测试（Neo4j 惰性 + registry）**

在 `tests/data/test_graph_store.py` 末尾追加：
```python
import pytest

from data.models.graph_store import Neo4jGraphStore


def test_neo4j_store_missing_driver_raises():
    """未安装 neo4j 驱动时应抛 RuntimeError（惰性加载）。"""
    gs = Neo4jGraphStore(uri="bolt://localhost:7687")
    with pytest.raises(RuntimeError, match="neo4j"):
        gs.get_technique("T1210")
```

`tests/data/test_registry.py`:
```python
import pytest

from data.models.registry import create_graph_store, create_vector_store
from data.models.vector_store import InMemoryVectorStore


def test_create_vector_store_in_memory():
    vs = create_vector_store("in_memory")
    assert isinstance(vs, InMemoryVectorStore)


def test_create_graph_store_in_memory():
    gs = create_graph_store("in_memory")
    assert 30 <= len(gs.all_techniques()) <= 40  # 默认 seed


def test_create_unknown_mode_raises():
    with pytest.raises(ValueError):
        create_vector_store("unknown")
    with pytest.raises(ValueError):
        create_graph_store("unknown")
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/data/test_graph_store.py::test_neo4j_store_missing_driver_raises tests/data/test_registry.py -v`
Expected: FAIL（ImportError）

- [ ] **Step 3: 在 `graph_store.py` 末尾追加 `Neo4jGraphStore`，并在 import 区追加 `from typing import Any`**

```python
class Neo4jGraphStore:
    """Neo4j 图存储 —— 真实客户端适配器（惰性加载）。

    首次方法调用时 ``import neo4j`` 并连接；未安装或连接失败时抛错，
    不做静默降级。拓扑节点 label ``Asset``、技战术节点 label ``Technique``，
    关系 label 即关系标签；``scope`` 作为节点属性归组。
    """

    def __init__(
        self,
        uri: str = "bolt://localhost:7687",
        user: str = "neo4j",
        password: str = "",
        database: str | None = None,
    ) -> None:
        """初始化 Neo4j 连接参数（不建立连接）。

        Args:
            uri: bolt 连接地址。
            user: 用户名。
            password: 密码。
            database: 数据库名，默认取 neo4j 默认库。
        """
        self._uri = uri
        self._user = user
        self._password = password
        self._database = database
        self._driver: Any | None = None  # 惰性：构造不导入三方包

    def _get_driver(self) -> Any:
        """惰性获取 neo4j 驱动。

        Raises:
            RuntimeError: 未安装 neo4j 包时。
            ConnectionError: 连接失败时。
        """
        if self._driver is not None:
            return self._driver
        try:
            from neo4j import GraphDatabase  # noqa: PLC0415
        except ImportError as exc:  # pragma: no cover - 依赖缺失路径
            raise RuntimeError("neo4j 驱动未安装，请 pip install aegisos[storage]") from exc
        try:
            driver = GraphDatabase.driver(self._uri, auth=(self._user, self._password))
            driver.verify_connectivity()
        except Exception as exc:  # pragma: no cover - 网络路径
            raise ConnectionError(f"无法连接 Neo4j: {exc}") from exc
        self._driver = driver
        return driver

    # ---- ATT&CK 知识 ----

    def seed_attck(self, entries: list[MemoryPacket]) -> int:
        """批量写入技战术（MERGE 幂等）与 tactic 关系。

        Args:
            entries: MemoryPacket 列表。

        Returns:
            写入条数。
        """
        driver = self._get_driver()
        with driver.session(database=self._database) as session:
            for p in entries:
                tid = str(p.semantic.get("technique_id") or p.task_id)
                session.run(
                    "MERGE (t:Technique {technique_id: $tid}) "
                    "SET t.name=$name, t.tactic=$tactic, t.platform=$platform, t.description=$desc",
                    tid=tid,
                    name=p.semantic.get("name", ""),
                    tactic=p.semantic.get("tactic", ""),
                    platform=p.semantic.get("platform", ""),
                    desc=p.semantic.get("description", ""),
                )
                tac = p.semantic.get("tactic", "")
                if tac:
                    session.run(
                        "MERGE (a:Tactic {name:$tac}) MERGE (a)-[:contains]->(t:Technique {technique_id:$tid})",
                        tac=tac,
                        tid=tid,
                    )
        return len(entries)

    def upsert_technique(self, technique_id: str, packet: MemoryPacket) -> None:
        """按 ID 幂等写入一条技战术（MERGE）。"""
        driver = self._get_driver()
        with driver.session(database=self._database) as session:
            session.run(
                "MERGE (t:Technique {technique_id: $tid}) "
                "SET t.name=$name, t.tactic=$tactic, t.platform=$platform, t.description=$desc",
                tid=technique_id,
                name=packet.semantic.get("name", ""),
                tactic=packet.semantic.get("tactic", ""),
                platform=packet.semantic.get("platform", ""),
                desc=packet.semantic.get("description", ""),
            )

    def get_technique(self, technique_id: str) -> MemoryPacket | None:
        """按 ID 查询技战术，还原为 MemoryPacket。"""
        driver = self._get_driver()
        with driver.session(database=self._database) as session:
            rec = session.run(
                "MATCH (t:Technique {technique_id: $tid}) RETURN t", tid=technique_id
            ).single()
        if rec is None:
            return None
        props = rec["t"]
        return MemoryPacket(
            task_id=technique_id,
            summary=f"{technique_id} {props.get('name', '')}",
            semantic={
                "technique_id": technique_id,
                "name": props.get("name", ""),
                "tactic": props.get("tactic", ""),
                "platform": props.get("platform", ""),
                "description": props.get("description", ""),
            },
            kind="decision",
        )

    def search_techniques(self, keyword: str) -> list[MemoryPacket]:
        """关键词检索技战术（名称/战术/ID 模糊匹配）。"""
        driver = self._get_driver()
        with driver.session(database=self._database) as session:
            recs = session.run(
                "MATCH (t:Technique) WHERE toLower(t.technique_id) CONTAINS $kw "
                "OR toLower(t.name) CONTAINS $kw OR toLower(t.tactic) CONTAINS $kw "
                "RETURN t.technique_id AS tid ORDER BY tid",
                kw=keyword.lower(),
            ).data()
        return [self._get_technique_or_blank(r["tid"]) for r in recs]

    def all_techniques(self) -> list[MemoryPacket]:
        """返回全部技战术。"""
        driver = self._get_driver()
        with driver.session(database=self._database) as session:
            recs = session.run("MATCH (t:Technique) RETURN t.technique_id AS tid ORDER BY tid").data()
        return [self._get_technique_or_blank(r["tid"]) for r in recs]

    def add_relation(self, src: str, rel: str, dst: str) -> None:
        """添加关系边（两端节点已存在时；tactic 节点需已 seed）。

        Args:
            src: 源节点（tactic 名或 technique_id）。
            rel: 关系标签。
            dst: 目标节点。

        Raises:
            ValueError: rel 不在合法标签集合时。
        """
        if rel not in _ALLOWED_RELS:
            raise ValueError(f"非法关系标签: {rel}")
        driver = self._get_driver()
        with driver.session(database=self._database) as session:
            session.run(
                f"MATCH (a) WHERE a.technique_id=$src OR a.name=$src "
                f"MATCH (b) WHERE b.technique_id=$dst OR b.name=$dst "
                f"MERGE (a)-[:{rel}]->(b)",
                src=src,
                dst=dst,
            )

    def related_techniques(self, technique_id: str, relation: str | None = None) -> list[MemoryPacket]:
        """返回与指定技战术关联的其他技战术（双向）。"""
        rel_clause = f"-[r:{relation}]-" if relation else "-[r]-"
        driver = self._get_driver()
        with driver.session(database=self._database) as session:
            recs = session.run(
                f"MATCH (t:Technique {{technique_id: $tid}}){rel_clause}(n:Technique) "
                "RETURN n.technique_id AS tid",
                tid=technique_id,
            ).data()
        return [self._get_technique_or_blank(r["tid"]) for r in recs]

    def _get_technique_or_blank(self, technique_id: str) -> MemoryPacket:
        """按 ID 查技战术；查不到时返回空白包（避免二次查询失败）。

        Args:
            technique_id: 技战术 ID。

        Returns:
            MemoryPacket 或空白包。
        """
        p = self.get_technique(technique_id)
        return p if p is not None else MemoryPacket(task_id=technique_id, kind="decision")

    # ---- 网络拓扑 ----

    def save_topology(self, scope: str, assets: list[Asset], links: list[tuple[str, str, str]]) -> None:
        """保存拓扑：删除旧 scope 节点后写入（MERGE 幂等）。"""
        driver = self._get_driver()
        with driver.session(database=self._database) as session:
            session.run("MATCH (a:Asset {scope: $scope}) DETACH DELETE a", scope=scope)
            for asset in assets:
                session.run(
                    "MERGE (a:Asset {asset_id: $aid}) SET a.scope=$scope, a.host=$host, "
                    "a.os=$os, a.exposure=$exposure, a.services=$services",
                    aid=asset.asset_id,
                    scope=scope,
                    host=asset.host,
                    os=asset.os,
                    exposure=asset.exposure,
                    services=list(asset.services),
                )
            for src, rel, dst in links:
                session.run(
                    f"MATCH (a:Asset {{asset_id: $src}}), (b:Asset {{asset_id: $dst}}) "
                    f"MERGE (a)-[:{rel}]->(b)",
                    src=src,
                    dst=dst,
                )

    def get_topology(self, scope: str) -> tuple[list[Asset], list[tuple[str, str, str]]]:
        """读取指定作用域拓扑，还原为 (assets, links)。"""
        driver = self._get_driver()
        with driver.session(database=self._database) as session:
            nodes = session.run("MATCH (a:Asset {scope: $scope}) RETURN a", scope=scope).data()
            links = session.run(
                "MATCH (a:Asset {scope: $scope})-[r]->(b:Asset) RETURN a.asset_id AS src, "
                "type(r) AS rel, b.asset_id AS dst",
                scope=scope,
            ).data()
        assets = [
            Asset(asset_id=n["a"]["asset_id"], host=n["a"].get("host", ""), os=n["a"].get("os", ""),
                  exposure=n["a"].get("exposure", "external"), services=list(n["a"].get("services", [])))
            for n in nodes
        ]
        return assets, [(l["src"], l["rel"], l["dst"]) for l in links]

    def list_topologies(self) -> list[str]:
        """返回全部已保存的拓扑作用域。"""
        driver = self._get_driver()
        with driver.session(database=self._database) as session:
            recs = session.run("MATCH (a:Asset) RETURN DISTINCT a.scope AS scope").data()
        return [r["scope"] for r in recs]
```

`data/models/registry.py`:
```python
# date: 2026-08-06
# dev: czy
"""存储后端注册表 —— 按 mode 分发生成图/向量存储。

消费方（memory/backend）只经 ``data.api`` 调用本模块的工厂函数，
不直接 import ``data.models`` 内部实现。
"""

from __future__ import annotations

from data.models.graph_store import InMemoryGraphStore, Neo4jGraphStore
from data.models.vector_store import InMemoryVectorStore, QdrantVectorStore


def create_graph_store(mode: str = "in_memory", **kwargs):
    """按 mode 创建图存储。

    Args:
        mode: ``"in_memory"``（默认）/ ``"neo4j"``。
        **kwargs: 透传给具体实现的连接参数（uri/user/password/seed_attck 等）。

    Returns:
        图存储实例（InMemoryGraphStore 或 Neo4jGraphStore）。

    Raises:
        ValueError: mode 未知时。
    """
    if mode == "in_memory":
        return InMemoryGraphStore(**kwargs)
    if mode == "neo4j":
        return Neo4jGraphStore(**kwargs)
    raise ValueError(f"未知 graph_store mode: {mode}")


def create_vector_store(mode: str = "in_memory", **kwargs):
    """按 mode 创建向量存储。

    Args:
        mode: ``"in_memory"``（默认）/ ``"qdrant"``。
        **kwargs: 透传给具体实现的连接参数（url/api_key/collection/timeout 等）。

    Returns:
        向量存储实例（InMemoryVectorStore 或 QdrantVectorStore）。

    Raises:
        ValueError: mode 未知时。
    """
    if mode == "in_memory":
        return InMemoryVectorStore()
    if mode == "qdrant":
        return QdrantVectorStore(**kwargs)
    raise ValueError(f"未知 vector_store mode: {mode}")
```

- [ ] **Step 4: 运行 tests/data 全量确认通过**

Run: `python -m pytest tests/data/ -v`
Expected: PASS（attck 4 + vector 4 + graph 5 + registry 3 = 16 passed）

- [ ] **Step 5: Commit**

```bash
git add data/models/graph_store.py data/models/registry.py tests/data/
git commit -m "feat(data): add InMemory/Neo4j graph stores and mode registry"
```

## Task 7: data/api 接口与工厂

**Files:**
- Modify: `data/api/__init__.py`
- Test: `tests/data/test_data_api.py`

**Interfaces:**
- Consumes: `data.models.registry` 工厂、`data.datasets.attck.knowledge.load_attck_dataset`（Task 2/6）。
- Produces: `GraphStoreAPI` / `VectorStoreAPI`（Protocol）、`create_graph_store` / `create_vector_store` / `load_attck_dataset`（R2 记忆模块与 R3 装配消费）。

- [ ] **Step 1: 写失败测试**

`tests/data/test_data_api.py`:
```python
import typing

from data.api import (
    GraphStoreAPI,
    VectorStoreAPI,
    create_graph_store,
    create_vector_store,
    load_attck_dataset,
)


def test_api_exposes_protocols():
    """GraphStoreAPI / VectorStoreAPI 应为 typing.Protocol 子类。"""
    assert isinstance(GraphStoreAPI, typing.Protocol)
    assert isinstance(VectorStoreAPI, typing.Protocol)


def test_api_factories_return_compatible_stores():
    gs = create_graph_store("in_memory")
    vs = create_vector_store("in_memory")
    gs.all_techniques()
    vs.count()
    assert len(load_attck_dataset()) >= 30
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/data/test_data_api.py -v`
Expected: FAIL（ImportError: cannot import name 'GraphStoreAPI'）

- [ ] **Step 3: 改写 `data/api/__init__.py`（保留既有接口，追加新接口与工厂）**

`data/api/__init__.py` 全文（`DatasetAPI`/`ModelSchemaAPI` 原样保留）：
```python
# date: 2026-08-06
# dev: czy
"""Data domain public API.

其他模块只从 ``data.api`` 导入；禁止 import ``data.models`` / ``data.datasets`` 内部实现。
"""

from __future__ import annotations

from typing import Any, Protocol

from protocol.cyber import Asset
from protocol.memory import MemoryPacket


class DatasetAPI(Protocol):
    def load(self, name: str, version: str = "latest") -> Any: ...
    def list_datasets(self) -> list: ...
    def preprocess(self, name: str, config: dict) -> Any: ...


class ModelSchemaAPI(Protocol):
    def register_schema(self, name: str, schema: dict) -> None: ...
    def validate(self, name: str, data: dict) -> bool: ...
    def get_schema(self, name: str) -> dict: ...
    def migrate(self, name: str, from_ver: str, to_ver: str) -> Any: ...


class VectorStoreAPI(Protocol):
    """向量存储接口 —— 记忆嵌入向量的增删查（Qdrant / 内存双实现）。

    Attributes:
        无实例属性；本接口为 ``Protocol``，仅约束方法签名。
    """

    def add(self, vector_id: str, vector: list[float], payload: dict | None = None) -> None:
        """写入/覆盖一条向量（幂等）。

        Args:
            vector_id: 向量唯一标识。
            vector: 向量本体；为空时跳过。
            payload: 附加元数据（如 MemoryPacket 序列化字段）。
        """
        ...

    def search(self, query: list[float], top_k: int = 5) -> list[tuple[str, dict, float]]:
        """按查询向量检索 Top-K。

        Args:
            query: 查询向量；为空时返回空列表。
            top_k: 返回条数上限。

        Returns:
            ``[(vector_id, payload, score)]`` 按相似度降序。
        """
        ...

    def delete(self, vector_id: str) -> None:
        """删除指定向量（不存在则静默）。"""
        ...

    def count(self) -> int:
        """返回已索引向量条数。"""
        ...

    def all(self) -> list[tuple[str, dict]]:
        """返回全部 ``(vector_id, payload)``。"""
        ...


class GraphStoreAPI(Protocol):
    """图存储接口 —— 网络拓扑 + ATT&CK 知识（Neo4j / 内存双实现）。

    Attributes:
        无实例属性；本接口为 ``Protocol``，仅约束方法签名。
    """

    # ---- 网络拓扑 ----
    def save_topology(self, scope: str, assets: list[Asset], links: list[tuple[str, str, str]]) -> None:
        """保存一个拓扑（按 scope 归组，覆盖写）。

        Args:
            scope: 拓扑作用域标识。
            assets: 资产节点列表。
            links: (src, rel, dst) 关系列表。
        """
        ...

    def get_topology(self, scope: str) -> tuple[list[Asset], list[tuple[str, str, str]]]:
        """读取指定作用域拓扑。

        Returns:
            ``(assets, links)``；不存在时 ``([], [])``。
        """
        ...

    def list_topologies(self) -> list[str]:
        """返回全部已保存的拓扑作用域。"""
        ...

    # ---- ATT&CK 知识 ----
    def seed_attck(self, entries: list[MemoryPacket]) -> int:
        """批量写入 ATT&CK 技战术条目。

        Returns:
            写入条数。
        """
        ...

    def upsert_technique(self, technique_id: str, packet: MemoryPacket) -> None:
        """按 ID 单条写入/覆盖一条技战术。"""
        ...

    def get_technique(self, technique_id: str) -> MemoryPacket | None:
        """按 ID 查询技战术；未找到返回 None。"""
        ...

    def search_techniques(self, keyword: str) -> list[MemoryPacket]:
        """关键词检索技战术。"""
        ...

    def all_techniques(self) -> list[MemoryPacket]:
        """返回全部技战术。"""
        ...

    def add_relation(self, src: str, rel: str, dst: str) -> None:
        """添加关系边（rel ∈ contains/precedes/uses/targets）。"""
        ...

    def related_techniques(self, technique_id: str, relation: str | None = None) -> list[MemoryPacket]:
        """返回与指定技战术关联的其他技战术（双向）。"""
        ...


def create_graph_store(mode: str = "in_memory", **kwargs) -> GraphStoreAPI:
    """按 mode 创建图存储（``"in_memory"`` 默认 / ``"neo4j"``）。

    Args:
        mode: 存储模式。
        **kwargs: 连接参数。

    Returns:
        满足 :class:`GraphStoreAPI` 的图存储实例。
    """
    from data.models.registry import create_graph_store as _create

    return _create(mode, **kwargs)


def create_vector_store(mode: str = "in_memory", **kwargs) -> VectorStoreAPI:
    """按 mode 创建向量存储（``"in_memory"`` 默认 / ``"qdrant"``）。

    Args:
        mode: 存储模式。
        **kwargs: 连接参数。

    Returns:
        满足 :class:`VectorStoreAPI` 的向量存储实例。
    """
    from data.models.registry import create_vector_store as _create

    return _create(mode, **kwargs)


def load_attck_dataset() -> list[MemoryPacket]:
    """加载 ATT&CK 数据集为 MemoryPacket 列表（记忆子系统预载共用源）。

    Returns:
        技战术知识包列表。
    """
    from data.datasets.attck.knowledge import load_attck_dataset as _load

    return _load()


__all__ = [
    "DatasetAPI",
    "ModelSchemaAPI",
    "GraphStoreAPI",
    "VectorStoreAPI",
    "create_graph_store",
    "create_vector_store",
    "load_attck_dataset",
]
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python -m pytest tests/data/ -v`
Expected: PASS（17 passed）

- [ ] **Step 5: Commit**

```bash
git add data/api/__init__.py tests/data/test_data_api.py
git commit -m "feat(data): expose GraphStoreAPI/VectorStoreAPI protocols and factories via data.api"
```

## Task 8: 配置（settings + defaults.yaml + pyproject）

**Files:**
- Modify: `tooling/configs/settings.py`
- Modify: `tooling/configs/defaults.yaml`
- Modify: `pyproject.toml`

**Interfaces:**
- Produces: `settings.storage`（`StorageConfig`）供 R3 装配消费。

- [ ] **Step 1: 在 `settings.py` 追加 `StorageConfig` 与根字段**

在 `FrontendEnvConfig` 类之后、`Settings` 类之前插入：
```python
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
```

- [ ] **Step 2: `Settings` 根新增 `storage` 字段**

在 `Settings` 类内 `frontend_env` 之后追加：
```python
    storage: StorageConfig = field(default_factory=StorageConfig)
```

- [ ] **Step 3: `_build_settings` 读取 storage 配置**

在 `_build_settings` 中，`fe_env = defaults.get("frontend_env", {})` 之后追加：
```python
    st = defaults.get("storage", {})
```
并在 `return Settings(...)` 的 `frontend_env=FrontendEnvConfig(...)` 之后追加：
```python
        storage=StorageConfig(
            graph_mode=_env("AEGIS_STORAGE_GRAPH_MODE", st.get("graph_mode", "in_memory")) or "in_memory",
            vector_mode=_env("AEGIS_STORAGE_VECTOR_MODE", st.get("vector_mode", "in_memory")) or "in_memory",
            neo4j_uri=_env("AEGIS_STORAGE_NEO4J_URI", st.get("neo4j_uri", "bolt://localhost:7687"))
            or "bolt://localhost:7687",
            neo4j_user=_env("AEGIS_STORAGE_NEO4J_USER", st.get("neo4j_user", "neo4j")) or "neo4j",
            neo4j_password=_env("AEGIS_STORAGE_NEO4J_PASSWORD", st.get("neo4j_password", "")) or "",
            qdrant_url=_env("AEGIS_STORAGE_QDRANT_URL", st.get("qdrant_url", "http://localhost:6333"))
            or "http://localhost:6333",
            qdrant_api_key=_env("AEGIS_STORAGE_QDRANT_API_KEY", st.get("qdrant_api_key", "")) or "",
            qdrant_collection=_env("AEGIS_STORAGE_QDRANT_COLLECTION", st.get("qdrant_collection", "memory_vectors"))
            or "memory_vectors",
        ),
```

- [ ] **Step 4: `defaults.yaml` 追加 storage 段**

在文件末尾追加：
```yaml
# --- 数据层存储后端（H2）---
storage:
  graph_mode: "in_memory"          # in_memory | neo4j
  vector_mode: "in_memory"         # in_memory | qdrant
  neo4j_uri: "bolt://localhost:7687"
  neo4j_user: "neo4j"
  neo4j_password: ""
  qdrant_url: "http://localhost:6333"
  qdrant_api_key: ""
  qdrant_collection: "memory_vectors"
```

- [ ] **Step 5: `pyproject.toml` 追加 storage extra**

在 `[project.optional-dependencies]` 中 `dev = [...]` 之后追加：
```toml
storage = [
    "neo4j>=5",
    "qdrant-client>=1.8",
]
```

- [ ] **Step 6: 验证配置加载**

Run: `python -c "from tooling.configs.settings import settings; s=settings.storage; print(s.graph_mode, s.vector_mode, s.neo4j_uri)"`
Expected: `in_memory in_memory bolt://localhost:7687`

- [ ] **Step 7: Commit**

```bash
git add tooling/configs/settings.py tooling/configs/defaults.yaml pyproject.toml
git commit -m "feat(data): add storage config section (graph/vector modes, neo4j/qdrant params)"
```

## Task 9: 规范登记 + R1 质量门禁

**Files:**
- Modify: `developer/specs/12_TECH_STACK_SPEC.md`
- Modify: `developer/specs/05_API_SPEC.md`

- [ ] **Step 1: `12_TECH_STACK_SPEC.md` 登记依赖**

在 §3 表格（后端/Agent/协议栈）末尾追加两行：
```
| **neo4j** | **>=5** | 图存储（网络拓扑 + ATT&CK 图）；可选 storage extra，惰性加载 | `data/models/graph_store.py` |
| **qdrant-client** | **>=1.8** | 向量存储（记忆嵌入）；可选 storage extra，惰性加载 | `data/models/vector_store.py` |
```

- [ ] **Step 2: `05_API_SPEC.md` §2.10 补充 Data API 契约**

在 §2.10 表格之后追加：
```
> **H2 新增**：`data.api` 暴露 `GraphStoreAPI`（拓扑 + ATT&CK）/ `VectorStoreAPI`（向量）+ 工厂 `create_graph_store(mode)` / `create_vector_store(mode)` / `load_attck_dataset()`。双实现：InMemory（默认，零依赖）/ Neo4j（`neo4j>=5` 惰性）/ Qdrant（`qdrant-client>=1.8` 惰性）。`GraphStoreAPI` 拓扑方法使用 `protocol.cyber.Asset`，ATT&CK 方法使用 `protocol.memory.MemoryPacket`；`VectorStoreAPI.search` 返回 `[(id, payload, score)]`。
```

- [ ] **Step 3: 安装 ruff 并跑 R1 全量门禁**

Run:
```bash
pip install ruff
ruff format data/ tests/data/ tooling/configs/settings.py
ruff check --fix data/ tests/data/ tooling/configs/settings.py
mypy data/ tests/data/
python -m pytest tests/ -q
```
Expected: ruff 完成、mypy 无错误、全量测试通过。

- [ ] **Step 4: 如有格式/类型问题就地修复**

修复后重跑 Step 3 直至全绿。

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "chore(data): register neo4j/qdrant in tech stack + API spec; R1 quality gate"
```

---

# R2 — aegisos_agents/memory 域（第 2 个域）

## Task 10: VectorMemory 后端注入

**Files:**
- Modify: `aegisos_agents/memory/vector/store.py`
- Test: `tests/aegisos_agents/memory/test_vector.py`（追加）

**Interfaces:**
- Consumes: `data.api.VectorStoreAPI`（Task 7，仅类型标注）。
- Produces: `VectorMemory(backend: VectorStoreAPI | None = None)` —— R2 Task 12 消费。

- [ ] **Step 1: 追加失败测试**

在 `tests/aegisos_agents/memory/test_vector.py` 末尾追加：
```python
from data.api import create_vector_store


def test_vector_backend_injected_delegates():
    """提供 backend 时 add/search/all/len 应委托后端。"""
    backend = create_vector_store("in_memory")
    vm = VectorMemory(backend=backend)
    vm.add(MemoryPacket(task_id="b1", embedding=[1.0, 0.0], summary="backend hit"))
    assert len(vm) == 1
    result = vm.search([1.0, 0.0], top_k=1)
    assert result[0].task_id == "b1"
    assert result[0].summary == "backend hit"


def test_vector_backend_empty_embedding_skipped():
    backend = create_vector_store("in_memory")
    vm = VectorMemory(backend=backend)
    vm.add(MemoryPacket(task_id="empty", embedding=[]))
    assert len(vm) == 0
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/aegisos_agents/memory/test_vector.py -v`
Expected: FAIL（TypeError: unexpected keyword argument 'backend'）

- [ ] **Step 3: 修改 `VectorMemory`**

在 `aegisos_agents/memory/vector/store.py` import 区追加 `from data.api import VectorStoreAPI`，并将类实现替换为（保留原内存逻辑为 backend=None 分支）：
```python
class VectorMemory:
    """向量记忆存储 —— 基于余弦相似度的语义检索（Qdrant 预留位 / 后端注入）。

    默认纯内存实现；传入 :class:`VectorStoreAPI` 后端（如 ``data.api`` 工厂创建的
    InMemory/Qdrant 存储）时，增删查委托给后端，行为对上层一致。

    Attributes:
        _backend: 可选的外部向量存储后端。
        _items: 内部维护的记忆列表（仅含 embedding 非空者）。
    """

    def __init__(self, backend: VectorStoreAPI | None = None) -> None:
        """初始化向量记忆存储。

        Args:
            backend: 可选的外部向量存储后端；为 None 时用内置内存实现。
        """
        self._backend = backend
        self._items: list[MemoryPacket] = []

    @staticmethod
    def _payload(packet: MemoryPacket) -> dict:
        """序列化 MemoryPacket 关键字段为向量 payload。

        Args:
            packet: 待序列化的记忆包。

        Returns:
            task_id/summary/kind/session_id 组成的 dict。
        """
        return {
            "task_id": packet.task_id,
            "summary": packet.summary,
            "kind": packet.kind,
            "session_id": packet.session_id,
        }

    @classmethod
    def _restore(cls, vector_id: str, payload: dict) -> MemoryPacket:
        """从后端 (id, payload) 还原 MemoryPacket。

        Args:
            vector_id: 向量标识（task_id 缺失时的兜底）。
            payload: 序列化字段 dict。

        Returns:
            还原后的记忆包。
        """
        return MemoryPacket(
            task_id=payload.get("task_id") or vector_id,
            summary=payload.get("summary", ""),
            kind=payload.get("kind", "normal"),
            session_id=payload.get("session_id", ""),
        )

    def add(self, packet: MemoryPacket) -> None:
        """索引一条记忆向量。

        Args:
            packet: 待索引的记忆片段，须携带 ``embedding``。
        """
        if not packet.embedding:  # 空列表跳过，避免无效索引项
            return
        if self._backend is not None:
            self._backend.add(
                packet.task_id or f"vec_{self._backend.count()}",
                packet.embedding,
                self._payload(packet),
            )
            return
        self._items.append(packet)

    def search(self, query: list[float], top_k: int = 5) -> list[MemoryPacket]:
        """按查询向量做余弦相似度检索，返回 Top-K 记忆。

        Args:
            query: 查询向量；为空时返回空列表。
            top_k: 返回条数上限，默认 5。

        Returns:
            按相似度降序排列的记忆列表，长度不超过 ``top_k``。
        """
        if not query or top_k <= 0:
            return []
        if self._backend is not None:
            hits = self._backend.search(query, top_k=top_k)
            return [self._restore(vid, payload) for vid, payload, _score in hits]
        scored = [(p, _cosine(query, p.embedding)) for p in self._items]
        # 按相似度降序；同分保持原写入顺序（stable sort）
        scored.sort(key=lambda x: x[1], reverse=True)
        return [p for p, _ in scored[:top_k]]

    def all(self) -> list[MemoryPacket]:
        """返回全部已索引的记忆（按写入顺序）。"""
        if self._backend is not None:
            return [self._restore(vid, payload) for vid, payload in self._backend.all()]
        return list(self._items)

    def __len__(self) -> int:
        """返回已索引的记忆条数。"""
        if self._backend is not None:
            return self._backend.count()
        return len(self._items)
```

> 说明：`_restore` 还原的记忆不携带 embedding（后端 search 不带向量），符合语义——检索结果用于上下文注入，不需再次计算相似度。`_items` 始终初始化以满足 mypy 严格模式；backend 存在时不会被访问。

- [ ] **Step 4: 运行测试确认通过**

Run: `python -m pytest tests/aegisos_agents/memory/test_vector.py -v`
Expected: PASS（5 旧 + 2 新）

## Task 11: SemanticMemory 图后端注入

**Files:**
- Modify: `aegisos_agents/memory/semantic/store.py`
- Test: `tests/aegisos_agents/memory/test_semantic.py`（追加）

**Interfaces:**
- Consumes: `data.api.GraphStoreAPI`、`data.api.load_attck_dataset`（Task 7）。
- Produces: `SemanticMemory(seed=True, graph_backend: GraphStoreAPI | None = None)` —— R2 Task 12 消费。

- [ ] **Step 1: 追加失败测试**

在 `tests/aegisos_agents/memory/test_semantic.py` 末尾追加：
```python
from data.api import create_graph_store


def test_semantic_graph_backend_delegates():
    """提供 graph_backend 时 get/search/all/len 应委托后端。"""
    backend = create_graph_store("in_memory", seed_attck=False)
    sm = SemanticMemory(seed=False, graph_backend=backend)
    sm.add("T0000", MemoryPacket(task_id="T0000", summary="probe", semantic={"technique_id": "T0000", "name": "Probe", "tactic": "test"}))
    assert sm.get("T0000") is not None
    assert len(sm.search("probe")) == 1
    assert len(sm) == 1


def test_semantic_graph_backend_seeds_when_empty():
    """graph_backend 为空且 seed=True 时应从数据集预载。"""
    backend = create_graph_store("in_memory", seed_attck=False)
    sm = SemanticMemory(seed=True, graph_backend=backend)
    assert len(sm) >= 30
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/aegisos_agents/memory/test_semantic.py -v`
Expected: FAIL（TypeError: unexpected keyword argument 'graph_backend'）

- [ ] **Step 3: 修改 `SemanticMemory`**

在 `aegisos_agents/memory/semantic/store.py` import 区追加 `from data.api import GraphStoreAPI, load_attck_dataset`，并将类实现替换为（`seed_attack_knowledge` 原样保留）：
```python
class SemanticMemory:
    """语义记忆存储 —— 结构化知识库（ATT&CK/CVE）。

    默认内存 dict + 种子；传入 :class:`GraphStoreAPI` 后端时，
    读写委托给图存储（ATT&CK 知识查询走后端）。

    Attributes:
        _backend: 可选的外部图存储后端。
        _knowledge: 内部维护的 concept_id -> 知识记忆包。
    """

    def __init__(self, seed: bool = True, graph_backend: GraphStoreAPI | None = None) -> None:
        """初始化语义记忆存储。

        Args:
            seed: 是否在构造时预置 ATT&CK 知识，默认 ``True``。
            graph_backend: 可选的外部图存储后端；为 None 时用内置内存实现。
        """
        self._backend = graph_backend
        self._knowledge: dict[str, MemoryPacket] = {}
        if graph_backend is None:
            if seed:
                self.seed_attack_knowledge()
        elif seed:
            # 后端为空时从共享数据集预载，避免首次查询退化
            if not graph_backend.all_techniques():
                graph_backend.seed_attck(load_attck_dataset())

    def add(self, concept_id: str, packet: MemoryPacket) -> None:
        """写入或覆盖一条知识条目。

        Args:
            concept_id: 知识概念唯一标识（如 ATT&CK 技战术 ID ``T1210``）。
            packet: 知识记忆包，其 ``semantic`` 字段承载结构化事实。
        """
        if self._backend is not None:
            self._backend.upsert_technique(concept_id, packet)
            return
        self._knowledge[concept_id] = packet

    def get(self, concept_id: str) -> MemoryPacket | None:
        """按概念 ID 精确查询知识条目。

        Args:
            concept_id: 目标概念标识符。

        Returns:
            匹配的知识记忆包；未找到时返回 ``None``。
        """
        if self._backend is not None:
            return self._backend.get_technique(concept_id)
        return self._knowledge.get(concept_id)

    def search(self, keyword: str) -> list[MemoryPacket]:
        """关键词检索知识库（大小写不敏感）。

        Args:
            keyword: 检索关键词，如 ``"lateral"``、``"扫描"``。

        Returns:
            命中的知识记忆包列表。
        """
        if self._backend is not None:
            return self._backend.search_techniques(keyword)
        kw = keyword.lower()
        hits: list[MemoryPacket] = []
        for packet in self._knowledge.values():
            # summary 文本匹配
            if kw in (packet.summary or "").lower():
                hits.append(packet)
                continue
            # semantic 字典各值文本匹配
            for v in packet.semantic.values():
                if kw in str(v).lower():
                    hits.append(packet)
                    break
        return hits

    def all(self) -> list[MemoryPacket]:
        """返回全部知识条目。"""
        if self._backend is not None:
            return self._backend.all_techniques()
        return list(self._knowledge.values())

    def seed_attack_knowledge(self) -> None:
        """预置 ATT&CK 种子技战术知识。"""
        for tid, (name, tactic, desc) in _ATTACK_SEED.items():
            self._knowledge[tid] = MemoryPacket(
                task_id=tid,
                summary=f"{tid} {name}",
                semantic={
                    "technique_id": tid,
                    "name": name,
                    "tactic": tactic,
                    "description": desc,
                },
                kind="decision",
            )

    def __len__(self) -> int:
        """返回知识条目总数。"""
        if self._backend is not None:
            return len(self._backend.all_techniques())
        return len(self._knowledge)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python -m pytest tests/aegisos_agents/memory/test_semantic.py -v`
Expected: PASS（4 旧 + 2 新）

## Task 12: MemoryStore 可选注入 + R2 门禁

**Files:**
- Modify: `aegisos_agents/memory/memory_store.py`
- Test: `tests/aegisos_agents/memory/test_memory_store.py`（追加）

**Interfaces:**
- Consumes: `data.api.VectorStoreAPI` / `GraphStoreAPI`（Task 7）、Task 10/11。
- Produces: `MemoryStore(vector_backend=None, graph_backend=None)` —— R3 装配消费。

- [ ] **Step 1: 追加失败测试**

在 `tests/aegisos_agents/memory/test_memory_store.py` 末尾追加：
```python
from data.api import create_graph_store, create_vector_store


def test_memory_store_backend_injection():
    """MemoryStore 注入 vector/graph 后端后读写检索应工作。"""
    ms = MemoryStore(
        vector_backend=create_vector_store("in_memory"),
        graph_backend=create_graph_store("in_memory", seed_attck=False),
    )
    ms.write(MemoryPacket(task_id="m1", embedding=[1.0, 0.0], summary="vec hit"))
    assert len(ms.vector) == 1
    assert ms.vector.search([1.0, 0.0])[0].task_id == "m1"
    ms.semantic.add("T9999", MemoryPacket(task_id="T9999", summary="kb", semantic={"technique_id": "T9999", "name": "KB", "tactic": "test"}))
    assert ms.semantic.get("T9999") is not None


def test_memory_store_default_no_backend_unchanged():
    """不注入后端时行为与现状一致。"""
    ms = MemoryStore()
    ms.write(MemoryPacket(task_id="d1", embedding=[1.0], summary="default"))
    assert len(ms.vector) == 1
    assert ms.semantic.get("T1210") is not None
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/aegisos_agents/memory/test_memory_store.py -v`
Expected: FAIL（TypeError: unexpected keyword argument 'vector_backend'）

- [ ] **Step 3: 修改 `MemoryStore.__init__`**

在 `aegisos_agents/memory/memory_store.py` import 区追加 `from data.api import GraphStoreAPI, VectorStoreAPI`，并替换 `__init__`：
```python
    # date: 2026-08-06
    # dev: czy
    # changelog: 新增 vector_backend/graph_backend 可选注入，对接 data 层存储后端
    def __init__(
        self,
        vector_backend: VectorStoreAPI | None = None,
        graph_backend: GraphStoreAPI | None = None,
    ) -> None:
        """初始化记忆集成存储，装配四层子存储 + 七个 v2 子模块。

        Args:
            vector_backend: 可选的外部向量存储后端（默认 None → 内置内存实现）。
            graph_backend: 可选的外部图存储后端（默认 None → 内置内存知识库）。
        """
        self.working = WorkingMemory()
        self.episodic = EpisodicMemory()
        self.semantic = SemanticMemory(seed=True, graph_backend=graph_backend)
        self.vector = VectorMemory(backend=vector_backend)
        # ---- v2 新增：7 个子模块 ----
        self.retrieval_engine = RetrievalEngine(self.vector, self.semantic, self.episodic)
        self.cache = MemoryCache()
        self.checkpoint = CheckpointManager(self)
        self.reflection = ReflectionEngine()
        self.archive = ArchiveStore()
        self.snapshot = SnapshotManager()
        self.sync = MemorySync()
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python -m pytest tests/aegisos_agents/memory/ -v`
Expected: PASS（75 旧 + 新增全绿）

- [ ] **Step 5: R2 质量门禁**

Run:
```bash
ruff format aegisos_agents/memory/ tests/aegisos_agents/memory/
ruff check --fix aegisos_agents/memory/ tests/aegisos_agents/memory/
mypy aegisos_agents/memory/
python -m pytest tests/ -q
```
Expected: 全绿（含 data 17 + memory 新增 + 其余域）。

- [ ] **Step 6: Commit**

```bash
git add aegisos_agents/memory/ tests/aegisos_agents/memory/
git commit -m "feat(memory): injectable vector/graph backends for VectorMemory/SemanticMemory/MemoryStore"
```

---

# R3 — 装配与文档收尾（第 3 轮）

## Task 13: backend/composition 接线

**Files:**
- Modify: `backend/core/composition.py`

**Interfaces:**
- Consumes: `data.api.create_*`（Task 7）、`settings.storage`（Task 8）、`MemoryStore`（Task 12）。

- [ ] **Step 1: 修改 import 区与 `Composition.__init__`**

在 `backend/core/composition.py` 的 `from aegisos_agents.memory.memory_store import MemoryStore` 之后追加：
```python
# date: 2026-08-06
# dev: czy
# changelog: 接入 data 层存储后端（默认 in_memory）
from data.api import create_graph_store, create_vector_store
from tooling.configs.settings import settings
```
将 `self.memory_api = MemoryStore()` 替换为：
```python
        # date: 2026-08-06
        # dev: czy
        # changelog: MemoryStore 注入 data 层存储后端（默认 in_memory，真实库按配置启用）
        self.memory_api = MemoryStore(
            vector_backend=self._build_vector_backend(),
            graph_backend=self._build_graph_backend(),
        )
```
并在类内追加两个静态方法（放在 `_create_orchestrator` 之前）：
```python
    @staticmethod
    def _build_vector_backend():
        """按 settings.storage 构造向量存储后端；in_memory 模式返回 None。

        Returns:
            VectorStoreAPI 实例或 None（使用记忆模块内置实现）。
        """
        s = settings.storage
        if s.vector_mode == "in_memory":
            return None
        return create_vector_store(
            s.vector_mode,
            url=s.qdrant_url,
            api_key=s.qdrant_api_key,
            collection=s.qdrant_collection,
        )

    @staticmethod
    def _build_graph_backend():
        """按 settings.storage 构造图存储后端；in_memory 模式返回 None。

        Returns:
            GraphStoreAPI 实例或 None（使用记忆模块内置实现）。
        """
        s = settings.storage
        if s.graph_mode == "in_memory":
            return None
        return create_graph_store(
            s.graph_mode,
            uri=s.neo4j_uri,
            user=s.neo4j_user,
            password=s.neo4j_password,
        )
```

- [ ] **Step 2: 验证组合根可实例化（默认模式）**

Run: `python -c "from backend.core.composition import Composition; c = Composition(); print(type(c.memory_api).__name__); c.memory_api.semantic.get('T1210')"`
Expected: `MemoryStore` 且 T1210 查询非 None（默认 in_memory，无需 DB）。

- [ ] **Step 3: 回归后端测试**

Run: `python -m pytest tests/backend/ -q`
Expected: 全绿。

## Task 14: 文档同步

**Files:**
- Modify: `data/AGENT.md`
- Modify: `aegisos_agents/memory/AGENT.md`
- Modify: `aegisos_agents/AGENT.md`、根 `AGENT.md`、`CLAUDE.md`、`docs/ARCHITECTURE.md`
- Modify: `developer/plan.md`、`developer/CHANGELOG.md`

按 11_AI_CODING_SPEC §7 逐一同步（具体改动要点）：

- [ ] **Step 1: `data/AGENT.md`「📋 模块实现详解」更新**

目录结构更新为含 `models/graph_store.py` / `vector_store.py` / `registry.py`、`datasets/attck/knowledge.py`；「已实现」补 `data/api` 四接口（DatasetAPI/ModelSchemaAPI/GraphStoreAPI/VectorStoreAPI）+ 工厂；「未实现」删除 Neo4j/Qdrant 两行并注明「✅ H2 完成（双实现适配层，默认 in_memory，真实库按配置启用）」。

- [ ] **Step 2: `aegisos_agents/memory/AGENT.md` 更新**

模块清单表：vector 行与 semantic 行状态更新为「✅ (P2) + H2 后端注入」；「接口」段补一句：`VectorMemory(backend)` / `SemanticMemory(graph_backend)` / `MemoryStore(vector_backend, graph_backend)` 支持 `data.api` 存储后端注入。

- [ ] **Step 3: 全局仪表盘文档更新**

- `aegisos_agents/AGENT.md`：记忆子系统段补「H2 对接 data 层存储后端」。
- 根 `AGENT.md`「📋 模块实现总览」：data 域行更新为「✅ H2 完成（InMemory/Neo4j/Qdrant 双实现）」+ 测试数更新；全局仪表盘测试数更新。
- `CLAUDE.md`：测试数与「下一步计划」更新（H2 ✅）。
- `docs/ARCHITECTURE.md`：data 域仪表盘更新。

- [ ] **Step 4: `developer/plan.md` 勾选**

将 §3 H2 数据层接入 4 项全部改为 `[x]`，整体状态改为「✅ 完成（2026-08-06）」；新增「最近变更」条目；按规则在 §7 完成区记录。

- [ ] **Step 5: `developer/CHANGELOG.md` 记录**

追加：`2026-08-06 H2 数据层接入完成 — data/models 双实现（InMemory/Neo4j/Qdrant）+ data/api 新接口与工厂 + memory 后端注入 + storage 配置`。

## Task 15: 全量质量门禁 + README 刷新 + 提交

- [ ] **Step 1: 刷新根 README**

Run: `python tooling/scripts/gen_readme.py`
Expected: 根 `README.md` 自动段刷新。

- [ ] **Step 2: 完整质量门禁**

Run:
```bash
ruff format .
ruff check --fix .
mypy .
python -m pytest tests/ -q
```
Expected: 全绿。

- [ ] **Step 3: 更新设计文档「实施完成」标记**

在 `docs/superpowers/specs/2026-08-06-h2-data-layer-neo4j-qdrant-design.md` 头部 `状态` 行改为 `已实施（R1-R3 完成）`。

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat(H2): wire data-layer storage backends + docs sync — H2 complete"
```

- [ ] **Step 5: 验证 git 干净**

Run: `git status --short`
Expected: 无未提交改动（此前遗留的 `docs/P2-*.md` 与 `.claude/settings.json` 未跟踪文件除外）。
