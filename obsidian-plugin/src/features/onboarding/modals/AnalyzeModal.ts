import { App, Modal } from "obsidian";
import { setPrimaryAction, setSecondaryAction, showError, showLoading } from "../../../modals/base";
import type { AnalyzeFolderResponse } from "../analyze-folder";

type AnalyzeFolderHandler = (folderPath: string) => Promise<AnalyzeFolderResponse>;
type AnalyzeSuccessHandler = (result: AnalyzeFolderResponse) => void;

export class AnalyzeModal extends Modal {
  private readonly defaultFolderPath: string;
  private readonly runAnalyze: AnalyzeFolderHandler;
  private readonly onAnalyzeSuccess: AnalyzeSuccessHandler;

  constructor(
    app: App,
    defaultFolderPath: string,
    runAnalyze: AnalyzeFolderHandler,
    onAnalyzeSuccess: AnalyzeSuccessHandler
  ) {
    super(app);
    this.defaultFolderPath = defaultFolderPath;
    this.runAnalyze = runAnalyze;
    this.onAnalyzeSuccess = onAnalyzeSuccess;
  }

  onOpen(): void {
    this.setTitle("Mind Lite: Analyze Folder");

    const { contentEl } = this;
    contentEl.empty();

    const descriptionEl = document.createElement("p");
    descriptionEl.textContent = "Choose a folder path to analyze.";
    contentEl.appendChild(descriptionEl);

    const inputEl = document.createElement("input");
    inputEl.type = "text";
    inputEl.value = this.defaultFolderPath;
    inputEl.placeholder = this.defaultFolderPath;
    inputEl.classList.add("mind-lite-modal__input");
    contentEl.appendChild(inputEl);

    const loadingEl = document.createElement("p");
    loadingEl.classList.add("mind-lite-modal__hidden");
    contentEl.appendChild(loadingEl);

    const errorEl = document.createElement("p");
    errorEl.classList.add("mind-lite-modal__hidden");
    contentEl.appendChild(errorEl);

    const actionsEl = document.createElement("div");
    contentEl.appendChild(actionsEl);

    const cancelButtonEl = document.createElement("button");
    const analyzeButtonEl = document.createElement("button");
    actionsEl.append(cancelButtonEl, analyzeButtonEl);

    setSecondaryAction(cancelButtonEl, "Cancel", () => {
      this.close();
    });

    setPrimaryAction(analyzeButtonEl, "Analyze", async () => {
      const folderPath = inputEl.value.trim() || this.defaultFolderPath;
      showError(errorEl, null);
      showLoading(loadingEl, true, "Analyzing folder...");

      try {
        const result = await this.runAnalyze(folderPath);
        this.close();
        this.onAnalyzeSuccess(result);
      } catch (error) {
        showError(errorEl, error);
      } finally {
        showLoading(loadingEl, false);
      }
    });
  }
}
