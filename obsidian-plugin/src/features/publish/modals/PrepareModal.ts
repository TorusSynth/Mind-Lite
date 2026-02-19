import { App, Modal } from "obsidian";
import { normalizePublishStage, type PublishPreparePayload, type PublishStage } from "../gom-flow";

type OnContinue = (stage: PublishStage) => void | Promise<void>;

export class PrepareModal extends Modal {
  private readonly payload: PublishPreparePayload;
  private readonly preparedContent: string;
  private readonly sanitized: boolean;
  private readonly initialStage: PublishStage;
  private readonly onContinue: OnContinue;

  constructor(
    app: App,
    payload: PublishPreparePayload,
    preparedContent: string,
    sanitized: boolean,
    initialStage: PublishStage,
    onContinue: OnContinue
  ) {
    super(app);
    this.payload = payload;
    this.preparedContent = preparedContent;
    this.sanitized = sanitized;
    this.initialStage = initialStage;
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

    const stageLabelEl = document.createElement("p");
    stageLabelEl.textContent = "Stage (seed|sprout|tree):";
    contentEl.appendChild(stageLabelEl);

    const stageInputEl = document.createElement("input");
    stageInputEl.type = "text";
    stageInputEl.value = this.initialStage;
    stageInputEl.placeholder = "seed";
    contentEl.appendChild(stageInputEl);

    const continueButtonEl = document.createElement("button");
    continueButtonEl.type = "button";
    continueButtonEl.textContent = "Continue";
    continueButtonEl.onclick = () => {
      void this.onContinue(normalizePublishStage(stageInputEl.value));
      this.close();
    };
    contentEl.appendChild(continueButtonEl);
  }
}
