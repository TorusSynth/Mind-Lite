import { Notice, Plugin } from "obsidian";

export default class MindLitePlugin extends Plugin {
  async onload(): Promise<void> {
    this.addCommand({
      id: "mind-lite-ping",
      name: "Mind Lite: Ping",
      callback: () => {
        new Notice("Mind Lite ping");
      }
    });
  }
}
