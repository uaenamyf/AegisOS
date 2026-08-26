# date: 2026-08-01
# dev: 123 chen
"""执行批判 —— 对 Agent 产出做多维结构检查。

纯算法实现：结构完整性、数据合理性、逻辑一致性、空结果检测四维检查，
不依赖 LLM 调用。用于产生 :class:`Critique` 列表供后续评分使用。
"""

from __future__ import annotations

from dataclasses import dataclass

# 合法端口范围
PORT_MIN, PORT_MAX = 1, 65535

# 常见破坏性操作关键词（用于 safety 检测）
DESTRUCTIVE_KEYWORDS = [
    "rm -rf", "drop table", "format", "shutdown",
    "delete", "destroy", "wipe", "erase",
]


@dataclass
class Critique:
    """执行批判条目。

    Attributes:
        dimension: 检查维度（completeness / sanity / consistency / emptiness）。
        severity: 严重度（high / medium / low）。
        message: 人类可读的问题描述。
        field: 关联字段名（可选）。
    """

    dimension: str = ""
    severity: str = "low"
    message: str = ""
    field: str = ""


class ExecutionCritic:
    """对 Agent 执行输出做多维批判检查。

    四维检查：
        - 结构完整性：必需字段是否存在且非空。
        - 数据合理性：字段值是否在合法范围（端口、IP格式等）。
        - 逻辑一致性：输入与输出间是否有明显矛盾。
        - 空结果检测：是否返回空列表/空对象（可能执行失败）。

    Attributes:
        无实例属性；本类为纯函数集合。
    """

    # ---- 公开接口 ----

    def critique(
        self,
        output: dict,
        expected_fields: list[str] | None = None,
        input_context: dict | None = None,
    ) -> list[Critique]:
        """对输出做完整四维批判检查。

        Args:
            output: Agent 执行输出的字典。
            expected_fields: 期望存在的字段列表，为 None 时跳过完整性检查。
            input_context: 原始输入上下文（用于逻辑一致性检查），可选。

        Returns:
            :class:`Critique` 列表，按严重度降序排列。
        """
        critiques: list[Critique] = []
        # 1) 结构完整性
        if expected_fields:
            critiques.extend(self._check_completeness(output, expected_fields))
        # 2) 空结果检测
        critiques.extend(self._check_emptiness(output))
        # 3) 数据合理性
        critiques.extend(self._check_sanity(output))
        # 4) 逻辑一致性
        if input_context:
            critiques.extend(self._check_consistency(output, input_context))
        # 按严重度排序：high 在前
        sev_order = {"high": 0, "medium": 1, "low": 2}
        critiques.sort(key=lambda c: sev_order.get(c.severity, 99))
        return critiques

    def has_blocker(self, critiques: list[Critique]) -> bool:
        """是否存在高严重度（blocker）问题。

        Args:
            critiques: 批判列表。

        Returns:
            ``True`` 表示存在必须修复的问题。
        """
        return any(c.severity == "high" for c in critiques)

    # ---- 私有检查方法 ----

    def _check_completeness(
        self, output: dict, expected_fields: list[str]
    ) -> list[Critique]:
        """检查必需字段是否存在且非空。

        Args:
            output: 输出字典。
            expected_fields: 期望存在的字段列表。

        Returns:
            缺失字段的批判条目列表。
        """
        critiques: list[Critique] = []
        for field in expected_fields:
            val = output.get(field)
            if val is None:
                critiques.append(
                    Critique(
                        dimension="completeness",
                        severity="high",
                        message=f"缺少必需字段: {field}",
                        field=field,
                    )
                )
            elif isinstance(val, (list, dict)) and len(val) == 0:
                critiques.append(
                    Critique(
                        dimension="completeness",
                        severity="medium",
                        message=f"字段 {field} 为空（可能未产出有效结果）",
                        field=field,
                    )
                )
        return critiques

    def _check_emptiness(self, output: dict) -> list[Critique]:
        """检测整体输出是否为空（关键指示执行失败）。

        Args:
            output: 输出字典。

        Returns:
            空结果批判条目。
        """
        if not output:
            return [
                Critique(
                    dimension="emptiness",
                    severity="high",
                    message="输出完全为空",
                )
            ]
        # 检测最外层列表/字典是否为空
        for key in ("assets", "findings", "alerts", "hypotheses", "steps", "result"):
            val = output.get(key)
            if isinstance(val, list) and len(val) == 0:
                return [
                    Critique(
                        dimension="emptiness",
                        severity="medium",
                        message=f"关键字段 {key} 为空列表，可能未发现任何目标",
                        field=key,
                    )
                ]
        return []

    def _check_sanity(self, output: dict) -> list[Critique]:
        """检查字段值的数据合理性（端口范围、破坏性标记等）。

        Args:
            output: 输出字典。

        Returns:
            数据异常条目列表。
        """
        critiques: list[Critique] = []
        # 递归检查所有字段值中的 port 数字 / 破坏性操作标记
        for key, val in self._flatten(output).items():
            if "port" in key.lower() and isinstance(val, int):
                if val < PORT_MIN or val > PORT_MAX:
                    critiques.append(
                        Critique(
                            dimension="sanity",
                            severity="medium",
                            message=f"端口号 {val} 超出合法范围 [{PORT_MIN}, {PORT_MAX}]",
                            field=key,
                        )
                    )
            elif "action" in key.lower() and isinstance(val, str):
                val_lower = val.lower()
                for kw in DESTRUCTIVE_KEYWORDS:
                    if kw in val_lower:
                        critiques.append(
                            Critique(
                                dimension="sanity",
                                severity="high",
                                message=f"检测到破坏性操作: {val}",
                                field=key,
                            )
                        )
        return critiques

    def _check_consistency(
        self, output: dict, input_context: dict
    ) -> list[Critique]:
        """检查输入与输出间的基本逻辑一致性。

        Args:
            output: 输出字典。
            input_context: 输入上下文字典。

        Returns:
            逻辑不一致条目列表。
        """
        critiques: list[Critique] = []
        # 检查 target_range 是否被覆盖
        target = input_context.get("target_range", "")
        output_str = str(output).lower()
        if target and target.lower() not in output_str and "assets" in output:
            assets = output.get("assets", [])
            if isinstance(assets, list) and len(assets) == 0:
                critiques.append(
                    Critique(
                        dimension="consistency",
                        severity="medium",
                        message=f"target_range={target} 但 assets 为空，可能扫描未覆盖目标",
                        field="assets",
                    )
                )
        return critiques

    # ---- 工具方法 ----

    @staticmethod
    def _flatten(d: dict, prefix: str = "") -> dict:
        """将嵌套字典扁平化为一级 key-value。

        Args:
            d: 待扁平化的字典。
            prefix: 当前键前缀。

        Returns:
            扁平化后的字典。
        """
        result: dict = {}
        for k, v in d.items():
            fk = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                result.update(ExecutionCritic._flatten(v, fk))
            elif isinstance(v, list):
                for i, item in enumerate(v):
                    if isinstance(item, dict):
                        result.update(ExecutionCritic._flatten(item, f"{fk}[{i}]"))
                    else:
                        result[f"{fk}[{i}]"] = item
            else:
                result[fk] = v
        return result
