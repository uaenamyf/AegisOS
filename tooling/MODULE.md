# tooling/ 模块实现文档

> 工程支撑层 — configs（配置） · scripts（工具脚本）。

📁 模块规范：[`AGENT.md`](AGENT.md) · 开发流程：[`09_DEVELOPMENT_SPEC.md`](../developer/specs/09_DEVELOPMENT_SPEC.md)

---

## 目录结构

```
tooling/
├── api/
│   └── __init__.py        ✅ 2 个 Protocol 接口定义
├── configs/
│   ├── backend.yaml       ✅ 后端配置
│   └── gateway.yaml       ✅ 网关配置
└── scripts/
    ├── gen_readme.py          ✅ README 自动生成
    ├── gen_ts_types.py        ✅ TS 类型自动生成
    ├── realign_agent_docs.py  ✅ AGENT.md 对齐
    └── add_agent_crossrefs.pl ✅ 批量添加交叉引用（Perl）
```

---

## 已实现

### `api/__init__.py` — 2 个公共接口（Protocol）

| 接口 | 方法 | 说明 |
|------|------|------|
| `ConfigAPI` | `get(key)` · `set(key, value)` · `load(profile)` | 配置管理 |
| `ScriptAPI` | `run(name, args)` · `list()` · `result(run_id)` | 脚本执行 |

---

### 工具脚本

#### `gen_readme.py` — README 自动生成

```bash
python3 tooling/scripts/gen_readme.py
```

**功能**：
- 遍历项目目录树
- 统计：顶层域数 · 总目录 · 总文件 · AGENT.md 数 · Python 文件数 · Markdown 文件数 · API 接口数 · protocol 契约类型数
- 生成目录树块
- 生成统计表

---

#### `gen_ts_types.py` — TypeScript 类型自动生成

```bash
python3 tooling/scripts/gen_ts_types.py
# 或
npm run gen:types
```

**功能**：
- 读取 `protocol/*.py` 的 `@dataclass` 类
- 将 Python 类型映射为 TypeScript 类型（`str → string`, `int → number`, `list → array`, `dict → Record`）
- 将 `Enum` 映射为 TS 联合类型
- 输出到 `frontend/src/protocol/types.ts`（36 个类型）

---

#### `realign_agent_docs.py` — AGENT.md 对齐

```bash
python3 tooling/scripts/realign_agent_docs.py
```

**功能**：
- 扫描全仓库 `AGENT.md` 文件
- 检查交叉引用是否与实际目录结构一致
- 自动修正引用路径

---

#### `add_agent_crossrefs.pl` — 批量添加交叉引用

```bash
perl tooling/scripts/add_agent_crossrefs.pl
```

**功能**：Perl 脚本，批量在各模块 AGENT.md 中添加「交叉引用（去哪里找）」段。

---

### 配置文件

#### `backend.yaml`

```yaml
backend:
  cors:
    origins:
      - http://localhost:5173
      - http://127.0.0.1:5173
```

#### `gateway.yaml`

网关路由配置。

---

## 未实现

- 🔲 `check_no_broadcast.py` — 全广播违规 CI 校验脚本（C4 待做）
