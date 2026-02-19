import { App, Modal } from "obsidian";
import type { JSONValue } from "../../../types/api";

export type RunHistoryEntry = {
  runId: string;
  state: string;
};

function normalizeText(value: unknown, fallback: string): string {
  if (typeof value !== "string") {
    return fallback;
  }

  const cleaned = value.trim();
  return cleaned.length > 0 ? cleaned : fallback;
}

export function parseRunHistoryEntries(value: JSONValue): RunHistoryEntry[] {
  const runs =
    typeof value === "object" && value != null && !Array.isArray(value)
      ? (value.runs as JSONValue)
      : value;

  if (!Array.isArray(runs)) {
    return [];
  }

  const entries: RunHistoryEntry[] = [];

  for (const item of runs) {
    if (typeof item !== "object" || item == null || Array.isArray(item)) {
      continue;
    }

    entries.push({
      runId: normalizeText(item.run_id, "(no id)"),
      state: normalizeText(item.state, "unknown")
    });
  }

  return entries;
}

export class RunHistoryModal extends Modal {
  private readonly runs: RunHistoryEntry[];
  private selectedState: string | null = null;

  constructor(app: App, runs: RunHistoryEntry[]) {
    super(app);
    this.runs = runs;
  }

  onOpen(): void {
    this.setTitle("Mind Lite: Weekly Deep Review");

    const { contentEl } = this;
    contentEl.empty();

    if (this.runs.length === 0) {
      const emptyEl = document.createElement("p");
      emptyEl.textContent = "No runs returned.";
      contentEl.appendChild(emptyEl);
      return;
    }

    const filterButtonsEl = document.createElement("div");
    contentEl.appendChild(filterButtonsEl);

    const listEl = document.createElement("ul");
    contentEl.appendChild(listEl);

    const stateCounts = new Map<string, number>();
    for (const run of this.runs) {
      stateCounts.set(run.state, (stateCounts.get(run.state) ?? 0) + 1);
    }

    const renderList = () => {
      listEl.empty();

      const visibleRuns =
        this.selectedState == null
          ? this.runs
          : this.runs.filter((run) => run.state === this.selectedState);

      for (const run of visibleRuns) {
        const itemEl = document.createElement("li");
        itemEl.textContent = `${run.runId} - ${run.state}`;
        listEl.appendChild(itemEl);
      }
    };

    const addFilterButton = (label: string, state: string | null) => {
      const buttonEl = document.createElement("button");
      buttonEl.type = "button";
      buttonEl.textContent = label;
      buttonEl.onclick = () => {
        this.selectedState = state;
        renderList();
      };
      filterButtonsEl.appendChild(buttonEl);
    };

    addFilterButton(`All (${this.runs.length})`, null);
    for (const [state, count] of stateCounts.entries()) {
      addFilterButton(`${state} (${count})`, state);
    }

    renderList();
  }
}
