import { apiPost } from "../../api/client";
import type { JSONObject, JSONValue } from "../../types/api";

export type LinkProposal = {
  target_note_id?: string;
  confidence?: number;
  reason?: string;
} & JSONObject;

export type CandidateNote = {
  note_id: string;
};

export type LinksProposeResult = {
  sourceNoteId: string;
  suggestions: LinkProposal[];
};

function asLinkProposalArray(value: JSONValue): LinkProposal[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value.filter((item): item is LinkProposal => {
    return typeof item === "object" && item !== null && !Array.isArray(item);
  });
}

function asLinksProposeResult(value: JSONValue): LinksProposeResult {
  if (typeof value !== "object" || value == null || Array.isArray(value)) {
    throw new Error("Invalid /links/propose response payload.");
  }

  const sourceNoteId = typeof value.source_note_id === "string" ? value.source_note_id.trim() : "";
  if (sourceNoteId.length === 0) {
    throw new Error("Invalid /links/propose response payload.");
  }

  return {
    sourceNoteId,
    suggestions: sortLinkProposalsByConfidenceDesc(asLinkProposalArray(value.suggestions))
  };
}

function getConfidence(value: JSONValue | undefined): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

export function sortLinkProposalsByConfidenceDesc(proposals: LinkProposal[]): LinkProposal[] {
  return [...proposals].sort((left, right) => {
    return getConfidence(right.confidence) - getConfidence(left.confidence);
  });
}

export function parseSourceNoteId(raw: string): string {
  const sourceNoteId = raw.trim();
  if (sourceNoteId.length === 0) {
    throw new Error("Source note id is required.");
  }

  return sourceNoteId;
}

export function parseCandidateNoteIds(raw: string): CandidateNote[] {
  const noteIds = raw
    .split(",")
    .map((item) => item.trim())
    .filter((item) => item.length > 0);

  if (noteIds.length === 0) {
    throw new Error("At least one candidate note id is required.");
  }

  return noteIds.map((noteId) => ({ note_id: noteId }));
}

export async function proposeLinks(sourceNoteId: string, candidateNotes: CandidateNote[]): Promise<LinksProposeResult> {
  const response = await apiPost<JSONObject, JSONValue>("/links/propose", {
    source_note_id: sourceNoteId,
    candidate_notes: candidateNotes
  });
  return asLinksProposeResult(response);
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

export async function applyLinks(
  sourceNoteId: string,
  links: LinkProposal[],
  minimumConfidence: number | null
): Promise<void> {
  const normalizedLinks = links
    .map((link) => {
      const targetNoteId = typeof link.target_note_id === "string" ? link.target_note_id.trim() : "";
      const confidence = typeof link.confidence === "number" && Number.isFinite(link.confidence) ? link.confidence : null;

      if (targetNoteId.length === 0 || confidence == null) {
        return null;
      }

      return {
        target_note_id: targetNoteId,
        confidence
      };
    })
    .filter((link): link is { target_note_id: string; confidence: number } => link != null);

  if (normalizedLinks.length === 0) {
    throw new Error("No valid links available to apply.");
  }

  const payload: JSONObject = {
    source_note_id: sourceNoteId,
    links: normalizedLinks
  };
  if (minimumConfidence != null) {
    payload.min_confidence = minimumConfidence;
  }

  await apiPost<JSONObject, JSONObject>("/links/apply", payload);
}
