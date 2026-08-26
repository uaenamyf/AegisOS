// date: 2026-07-05
// dev: Claude Code (glm-5.2)
// changelog: 前端命名对齐后端——从 mappers/apimappers/ 迁移至 lib/api-client/（对应后端 core/ 网关职责）

import { config } from "@/config";
import type { ApiError } from "@/protocol/frontend-types";

function baseUrl(): string {
  return config.apiBaseUrl;
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
    [config.apiKeyHeader]: config.apiKey,
  };
  try {
    const trace = localStorage.getItem("aegis.trace_id");
    const session = localStorage.getItem("aegis.session_id");
    if (trace) headers[config.traceHeader] = trace;
    if (session) headers[config.sessionHeader] = session;
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
