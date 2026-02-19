import { App, Modal } from "obsidian";
import type { GomPublishFlowResult } from "../gom-flow";

export class GateResultsModal extends Modal {
  private readonly result: GomPublishFlowResult;

  constructor(app: App, result: GomPublishFlowResult) {
    super(app);
    this.result = result;
  }

  onOpen(): void {
    this.setTitle("Mind Lite: GOM Gate Results");

    const { contentEl } = this;
    contentEl.empty();

    const draftIdEl = document.createElement("p");
    draftIdEl.textContent = `Draft: ${this.result.draftId}`;
    contentEl.appendChild(draftIdEl);

    const gateEl = document.createElement("p");
    gateEl.textContent = `Gate passed: ${this.result.gatePassed ? "yes" : "no"}`;
    contentEl.appendChild(gateEl);

    const stageEl = document.createElement("p");
    stageEl.textContent = `Stage: ${this.result.stage}`;
    contentEl.appendChild(stageEl);

    if (this.result.markStatus != null) {
      const markEl = document.createElement("p");
      markEl.textContent = `Mark status: ${this.result.markStatus}`;
      contentEl.appendChild(markEl);
    }

    if (this.result.hardFailReasons.length > 0) {
      const reasonsEl = document.createElement("p");
      reasonsEl.textContent = `Hard fail reasons: ${this.result.hardFailReasons.join(", ")}`;
      contentEl.appendChild(reasonsEl);
    }

    if (this.result.recommendedActions.length > 0) {
      const actionsEl = document.createElement("p");
      actionsEl.textContent = `Recommended actions: ${this.result.recommendedActions.join(", ")}`;
      contentEl.appendChild(actionsEl);
    }

    const diagnosticsTitleEl = document.createElement("p");
    diagnosticsTitleEl.textContent = "Diagnostics:";
    contentEl.appendChild(diagnosticsTitleEl);

    const diagnosticsEl = document.createElement("ul");
    contentEl.appendChild(diagnosticsEl);

    for (const item of this.result.diagnostics) {
      const rowEl = document.createElement("li");
      rowEl.textContent = `${item.stage}: ${item.ok ? "ok" : "failed"} - ${item.detail}`;
      diagnosticsEl.appendChild(rowEl);
    }
  }
}
