import { Notice, type Plugin } from "obsidian";
import { apiPost } from "../../api/client";
import { setLastRunId } from "../runs/history";
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

function resolveDefaultFolderPath(plugin: Plugin): string | null {
  const adapter = plugin.app.vault.adapter as { basePath?: string } | undefined;
  const basePath = adapter?.basePath?.trim();
  return basePath && basePath.length > 0 ? basePath : null;
}

export function registerAnalyzeFolderCommand(plugin: Plugin): void {
  plugin.addCommand({
    id: "mind-lite-analyze-folder",
    name: "Mind Lite: Analyze Folder",
    callback: () => {
      const defaultFolderPath = resolveDefaultFolderPath(plugin);
      if (defaultFolderPath == null) {
        new Notice("Mind Lite could not detect your vault path. Enter a folder path to continue.");
      }

      const modal = new AnalyzeModal(
        plugin.app,
        defaultFolderPath ?? "",
        analyzeFolder,
        (result) => {
          setLastRunId(result.run_id);
          new RunStatusModal(plugin.app, result).open();
        }
      );

      modal.open();
    }
  });
}
