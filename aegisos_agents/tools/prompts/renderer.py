# date: 2026-08-03
# dev: 123 chen
"""Prompt 渲染器 —— 模板变量替换 + 校验。

支持 ``{{ var_name }}`` 占位符替换为实际值，并在渲染前校验
缺失变量，避免发送不完整的 Prompt 给 LLM。
"""

from __future__ import annotations

import re

# 匹配 {{ variable_name }} 模式
_VAR_PATTERN = re.compile(r"\{\{\s*(\w+)\s*\}\}")


class PromptRenderer:
    """Prompt 模板渲染器。

    支持 ``{{ var_name }}`` 变量替换，以及渲染前变量校验。

    Attributes:
        无实例属性；本类为纯函数集合。
    """

    @staticmethod
    def render(template_content: str, variables: dict[str, str]) -> str:
        """渲染模板：将 ``{{ var }}`` 替换为 variables 中对应值。

        Args:
            template_content: 含占位符的模板字符串。
            variables: 变量名到值的映射。

        Returns:
            渲染后的 Prompt 字符串。

        Raises:
            ValueError: 当模板引用了 variables 中不存在的变量时。
        """
        missing = PromptRenderer.validate(template_content, variables)
        if missing:
            raise ValueError(
                f"模板渲染失败：缺少变量 {missing}，"
                f"请确认 variables 中是否包含这些键。"
            )

        def _replace(match: re.Match) -> str:
            var_name = match.group(1)
            return variables.get(var_name, match.group(0))

        return _VAR_PATTERN.sub(_replace, template_content)

    @staticmethod
    def validate(template_content: str, variables: dict[str, str]) -> list[str]:
        """校验模板中的变量是否都已提供。

        Args:
            template_content: 模板字符串。
            variables: 提供的变量字典。

        Returns:
            缺失的变量名列表；全部提供时返回空列表。
        """
        required = set(_VAR_PATTERN.findall(template_content))
        provided = set(variables.keys())
        return sorted(required - provided)

    @staticmethod
    def extract_variables(template_content: str) -> list[str]:
        """从模板内容中提取所有变量名。

        Args:
            template_content: 模板字符串。

        Returns:
            去重后的变量名列表。
        """
        return sorted(set(_VAR_PATTERN.findall(template_content)))
