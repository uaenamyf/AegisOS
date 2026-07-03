// @aegis-gen
// date: 2026-07-03
// dev: Claude Code (glm-5.2)
// change: 导入源拆分——前端本地类型 ApiError 改从 @/protocol/frontend-types 引入（protocol 生成器剥离前端类型）
// @aegis-gen
// date: 2026-06-27
// dev: Claude Code (glm-5.2)
// change: 新建 apimappers/client.ts，REST fetch 封装：base URL、鉴权头、错误处理

import type { ApiError } from "@/protocol/frontend-types";

const DEFAULT_BASE_URL = "http://localhost:8000/api/v1";

function baseUrl(): string {
  const env = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "";
  return env.length > 0 ? env : DEFAULT_BASE_URL;
}

function authToken(): string | null {
  try {
    return localStorage.getItem("aegis.token");
  } catch {
    return null;
  }
}

export class ApiClientError extends Error {
  readonly code: string;
  readonly trace_id?: string;
  readonly status: number;

  constructor(error: ApiError, status: number) {
    super(error.message);
    this.name = "ApiClientError";
    this.code = error.code;
    this.trace_id = error.trace_id;
    this.status = status;
  }
}

function traceHeaders(): Record<string, string> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "application/json",
    "X-API-Key": "aegis-dev-key",
  };
  try {
    const trace = localStorage.getItem("aegis.trace_id");
    const session = localStorage.getItem("aegis.session_id");
    if (trace) headers["X-Trace-Id"] = trace;
    if (session) headers["X-Session-Id"] = session;
  } catch {
    /* ignore storage errors */
  }
  const token = authToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  return headers;
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
): Promise<T> {
  const url = `${baseUrl()}${path}`;
  const init: RequestInit = {
    method,
    headers: traceHeaders(),
  };
  if (body !== undefined) {
    init.body = JSON.stringify(body);
  }

  let res: Response;
  try {
    res = await fetch(url, init);
  } catch (err) {
    throw new ApiClientError(
      { code: "network", message: (err as Error).message, trace_id: "" },
      0,
    );
  }

  if (res.status === 204) {
    return undefined as T;
  }

  const text = await res.text();
  const data = text ? JSON.parse(text) : null;

  if (!res.ok) {
    const apiErr: ApiError = data ?? {
      code: "http",
      message: `HTTP ${res.status}`,
    };
    throw new ApiClientError(apiErr, res.status);
  }

  return data as T;
}

export const apiClient = {
  get: <T>(path: string): Promise<T> => request<T>("GET", path),
  post: <T>(path: string, body?: unknown): Promise<T> =>
    request<T>("POST", path, body),
  put: <T>(path: string, body?: unknown): Promise<T> =>
    request<T>("PUT", path, body),
  del: <T>(path: string): Promise<T> => request<T>("DELETE", path),
  baseUrl,
};

export type ApiClient = typeof apiClient;
