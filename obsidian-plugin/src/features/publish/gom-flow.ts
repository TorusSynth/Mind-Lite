import { apiPost } from "../../api/client";
import { createErrorText } from "../../modals/base";

export type PublishPreparePayload = {
  draft_id: string;
  content: string;
  target: string;
};

type PublishPrepareResponse = {
  draft_id: string;
  target: string;
  prepared_content: string;
  sanitized?: boolean;
};

type PublishScoreResponse = {
  draft_id: string;
  scores?: {
    structure?: number;
    clarity?: number;
    safety?: number;
    overall?: number;
  };
  gate_passed: boolean;
};

type PublishMarkResponse = {
  draft_id: string;
  status?: string;
};

export type GateStageDiagnostic = {
  stage: "prepare" | "score" | "mark-for-gom";
  ok: boolean;
  detail: string;
};

export type GomPublishFlowResult = {
  draftId: string;
  target: string;
  preparedContent: string;
  gatePassed: boolean;
  markStatus: string | null;
  diagnostics: GateStageDiagnostic[];
};

function deriveTitle(preparedContent: string, draftId: string): string {
  for (const line of preparedContent.split("\n")) {
    const headingMatch = line.trim().match(/^#+\s+(.+)$/);
    if (headingMatch != null) {
      const heading = headingMatch[1].trim();
      if (heading.length > 0) {
        return heading;
      }
    }
  }

  return draftId;
}

export async function prepareDraftForGom(payload: PublishPreparePayload): Promise<PublishPrepareResponse> {
  return apiPost<PublishPreparePayload, PublishPrepareResponse>("/publish/prepare", payload);
}

export async function runGomGateFlow(
  prepared: PublishPrepareResponse
): Promise<GomPublishFlowResult> {
  const diagnostics: GateStageDiagnostic[] = [];
  diagnostics.push({
    stage: "prepare",
    ok: true,
    detail: `target=${prepared.target}, sanitized=${prepared.sanitized === true ? "yes" : "no"}`
  });

  let scoreResult: PublishScoreResponse;
  try {
    scoreResult = await apiPost<{ draft_id: string; content: string }, PublishScoreResponse>("/publish/score", {
      draft_id: prepared.draft_id,
      content: prepared.prepared_content
    });
  } catch (error) {
    diagnostics.push({
      stage: "score",
      ok: false,
      detail: createErrorText(error)
    });

    return {
      draftId: prepared.draft_id,
      target: prepared.target,
      preparedContent: prepared.prepared_content,
      gatePassed: false,
      markStatus: null,
      diagnostics
    };
  }

  const overall = scoreResult.scores?.overall;
  diagnostics.push({
    stage: "score",
    ok: true,
    detail: `overall=${typeof overall === "number" ? overall.toFixed(2) : "n/a"}, gate_passed=${scoreResult.gate_passed}`
  });

  if (!scoreResult.gate_passed) {
    diagnostics.push({
      stage: "mark-for-gom",
      ok: false,
      detail: "Skipped because gate did not pass"
    });

    return {
      draftId: prepared.draft_id,
      target: prepared.target,
      preparedContent: prepared.prepared_content,
      gatePassed: false,
      markStatus: null,
      diagnostics
    };
  }

  try {
    const markResult = await apiPost<
      { draft_id: string; title: string; prepared_content: string },
      PublishMarkResponse
    >("/publish/mark-for-gom", {
      draft_id: prepared.draft_id,
      title: deriveTitle(prepared.prepared_content, prepared.draft_id),
      prepared_content: prepared.prepared_content
    });

    diagnostics.push({
      stage: "mark-for-gom",
      ok: true,
      detail: markResult.status ?? "queued_for_gom"
    });

    return {
      draftId: prepared.draft_id,
      target: prepared.target,
      preparedContent: prepared.prepared_content,
      gatePassed: true,
      markStatus: markResult.status ?? null,
      diagnostics
    };
  } catch (error) {
    diagnostics.push({
      stage: "mark-for-gom",
      ok: false,
      detail: createErrorText(error)
    });

    return {
      draftId: prepared.draft_id,
      target: prepared.target,
      preparedContent: prepared.prepared_content,
      gatePassed: true,
      markStatus: null,
      diagnostics
    };
  }
}
