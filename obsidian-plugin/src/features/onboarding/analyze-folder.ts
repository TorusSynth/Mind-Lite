import type { Plugin } from "obsidian";
import { apiPost } from "../../api/client";
import { AnalyzeModal } from "./modals/AnalyzeModal";
import { RunStatusModal } from "./modals/RunStatusModal";

export type ProposalCounts = Record<string, number>;

export type AnalyzeFolderResponse = {
  run_id: string;
  state: string;
  proposal_counts?: ProposalCounts;
};

type AnalyzeFolderRequest = {
  folder_path: string;
  mode: "analyze";
};

export async function analyzeFolder(folderPath: string): Promise<AnalyzeFolderResponse> {
  return apiPost<AnalyzeFolderRequest, AnalyzeFolderResponse>("/onboarding/analyze-folder", {
    folder_path: folderPath,
    mode: "analyze"
  });
}

function resolveDefaultFolderPath(plugin: Plugin): string {
  const adapter = plugin.app.vault.adapter as { basePath?: string };
  const basePath = adapter.basePath?.trim();
  return basePath && basePath.length > 0 ? basePath : ".";
}

export function registerAnalyzeFolderCommand(plugin: Plugin): void {
  plugin.addCommand({
    id: "mind-lite-analyze-folder",
    name: "Mind Lite: Analyze Folder",
    callback: () => {
      const modal = new AnalyzeModal(
        plugin.app,
        resolveDefaultFolderPath(plugin),
        analyzeFolder,
        (result) => {
          new RunStatusModal(plugin.app, result).open();
        }
      );

      modal.open();
    }
  });
}
