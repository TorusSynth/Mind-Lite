import { App, Modal } from "obsidian";
import type { AnalyzeFolderResponse } from "../analyze-folder";

export class RunStatusModal extends Modal {
  private readonly result: AnalyzeFolderResponse;

  constructor(app: App, result: AnalyzeFolderResponse) {
    super(app);
    this.result = result;
  }

  onOpen(): void {
    this.setTitle("Mind Lite: Analyze Run Status");

    const { contentEl } = this;
    contentEl.empty();

    const runIdEl = document.createElement("p");
    runIdEl.textContent = `Run ID: ${this.result.run_id}`;
    contentEl.appendChild(runIdEl);

    const stateEl = document.createElement("p");
    stateEl.textContent = `State: ${this.result.state}`;
    contentEl.appendChild(stateEl);

    const countsTitleEl = document.createElement("p");
    countsTitleEl.textContent = "Proposal counts:";
    contentEl.appendChild(countsTitleEl);

    const counts = this.result.proposal_counts ?? {};
    const entries = Object.entries(counts);

    if (entries.length === 0) {
      const emptyEl = document.createElement("p");
      emptyEl.textContent = "No proposal counts returned.";
      contentEl.appendChild(emptyEl);
      return;
    }

    const listEl = document.createElement("ul");
    contentEl.appendChild(listEl);

    for (const [key, value] of entries) {
      const itemEl = document.createElement("li");
      itemEl.textContent = `${key}: ${value}`;
      listEl.appendChild(itemEl);
    }
  }
}
