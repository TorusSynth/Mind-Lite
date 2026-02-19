import { Notice, Plugin } from "obsidian";
import { apiPost } from "./api/client";
import { LinksReviewModal } from "./features/links/modals/LinksReviewModal";
import {
  applyLinks,
  parseCandidateNoteIds,
  parseMinimumConfidence,
  parseSourceNoteId,
  proposeLinks,
  type LinkProposal
} from "./features/links/propose-links";
import { ReviewModal } from "./features/organize/modals/ReviewModal";
import { registerAnalyzeFolderCommand } from "./features/onboarding/analyze-folder";
import { getLastRunId } from "./features/runs/history";
import { RollbackModal } from "./features/runs/modals/RollbackModal";
import { createErrorText } from "./modals/base";

type PromptFn = (message?: string, defaultValue?: string) => string | null;

function getPromptFn(): PromptFn | undefined {
  return (globalThis as typeof globalThis & { prompt?: PromptFn }).prompt;
}

export default class MindLitePlugin extends Plugin {
  private lastLinkSourceNoteId: string | null = null;
  private lastLinkSuggestions: LinkProposal[] = [];

  async onload(): Promise<void> {
    registerAnalyzeFolderCommand(this);

    this.addCommand({
      id: "mind-lite-review-proposals",
      name: "Mind Lite: Review Proposals",
      callback: () => {
        const runId = getLastRunId();

        if (runId == null) {
          new Notice("Mind Lite has no recent run to review.");
          return;
        }

        new ReviewModal(this.app, runId).open();
      }
    });

    this.addCommand({
      id: "mind-lite-apply-approved",
      name: "Mind Lite: Apply Approved",
      callback: async () => {
        const runId = getLastRunId();

        if (runId == null) {
          new Notice("Mind Lite has no recent run to apply.");
          return;
        }

        try {
          await apiPost<Record<string, never>, Record<string, never>>(`/runs/${runId}/apply`, {});
          new Notice("Mind Lite applied approved proposals.");
        } catch (error) {
          new Notice(createErrorText(error));
        }
      }
    });

    this.addCommand({
      id: "mind-lite-rollback-last-batch",
      name: "Mind Lite: Rollback Last Batch",
      callback: () => {
        const runId = getLastRunId();

        if (runId == null) {
          new Notice("Mind Lite has no recent run to roll back.");
          return;
        }

        new RollbackModal(this.app, runId, async (targetRunId) => {
          await apiPost<Record<string, never>, Record<string, never>>(`/runs/${targetRunId}/rollback`, {});
        }).open();
      }
    });

    this.addCommand({
      id: "mind-lite-propose-links",
      name: "Mind Lite: Propose Links",
      callback: async () => {
        const prompt = getPromptFn();
        const rawSourceNoteId = prompt?.("Source note id", "");
        if (rawSourceNoteId == null) {
          return;
        }

        const rawCandidateNoteIds = prompt?.("Candidate note ids (comma-separated)", "");
        if (rawCandidateNoteIds == null) {
          return;
        }

        try {
          const sourceNoteId = parseSourceNoteId(rawSourceNoteId);
          const candidateNotes = parseCandidateNoteIds(rawCandidateNoteIds);
          const result = await proposeLinks(sourceNoteId, candidateNotes);
          this.lastLinkSourceNoteId = result.sourceNoteId;
          this.lastLinkSuggestions = result.suggestions;
          new LinksReviewModal(this.app, result.suggestions).open();
        } catch (error) {
          new Notice(createErrorText(error));
        }
      }
    });

    this.addCommand({
      id: "mind-lite-apply-links",
      name: "Mind Lite: Apply Links",
      callback: async () => {
        if (this.lastLinkSourceNoteId == null || this.lastLinkSuggestions.length === 0) {
          new Notice("Propose links first to collect suggestions.");
          return;
        }

        const prompt = getPromptFn();
        const rawMinimumConfidence = prompt?.("Minimum confidence (0-1, optional)", "");

        if (rawMinimumConfidence == null) {
          return;
        }

        try {
          const minimumConfidence = parseMinimumConfidence(rawMinimumConfidence);
          await applyLinks(this.lastLinkSourceNoteId, this.lastLinkSuggestions, minimumConfidence);
          new Notice("Mind Lite applied links.");
        } catch (error) {
          new Notice(createErrorText(error));
        }
      }
    });

    this.addCommand({
      id: "mind-lite-ping",
      name: "Mind Lite: Ping",
      callback: () => {
        new Notice("Mind Lite ping");
      }
    });
  }
}
