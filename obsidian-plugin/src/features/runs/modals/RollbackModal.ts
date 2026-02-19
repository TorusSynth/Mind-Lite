import { App, Modal, Notice } from "obsidian";
import { createErrorText, setPrimaryAction, setSecondaryAction } from "../../../modals/base";

type ExecuteRollback = (runId: string) => Promise<void>;

export class RollbackModal extends Modal {
  private readonly runId: string;
  private readonly executeRollback: ExecuteRollback;

  constructor(app: App, runId: string, executeRollback: ExecuteRollback) {
    super(app);
    this.runId = runId;
    this.executeRollback = executeRollback;
  }

  onOpen(): void {
    this.setTitle("Mind Lite: Rollback Last Batch");

    const { contentEl } = this;
    contentEl.empty();

    const descriptionEl = document.createElement("p");
    descriptionEl.textContent = `Rollback the last applied batch for run ${this.runId}?`;
    contentEl.appendChild(descriptionEl);

    const errorEl = document.createElement("p");
    contentEl.appendChild(errorEl);

    const actionsEl = document.createElement("div");
    contentEl.appendChild(actionsEl);

    const cancelButtonEl = document.createElement("button");
    const rollbackButtonEl = document.createElement("button");
    actionsEl.append(cancelButtonEl, rollbackButtonEl);

    setSecondaryAction(cancelButtonEl, "Cancel", () => {
      this.close();
    });

    setPrimaryAction(rollbackButtonEl, "Rollback", async () => {
      try {
        await this.executeRollback(this.runId);
        new Notice("Mind Lite rolled back the last batch.");
        this.close();
      } catch (error) {
        errorEl.textContent = createErrorText(error);
      }
    });
  }
}
