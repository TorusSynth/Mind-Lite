import { App, Modal, Notice, Setting } from "obsidian";
import {
  fetchModelsCatalog,
  fetchLlmConfig,
  setModel,
  setOpenRouterApiKey,
  type ModelInfo,
  type ModelsCatalog,
  type LlmConfig,
  formatModelName,
} from "../model-config";
import { createErrorText } from "../../../modals/base";

export class ModelPickerModal extends Modal {
  private catalog: ModelsCatalog | null = null;
  private config: LlmConfig | null = null;
  private selectedCategory: "free" | "local" | "smart" = "free";
  private selectedModel: ModelInfo | null = null;
  private apiKeyInput: string = "";

  constructor(app: App) {
    super(app);
  }

  async onOpen(): Promise<void> {
    const { contentEl } = this;
    contentEl.empty();
    contentEl.addClass("mind-lite-model-picker");

    contentEl.createEl("h2", { text: "LLM Model Selection" });

    await this.loadData();
    this.render();
  }

  async loadData(): Promise<void> {
    try {
      this.catalog = await fetchModelsCatalog();
      this.config = await fetchLlmConfig();
    } catch (error) {
      new Notice(createErrorText(error));
    }
  }

  render(): void {
    const { contentEl } = this;
    contentEl.empty();
    contentEl.addClass("mind-lite-model-picker");

    contentEl.createEl("h2", { text: "LLM Model Selection" });

    if (!this.catalog || !this.config) {
      contentEl.createEl("p", { text: "Loading..." });
      return;
    }

    this.renderCurrentModel();
    this.renderCategoryTabs();
    this.renderModelList();
    this.renderApiKeySection();
  }

  renderCurrentModel(): void {
    const { contentEl } = this;
    
    if (!this.config) return;

    new Setting(contentEl)
      .setName("Current Model")
      .setDesc(`${this.config.active_model} (${this.config.active_provider})`)
      .addButton((btn) => {
        btn.setButtonText("Switch Model")
          .onClick(() => {
            if (this.selectedModel) {
              this.switchModel();
            } else {
              new Notice("Select a model first");
            }
          });
      });
  }

  renderCategoryTabs(): void {
    const { contentEl } = this;

    const tabContainer = contentEl.createDiv({ cls: "mind-lite-tabs" });

    const categories: Array<"free" | "local" | "smart"> = ["free", "local", "smart"];
    const categoryNames = { free: "Free", local: "Local", smart: "Smart" };

    for (const cat of categories) {
      const tab = tabContainer.createEl("button", {
        text: categoryNames[cat],
        cls: this.selectedCategory === cat ? "mind-lite-tab-active" : "mind-lite-tab",
      });
      tab.addEventListener("click", () => {
        this.selectedCategory = cat;
        this.selectedModel = null;
        this.render();
      });
    }
  }

  renderModelList(): void {
    const { contentEl } = this;

    if (!this.catalog) return;

    const models = this.catalog[this.selectedCategory];
    const listContainer = contentEl.createDiv({ cls: "mind-lite-model-list" });

    for (const model of models) {
      const isSelected = this.selectedModel?.id === model.id;
      const isActive = this.config?.active_model === model.id;

      const item = listContainer.createDiv({
        cls: `mind-lite-model-item ${isSelected ? "selected" : ""} ${isActive ? "active" : ""}`,
      });

      item.createEl("strong", { text: model.name });
      item.createEl("span", {
        text: ` - ${Math.round(model.context / 1000)}K context`,
        cls: "mind-lite-model-context",
      });

      if (isActive) {
        item.createEl("span", { text: " (active)", cls: "mind-lite-active-tag" });
      }

      item.addEventListener("click", () => {
        this.selectedModel = model;
        this.render();
      });
    }
  }

  renderApiKeySection(): void {
    const { contentEl } = this;

    if (this.selectedCategory === "local") {
      contentEl.createEl("p", {
        text: "Local models use LM Studio. No API key required.",
        cls: "mind-lite-info",
      });
      return;
    }

    new Setting(contentEl)
      .setName("OpenRouter API Key")
      .setDesc(
        this.config?.has_openrouter_key
          ? "API key is configured"
          : "Enter your OpenRouter API key"
      )
      .addText((text) => {
        text.setPlaceholder("sk-or-...")
          .setValue(this.apiKeyInput)
          .onChange((value) => {
            this.apiKeyInput = value;
          });
      })
      .addButton((btn) => {
        btn.setButtonText("Save Key")
          .onClick(async () => {
            if (this.apiKeyInput.trim()) {
              try {
                await setOpenRouterApiKey(this.apiKeyInput.trim());
                new Notice("API key saved");
                this.apiKeyInput = "";
                await this.loadData();
                this.render();
              } catch (error) {
                new Notice(createErrorText(error));
              }
            }
          });
      });

    if (this.config?.has_openrouter_key) {
      new Setting(contentEl)
        .setName("Clear API Key")
        .addButton((btn) => {
          btn.setButtonText("Clear")
            .setWarning()
            .onClick(async () => {
              try {
                const { apiDelete } = await import("../../../api/client");
                await apiDelete("/llm/config/api-key");
                new Notice("API key cleared");
                await this.loadData();
                this.render();
              } catch (error) {
                new Notice(createErrorText(error));
              }
            });
        });
    }
  }

  async switchModel(): Promise<void> {
    if (!this.selectedModel) return;

    try {
      await setModel(this.selectedModel.provider, this.selectedModel.id);
      new Notice(`Switched to ${this.selectedModel.name}`);
      await this.loadData();
      this.render();
    } catch (error) {
      new Notice(createErrorText(error));
    }
  }

  onClose(): void {
    const { contentEl } = this;
    contentEl.empty();
  }
}
