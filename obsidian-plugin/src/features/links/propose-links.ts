import { apiPost } from "../../api/client";
import type { JSONObject, JSONValue } from "../../types/api";

export type LinkProposal = {
  source?: string;
  target?: string;
  confidence?: number;
} & JSONObject;

function asLinkProposalArray(value: JSONValue): LinkProposal[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value.filter((item): item is LinkProposal => {
    return typeof item === "object" && item !== null && !Array.isArray(item);
  });
}

function getConfidence(value: JSONValue | undefined): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

export function sortLinkProposalsByConfidenceDesc(proposals: LinkProposal[]): LinkProposal[] {
  return [...proposals].sort((left, right) => {
    return getConfidence(right.confidence) - getConfidence(left.confidence);
  });
}

export async function proposeLinks(): Promise<LinkProposal[]> {
  const response = await apiPost<Record<string, never>, JSONValue>("/links/propose", {});
  return sortLinkProposalsByConfidenceDesc(asLinkProposalArray(response));
}

export function parseMinimumConfidence(raw: string): number | null {
  const trimmed = raw.trim();

  if (trimmed.length === 0) {
    return null;
  }

  const parsed = Number(trimmed);
  if (!Number.isFinite(parsed) || parsed < 0 || parsed > 1) {
    throw new Error("Minimum confidence must be a number between 0 and 1.");
  }

  return parsed;
}

export async function applyLinks(minimumConfidence: number | null): Promise<void> {
  const payload: JSONObject = {};
  if (minimumConfidence != null) {
    payload.minimum_confidence = minimumConfidence;
  }

  await apiPost<JSONObject, JSONObject>("/links/apply", payload);
}
