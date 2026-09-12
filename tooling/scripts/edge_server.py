#!/usr/bin/env python3
# date: 2026-08-27
# dev: ox-alpha
"""AegisOS 极简边缘推理服务（stdlib 零依赖，scp 到服务器即跑）。

职责：
    - 接收推理请求（POST /infer）并返回结果；
    - 健康检查（GET /health），暴露在线状态与缓存统计；
    - 区域聚合缓存：同 prompt+model 在 TTL 内命中直接返回缓存结果，
      体现"边缘层区域聚合"的差异化能力。

启动方式：
    python edge_server.py --port 8900
    python edge_server.py --port 8900 --ollama-model qwen2.5:7b  # 有 Ollama 时

协议：
    POST /infer  body: {"prompt": str, "system": str?, "temperature": float?,
                          "max_tokens": int?}
                 resp: {"ok": bool, "text": str, "tier": "edge",
                        "usage": {"prompt_tokens": int, "completion_tokens": int},
                        "cached": bool}

    GET /health   resp: {"status": "ok", "cache_size": int}
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

# ---- 缓存 ----

_cache: dict[str, tuple[float, dict]] = {}
CACHE_TTL = 60.0  # 秒


def _cache_key(prompt: str, model: str) -> str:
    return hashlib.sha256(f"{prompt}|{model}".encode()).hexdigest()[:16]


def _cache_prune() -> None:
    now = time.time()
    expired = [k for k, (ts, _) in _cache.items() if now - ts > CACHE_TTL]
    for k in expired:
        del _cache[k]


# ---- 推理 ----

def _estimate_tokens(text: str) -> int:
    """粗略 token 估算：中文字按 1.5 token/字，英文按 1 token/4 字符。"""
    chars = len(text)
    chinese = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
    return int(chinese * 1.5 + (chars - chinese) * 0.25)


def _mock_infer(prompt: str, system: str) -> dict:
    """本地 mock 推理：无 Ollama 时返回固定短语（保证联调可跑）。"""
    reply = (
        f"[边缘服务·本地模式] 收到推理请求。"
        f"前端提示={system[:30] if system else '无'}，"
        f"用户输入={prompt[:50]}。"
        f"本边缘节点当前运行在 mock 模式，未连接 Ollama。"
    )
    return {
        "ok": True,
        "text": reply,
        "tier": "edge",
        "usage": {
            "prompt_tokens": _estimate_tokens(prompt),
            "completion_tokens": _estimate_tokens(reply),
        },
        "cached": False,
    }


def _aggregate_results(results: list[dict]) -> dict:
    """区域聚合：合并多条推理结果，产出汇总摘要。"""
    ok_count = sum(1 for r in results if r["ok"])
    total_prompt = sum(r["usage"]["prompt_tokens"] for r in results)
    total_completion = sum(r["usage"]["completion_tokens"] for r in results)
    cached_count = sum(1 for r in results if r.get("cached"))

    texts = [r["text"] for r in results if r["ok"]]
    summary = (
        f"[边缘区域聚合] 共接收 {len(results)} 条子请求，"
        f"成功 {ok_count} 条，缓存命中 {cached_count} 条。"
        f"汇总摘要：{' | '.join(texts[:3])}"
        f"{'...' if len(texts) > 3 else ''}"
    )

    return {
        "ok": True,
        "aggregated_text": summary,
        "tier": "edge",
        "sub_count": len(results),
        "ok_count": ok_count,
        "cached_count": cached_count,
        "usage": {
            "prompt_tokens": total_prompt,
            "completion_tokens": total_completion,
        },
        "sub_results": results,
    }


def _try_ollama_infer(prompt: str, system: str, model: str, temperature: float, max_tokens: int) -> dict | None:
    """尝试调本机 Ollama；失败返回 None。"""
    import urllib.request

    payload = {
        "model": model,
        "prompt": prompt,
        "system": system,
        "stream": False,
        "options": {"temperature": temperature, "num_predict": max_tokens},
    }
    try:
        req = urllib.request.Request(
            "http://localhost:11434/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return {
            "ok": True,
            "text": data.get("response", ""),
            "tier": "edge",
            "usage": {
                "prompt_tokens": int(data.get("prompt_eval_count", 0) or 0),
                "completion_tokens": int(data.get("eval_count", 0) or 0),
            },
            "cached": False,
        }
    except Exception:
        return None


# ---- HTTP Handler ----

class EdgeHandler(BaseHTTPRequestHandler):
    ollama_model: str = ""

    def log_message(self, fmt, *args):
        """静默日志，仅输出到 stderr。"""
        print(f"[edge_server] {fmt % args}", file=sys.stderr)

    def _send_json(self, status: int, body: dict) -> None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        if self.path == "/health":
            _cache_prune()
            self._send_json(200, {"status": "ok", "cache_size": len(_cache)})
        else:
            self._send_json(404, {"error": "not found"})

    def do_POST(self) -> None:
        # 读取请求体
        length = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(length).decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._send_json(400, {"ok": False, "error": "invalid json"})
            return

        if self.path == "/aggregate":
            self._handle_aggregate(body)
            return
        if self.path != "/infer":
            self._send_json(404, {"error": "not found"})
            return

        prompt = body.get("prompt", "")
        if not prompt:
            self._send_json(400, {"ok": False, "error": "missing prompt"})
            return

        self._send_json(200, self._infer_one(body))

    def _infer_one(self, body: dict) -> dict:
        """单条推理：区域聚合缓存 → Ollama → mock 回退。"""
        prompt = body.get("prompt", "")
        system = body.get("system", "")
        temperature = body.get("temperature", 0.7)
        max_tokens = body.get("max_tokens", 512)

        # 区域聚合缓存
        key = _cache_key(prompt, self.ollama_model)
        _cache_prune()
        if key in _cache:
            _, cached = _cache[key]
            cached["cached"] = True
            return cached

        # 尝试 Ollama → 回退 mock
        result = None
        if self.ollama_model:
            result = _try_ollama_infer(prompt, system, self.ollama_model, temperature, max_tokens)
        if result is None:
            result = _mock_infer(prompt, system)

        _cache[key] = (time.time(), result)
        return result

    def _handle_aggregate(self, body: dict) -> None:
        """区域聚合：接收多条子请求，逐条推理后合并汇总。

        body: {"prompts": [str, ...], "system": str?}
        """
        prompts = body.get("prompts", [])
        system = body.get("system", "")
        if not prompts or not isinstance(prompts, list):
            self._send_json(400, {"ok": False, "error": "missing prompts list"})
            return

        results = [self._infer_one({"prompt": p, "system": system}) for p in prompts]
        self._send_json(200, _aggregate_results(results))


# ---- 入口 ----

def main() -> None:
    parser = argparse.ArgumentParser(description="AegisOS 边缘推理服务")
    parser.add_argument("--port", type=int, default=8900, help="监听端口（默认 8900）")
    parser.add_argument(
        "--ollama-model",
        type=str,
        default=os.environ.get("AEGIS_EDGE_OLLAMA_MODEL", ""),
        help="Ollama 模型名（如 qwen2.5:7b），不设置则使用 mock 模式",
    )
    args = parser.parse_args()

    EdgeHandler.ollama_model = args.ollama_model

    server = HTTPServer(("0.0.0.0", args.port), EdgeHandler)
    mode = f"ollama:{args.ollama_model}" if args.ollama_model else "mock"
    print(f"[edge_server] listening on 0.0.0.0:{args.port} (mode={mode})", file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[edge_server] shutting down", file=sys.stderr)
        server.shutdown()


if __name__ == "__main__":
    main()
