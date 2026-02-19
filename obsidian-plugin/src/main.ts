import { Notice, Plugin } from "obsidian";
import { apiPost } from "./api/client";
import { ReviewModal } from "./features/organize/modals/ReviewModal";
import { registerAnalyzeFolderCommand } from "./features/onboarding/analyze-folder";
import { getLastRunId } from "./features/runs/history";
import { RollbackModal } from "./features/runs/modals/RollbackModal";
import { createErrorText } from "./modals/base";

export default class MindLitePlugin extends Plugin {
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
      id: "mind-lite-ping",
      name: "Mind Lite: Ping",
      callback: () => {
        new Notice("Mind Lite ping");
      }
    });
  }
}
