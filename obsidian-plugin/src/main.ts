import { Notice, Plugin } from "obsidian";
import { registerAnalyzeFolderCommand } from "./features/onboarding/analyze-folder";

export default class MindLitePlugin extends Plugin {
  async onload(): Promise<void> {
    registerAnalyzeFolderCommand(this);

    this.addCommand({
      id: "mind-lite-ping",
      name: "Mind Lite: Ping",
      callback: () => {
        new Notice("Mind Lite ping");
      }
    });
  }
}
