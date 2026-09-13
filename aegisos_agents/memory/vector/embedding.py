# date: 2026-09-13
# dev: OpenSquilla
# changelog: 新增轻量确定性文本嵌入——激活向量检索通道（离线、零模型依赖）

"""轻量确定性文本嵌入。

在未接入真实 embedding 模型（如 bge / OpenAI embedding）前，为记忆文本生成
一个**确定性的字符 n-gram 哈希向量**，使 :class:`VectorMemory` 的余弦相似度
通道真正工作（而非空转），从而让 RRF 混合检索的"向量通道"名实相符。

设计要点：
    - 纯标准库 + ``hashlib``，离线可跑，演示/评测零依赖。
    - 特征 = 字符级 2-gram 词袋，经 ``md5`` 哈希映射到固定维度向量。
    - 每个特征在其桶位累加权重并做 L2 归一化，得到单位向量，供余弦相似度使用。
    - 维度 ``DEFAULT_DIM`` 默认 256，够小、够稳；可在构造时调整。

升级路径：对接真实 embedding 模型时，仅需替换 :func:`embed_text` 的实现，
保留同签名即可无缝切换（接口稳定，行为对上层一致）。
"""

from __future__ import annotations

import hashlib
import math
import re

DEFAULT_DIM = 256
_TOKEN_RE = re.compile(r"[\w\u4e00-\u9fff]+", re.UNICODE)


class HashingEmbedder:
    """字符 n-gram 哈希嵌入器（确定性，离线可用）。"""

    def __init__(self, dim: int = DEFAULT_DIM, ngram: int = 2) -> None:
        """初始化嵌入器。

        Args:
            dim: 向量维度。
            ngram: 字符 n-gram 窗口大小，默认 2（bigram）。
        """
        self.dim = dim
        self.ngram = ngram

    def _features(self, text: str) -> list[str]:
        """从文本提取字符 n-gram 特征。

        Args:
            text: 原始文本。

        Returns:
            特征字符串列表（含 1-gram 与 n-gram，兼顾词与上下文）。
        """
        text = text.lower()
        # 分字/分词，保留中英文与数字
        tokens = _TOKEN_RE.findall(text)
        flat = list(text)  # 字符级，保留中文单字语义
        features: list[str] = []
        for t in tokens:
            if len(t) == 1:
                features.append(t)
            else:
                features.extend(t[i : i + self.ngram] or t[i] for i in range(len(t)))
        # 去重保持稳定序
        return list(dict.fromkeys(features)) if features else flat

    def embed(self, text: str) -> list[float]:
        """把文本编码成 L2 归一化向量。

        Args:
            text: 待编码文本；空串返回空列表（不参与向量检索）。

        Returns:
            维度为 ``self.dim`` 的归一化浮点向量；空输入返回 []。
        """
        tokens = self._features(text)
        if not tokens:
            return []
        vec = [0.0] * self.dim
        for tok in tokens:
            h = hashlib.md5(tok.encode("utf-8")).digest()
            bucket = int.from_bytes(h[:4], "little") % self.dim
            vec[bucket] += 1.0
        # L2 归一化（零范数返回零向量，避免除零；调用方会忽略零向量）
        norm = math.sqrt(sum(v * v for v in vec))
        if norm <= 0:
            return vec
        return [v / norm for v in vec]


_global_embedder = HashingEmbedder()


def embed_text(text: str, dim: int = DEFAULT_DIM) -> list[float]:
    """便捷函数：用全局默认嵌入器把文本编码成向量。

    Args:
        text: 待编码文本。
        dim: 向量维度。

    Returns:
        归一化向量；空文本返回空列表。
    """
    if not text:
        return []
    if dim == _global_embedder.dim:
        return _global_embedder.embed(text)
    return HashingEmbedder(dim=dim).embed(text)


def embed_texts(texts: list[str], dim: int = DEFAULT_DIM) -> list[list[float]]:
    """批量编码多段文本为向量。

    Args:
        texts: 待编码文本列表。
        dim: 向量维度。

    Returns:
        与输入等长的向量列表（空文本对应空列表）。
    """
    return [embed_text(t, dim=dim) for t in texts]