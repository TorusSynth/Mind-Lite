import { Notice, Plugin } from "obsidian";
import { apiGet, apiPost } from "./api/client";
import { LinksReviewModal } from "./features/links/modals/LinksReviewModal";
import {
  applyLinks,
  parseCandidateNoteIds,
  parseMinimumConfidence,
  parseSourceNoteId,
  proposeLinks,
  type LinkProposal
} from "./features/links/propose-links";
import { analyzeFolder } from "./features/onboarding/analyze-folder";
import { RunStatusModal } from "./features/onboarding/modals/RunStatusModal";
import { ReviewModal } from "./features/organize/modals/ReviewModal";
import { registerAnalyzeFolderCommand } from "./features/onboarding/analyze-folder";
import { normalizePublishStage, prepareDraftForGom, runGomGateFlow } from "./features/publish/gom-flow";
import { GateResultsModal } from "./features/publish/modals/GateResultsModal";
import { PrepareModal } from "./features/publish/modals/PrepareModal";
import { getLastRunId, setLastRunId } from "./features/runs/history";
import { parseRunHistoryEntries, RunHistoryModal } from "./features/runs/modals/RunHistoryModal";
import { RollbackModal } from "./features/runs/modals/RollbackModal";
import { createErrorText } from "./modals/base";
import type { JSONValue } from "./types/api";

type PromptFn = (message?: string, defaultValue?: string) => string | null;

function getPromptFn(): PromptFn | undefined {
  return (globalThis as typeof globalThis & { prompt?: PromptFn }).prompt;
}

function resolveDailyTriageFolder(plugin: Plugin): string | null {
  const workspace = plugin.app.workspace as
    | {
        getActiveFile?: () => { parent?: { path?: string } } | null;
      }
    | undefined;
  const activeFolderPath = workspace?.getActiveFile?.()?.parent?.path?.trim();
  if (activeFolderPath != null && activeFolderPath.length > 0) {
    return activeFolderPath;
  }

  const adapter = plugin.app.vault.adapter as { basePath?: string } | undefined;
  const basePath = adapter?.basePath?.trim();
  return basePath != null && basePath.length > 0 ? basePath : null;
}

export default class MindLitePlugin extends Plugin {
  private lastLinkSourceNoteId: string | null = null;
  private lastLinkSuggestions: LinkProposal[] = [];
  private hasFreshLinkSuggestions = false;

  private clearLinkSuggestionsCache(): void {
    this.lastLinkSourceNoteId = null;
    this.lastLinkSuggestions = [];
    this.hasFreshLinkSuggestions = false;
  }

  private hasValidLinkSuggestionsCache(): boolean {
    return this.hasFreshLinkSuggestions && this.lastLinkSourceNoteId != null && this.lastLinkSuggestions.length > 0;
  }

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
          try {
            await apiPost<Record<string, never>, Record<string, never>>(`/runs/${runId}/approve`, {});
          } catch {
            // Allow apply retries when approval already happened.
          }

          await apiPost<Record<string, never>, Record<string, never>>(`/runs/${runId}/apply`, {});
          new Notice("Mind Lite approved and applied proposals.");
        } catch (applyError) {
          new Notice(createErrorText(applyError));
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
        this.clearLinkSuggestionsCache();

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
          this.hasFreshLinkSuggestions = true;
          new LinksReviewModal(this.app, result.suggestions).open();
        } catch (error) {
          this.clearLinkSuggestionsCache();
          new Notice(createErrorText(error));
        }
      }
    });

    this.addCommand({
      id: "mind-lite-apply-links",
      name: "Mind Lite: Apply Links",
      callback: async () => {
        if (!this.hasValidLinkSuggestionsCache()) {
          new Notice("No fresh link suggestions available. Run Propose Links first.");
          return;
        }

        const prompt = getPromptFn();
        const rawMinimumConfidence = prompt?.("Minimum confidence (0-1, optional)", "");

        if (rawMinimumConfidence == null) {
          return;
        }

        try {
          const minimumConfidence = parseMinimumConfidence(rawMinimumConfidence);
          await applyLinks(this.lastLinkSourceNoteId!, this.lastLinkSuggestions, minimumConfidence);
          new Notice("Mind Lite applied links.");
        } catch (error) {
          new Notice(createErrorText(error));
        }
      }
    });

    this.addCommand({
      id: "mind-lite-daily-triage",
      name: "Mind Lite: Daily Triage",
      callback: async () => {
        const folderPath = resolveDailyTriageFolder(this);
        if (folderPath == null) {
          new Notice("Mind Lite could not detect an active folder for daily triage.");
          return;
        }

        try {
          const result = await analyzeFolder(folderPath);
          setLastRunId(result.run_id);
          new RunStatusModal(this.app, result).open();
          new Notice(`Mind Lite daily triage complete: ${result.run_id} (${result.state})`);
        } catch (error) {
          new Notice(createErrorText(error));
        }
      }
    });

    this.addCommand({
      id: "mind-lite-weekly-deep-review",
      name: "Mind Lite: Weekly Deep Review",
      callback: async () => {
        try {
          const response = await apiGet<JSONValue>("/runs");
          const runs = parseRunHistoryEntries(response);
          new RunHistoryModal(this.app, runs).open();
        } catch (error) {
          new Notice(createErrorText(error));
        }
      }
    });

    this.addCommand({
      id: "mind-lite-publish-to-gom",
      name: "Mind Lite: Publish to GOM",
      callback: async () => {
        const prompt = getPromptFn();
        const draftId = prompt?.("Draft id", "");
        if (draftId == null) {
          return;
        }

        const content = prompt?.("Content", "");
        if (content == null) {
          return;
        }

        const target = prompt?.("Target", "gom") ?? "gom";
        const normalizedTarget = target.trim().length > 0 ? target.trim() : "gom";
        const rawStage = prompt?.("Stage (seed|sprout|tree)", "seed") ?? "seed";
        const stage = normalizePublishStage(rawStage);

        try {
          const payload = {
            draft_id: draftId,
            content,
            target: normalizedTarget
          };
          const prepared = await prepareDraftForGom(payload);
          new PrepareModal(this.app, payload, prepared.prepared_content, prepared.sanitized === true, stage, async (selectedStage) => {
            const flowResult = await runGomGateFlow(prepared, selectedStage);
            new GateResultsModal(this.app, flowResult).open();
          }).open();
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
