import { apiGet, apiPost, apiDelete } from "../../api/client";
import type { JSONValue } from "../../types/api";

export interface ModelInfo {
  id: string;
  name: string;
  context: number;
  provider: string;
}

export interface LlmConfig {
  active_provider: string;
  active_model: string;
  has_openrouter_key: boolean;
  lmstudio_url: string;
  recently_used: Array<{ provider: string; model: string }>;
}

export interface ModelsCatalog {
  free: ModelInfo[];
  local: ModelInfo[];
  smart: ModelInfo[];
}

function parseModelsCatalog(data: JSONValue): ModelsCatalog {
  const models = data as Record<string, JSONValue[]>;
  return {
    free: (models.free || []).map(parseModelInfo),
    local: (models.local || []).map(parseModelInfo),
    smart: (models.smart || []).map(parseModelInfo),
  };
}

function parseModelInfo(data: JSONValue): ModelInfo {
  const m = data as Record<string, JSONValue>;
  return {
    id: m.id as string,
    name: m.name as string,
    context: m.context as number,
    provider: m.provider as string,
  };
}

function parseLlmConfig(data: JSONValue): LlmConfig {
  const c = data as Record<string, JSONValue>;
  return {
    active_provider: c.active_provider as string,
    active_model: c.active_model as string,
    has_openrouter_key: c.has_openrouter_key as boolean,
    lmstudio_url: c.lmstudio_url as string,
    recently_used: (c.recently_used || []) as Array<{ provider: string; model: string }>,
  };
}

export async function fetchModelsCatalog(): Promise<ModelsCatalog> {
  const response = await apiGet<JSONValue>("/llm/models");
  return parseModelsCatalog(response);
}

export async function fetchLlmConfig(): Promise<LlmConfig> {
  const response = await apiGet<JSONValue>("/llm/config");
  return parseLlmConfig(response);
}

export async function setModel(provider: string, model: string): Promise<void> {
  await apiPost("/llm/config", { provider, model });
}

export async function setOpenRouterApiKey(apiKey: string): Promise<void> {
  await apiPost("/llm/config/api-key", { api_key: apiKey });
}

export async function clearOpenRouterApiKey(): Promise<void> {
  await apiDelete("/llm/config/api-key");
}

export function formatModelName(model: ModelInfo): string {
  const contextK = Math.round(model.context / 1000);
  return `${model.name} (${contextK}K ctx)`;
}
