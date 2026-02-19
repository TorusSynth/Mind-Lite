import { App, Modal } from "obsidian";
import { setSecondaryAction } from "../../../modals/base";
import { sortLinkProposalsByConfidenceDesc, type LinkProposal } from "../propose-links";

function asLabelPart(value: unknown, fallback: string): string {
  if (typeof value !== "string") {
    return fallback;
  }

  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : fallback;
}

function formatConfidence(value: unknown): string {
  return typeof value === "number" && Number.isFinite(value) ? value.toFixed(2) : "0.00";
}

export class LinksReviewModal extends Modal {
  private readonly proposals: LinkProposal[];

  constructor(app: App, proposals: LinkProposal[]) {
    super(app);
    this.proposals = sortLinkProposalsByConfidenceDesc(proposals);
  }

  onOpen(): void {
    this.setTitle("Mind Lite: Link Proposals");

    const { contentEl } = this;
    contentEl.empty();

    if (this.proposals.length === 0) {
      const emptyEl = document.createElement("p");
      emptyEl.textContent = "No link proposals returned.";
      contentEl.appendChild(emptyEl);
      return;
    }

    const listEl = document.createElement("ul");
    contentEl.appendChild(listEl);

    for (const proposal of this.proposals) {
      const itemEl = document.createElement("li");
      const target = asLabelPart(proposal.target_note_id, "(unknown)");
      const reason = asLabelPart(proposal.reason, "unspecified_reason");
      itemEl.textContent = `${target} (${formatConfidence(proposal.confidence)}) - ${reason}`;
      listEl.appendChild(itemEl);
    }

    const closeButtonEl = document.createElement("button");
    contentEl.appendChild(closeButtonEl);
    setSecondaryAction(closeButtonEl, "Close", () => {
      this.close();
    });
  }
}
