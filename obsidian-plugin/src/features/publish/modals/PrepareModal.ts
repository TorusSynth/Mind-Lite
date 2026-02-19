import { App, Modal } from "obsidian";
import type { PublishPreparePayload } from "../gom-flow";

type OnContinue = () => void | Promise<void>;

export class PrepareModal extends Modal {
  private readonly payload: PublishPreparePayload;
  private readonly preparedContent: string;
  private readonly sanitized: boolean;
  private readonly onContinue: OnContinue;

  constructor(
    app: App,
    payload: PublishPreparePayload,
    preparedContent: string,
    sanitized: boolean,
    onContinue: OnContinue
  ) {
    super(app);
    this.payload = payload;
    this.preparedContent = preparedContent;
    this.sanitized = sanitized;
    this.onContinue = onContinue;
  }

  onOpen(): void {
    this.setTitle("Mind Lite: Publish Prepare");

    const { contentEl } = this;
    contentEl.empty();

    const draftIdEl = document.createElement("p");
    draftIdEl.textContent = `Draft: ${this.payload.draft_id}`;
    contentEl.appendChild(draftIdEl);

    const targetEl = document.createElement("p");
    targetEl.textContent = `Target: ${this.payload.target}`;
    contentEl.appendChild(targetEl);

    const sanitizedEl = document.createElement("p");
    sanitizedEl.textContent = `Sanitized: ${this.sanitized ? "yes" : "no"}`;
    contentEl.appendChild(sanitizedEl);

    const previewTitleEl = document.createElement("p");
    previewTitleEl.textContent = "Prepared content:";
    contentEl.appendChild(previewTitleEl);

    const previewEl = document.createElement("pre");
    previewEl.textContent = this.preparedContent;
    contentEl.appendChild(previewEl);

    const continueButtonEl = document.createElement("button");
    continueButtonEl.type = "button";
    continueButtonEl.textContent = "Continue";
    continueButtonEl.onclick = () => {
      void this.onContinue();
      this.close();
    };
    contentEl.appendChild(continueButtonEl);
  }
}
