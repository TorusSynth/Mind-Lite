import type { JSONObject, JSONValue } from "../types/api";

const API_BASE_URL = "http://localhost:8000";

export class APIError extends Error {
  readonly status: number;

  constructor(status: number) {
    super(`API request failed with status ${status}`);
    this.name = "APIError";
    this.status = status;
  }
}

async function request<TResponse extends JSONValue>(
  method: "GET" | "POST",
  path: string,
  body?: JSONObject
): Promise<TResponse> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined
  });

  if (!response.ok) {
    throw new APIError(response.status);
  }

  const json = (await response.json()) as TResponse;

  return json;
}

export async function apiGet<TResponse extends JSONValue>(path: string): Promise<TResponse> {
  return request<TResponse>("GET", path);
}

export async function apiPost<TRequest extends JSONObject, TResponse extends JSONValue>(
  path: string,
  payload: TRequest
): Promise<TResponse> {
  return request<TResponse>("POST", path, payload);
}
