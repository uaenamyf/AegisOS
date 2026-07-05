# date: 2026-06-27
# dev: myf
# changelog: 新建 DI 端口定义，供智能体回调后端能力（持久化/会话/任务状态），由后端实现并注入
"""智能体域 DI 端口定义 —— 后端能力的反向注入接口。

本模块定义了一组 ``Protocol`` 端口，供智能体域（runtime / action）在运行时
回调后端能力（持久化、会话上下文、任务状态写回）。端口由后端实现
（``backend/services/agent/ports.py``）并在组合根 ``backend/composition.py``
处注入，从而实现依赖倒置（DIP）：

- 智能体域依赖自身抽象（本文件），不反向 import 后端；
- 后端依赖 ``agents.api.ports``（正向依赖）并提供实现。

详见 ``developer/specs/plans/13_FRONTEND_BACKEND_PLAN.md`` §3.2。
"""

from __future__ import annotations

from typing import Protocol

from protocol import TaskStatus


class PersistencePort(Protocol):
    """持久化能力端口，供智能体保存任务结果与产物。

    该端口由后端实现，智能体域通过此抽象访问持久化存储，
    避免对后端具体实现的直接依赖。

    Attributes:
        无实例属性；本端口为 ``Protocol``，仅约束方法签名。
    """

    def save_task_result(self, task_id: str, result: dict) -> bool:
        """保存单个任务的执行结果。

        Args:
            task_id: 任务唯一标识符。
            result: 任务执行结果，以字典形式承载结构化数据。

        Returns:
            bool: 保存成功返回 ``True``，失败返回 ``False``。
        """
        ...

    def save_artifact(self, task_id: str, name: str, content: bytes) -> str:
        """保存任务产物（如生成文件、二进制数据）。

        Args:
            task_id: 关联任务标识符。
            name: 产物名称（用于检索与展示）。
            content: 产物的二进制内容。

        Returns:
            str: 产物的存储路径或唯一引用标识；失败时由实现决定返回值。
        """
        ...


class SessionPort(Protocol):
    """会话与用户上下文能力端口，供智能体获取运行时上下文。

    智能体在规划与执行时，可通过此端口读取当前会话信息及用户上下文，
    以实现个性化推理与权限感知。

    Attributes:
        无实例属性；本端口为 ``Protocol``，仅约束方法签名。
    """

    def get_session(self, session_id: str) -> dict:
        """获取会话信息。

        Args:
            session_id: 会话唯一标识符。

        Returns:
            dict: 会话信息字典，包含会话状态、时间戳等字段。
        """
        ...

    def get_user_context(self, session_id: str) -> dict:
        """获取会话关联的用户上下文。

        Args:
            session_id: 会话唯一标识符，用于定位所属用户。

        Returns:
            dict: 用户上下文字典，可包含用户偏好、权限、画像等信息。
        """
        ...


class TaskUpdatePort(Protocol):
    """任务状态写回能力端口，供智能体更新任务生命周期状态。

    智能体在执行过程中通过此端口将任务状态（如进行中、成功、失败）
    同步回后端，驱动外部任务编排与可观测展示。

    Attributes:
        无实例属性；本端口为 ``Protocol``，仅约束方法签名。
    """

    def update_status(self, task_id: str, status: TaskStatus) -> bool:
        """更新指定任务的执行状态。

        Args:
            task_id: 任务唯一标识符。
            status: 目标状态，取值见 ``protocol.TaskStatus`` 枚举。

        Returns:
            bool: 更新成功返回 ``True``，失败返回 ``False``。
        """
        ...


__all__ = ["PersistencePort", "SessionPort", "TaskUpdatePort"]  # 对外暴露三个 DI 端口
