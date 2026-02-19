import { App, Modal } from "obsidian";
import { apiGet } from "../../../api/client";
import { createErrorText } from "../../../modals/base";
import type { JSONObject, JSONPrimitive, JSONValue } from "../../../types/api";

type Proposal = {
  proposal_id?: string;
  status?: string;
  risk_tier?: string;
} & JSONObject;

type ProposalGroup = {
  key: string;
  proposals: Proposal[];
};

type LoadProposals = (runId: string) => Promise<Proposal[]>;

function asProposalArray(value: JSONValue): Proposal[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value.filter((item): item is Proposal => {
    return typeof item === "object" && item !== null && !Array.isArray(item);
  });
}

function parseProposalsResponse(value: JSONValue): Proposal[] {
  if (typeof value !== "object" || value == null || Array.isArray(value)) {
    return [];
  }

  return asProposalArray(value.proposals as JSONValue);
}

function normalizeKeyPart(value: JSONValue | undefined, fallback: string): string {
  if (typeof value !== "string") {
    return fallback;
  }

  const cleaned = value.trim();
  return cleaned.length > 0 ? cleaned : fallback;
}

export function groupProposalsByStatusAndRisk(proposals: Proposal[]): ProposalGroup[] {
  const groups = new Map<string, Proposal[]>();

  for (const proposal of proposals) {
    const status = normalizeKeyPart(proposal.status as JSONPrimitive | undefined, "unknown");
    const riskTier = normalizeKeyPart(proposal.risk_tier as JSONPrimitive | undefined, "unknown");
    const key = `${status} / ${riskTier}`;
    const existing = groups.get(key);

    if (existing == null) {
      groups.set(key, [proposal]);
      continue;
    }

    existing.push(proposal);
  }

  return Array.from(groups.entries()).map(([key, groupedProposals]) => ({
    key,
    proposals: groupedProposals
  }));
}

async function defaultLoadProposals(runId: string): Promise<Proposal[]> {
  const response = await apiGet<JSONValue>(`/runs/${runId}/proposals`);
  return parseProposalsResponse(response);
}

export class ReviewModal extends Modal {
  private readonly runId: string;
  private readonly loadProposals: LoadProposals;

  constructor(app: App, runId: string, loadProposals: LoadProposals = defaultLoadProposals) {
    super(app);
    this.runId = runId;
    this.loadProposals = loadProposals;
  }

  onOpen(): void {
    this.setTitle("Mind Lite: Review Proposals");

    const { contentEl } = this;
    contentEl.empty();

    const runIdEl = document.createElement("p");
    runIdEl.textContent = `Run ID: ${this.runId}`;
    contentEl.appendChild(runIdEl);

    const loadingEl = document.createElement("p");
    loadingEl.textContent = "Loading proposals...";
    contentEl.appendChild(loadingEl);

    const resultEl = document.createElement("div");
    contentEl.appendChild(resultEl);

    void this.renderProposals(resultEl, loadingEl);
  }

  private async renderProposals(resultEl: HTMLElement, loadingEl: HTMLElement): Promise<void> {
    try {
      const proposals = await this.loadProposals(this.runId);
      const groups = groupProposalsByStatusAndRisk(proposals);

      if (groups.length === 0) {
        const emptyEl = document.createElement("p");
        emptyEl.textContent = "No proposals returned for this run.";
        resultEl.appendChild(emptyEl);
        return;
      }

      for (const group of groups) {
        const groupTitleEl = document.createElement("p");
        groupTitleEl.textContent = `${group.key} (${group.proposals.length})`;
        resultEl.appendChild(groupTitleEl);

        const groupListEl = document.createElement("ul");
        resultEl.appendChild(groupListEl);

        for (const proposal of group.proposals) {
          const itemEl = document.createElement("li");
          itemEl.textContent = `Proposal ${proposal.proposal_id ?? "(no id)"}`;
          groupListEl.appendChild(itemEl);
        }
      }
    } catch (error) {
      const errorEl = document.createElement("p");
      errorEl.textContent = createErrorText(error);
      resultEl.appendChild(errorEl);
    } finally {
      loadingEl.textContent = "";
    }
  }
}
