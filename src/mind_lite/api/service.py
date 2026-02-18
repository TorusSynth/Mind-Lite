from copy import deepcopy
from dataclasses import asdict
import json
from pathlib import Path

from mind_lite.contracts.action_tiering import decide_action_mode
from mind_lite.contracts.budget_guardrails import evaluate_budget
from mind_lite.contracts.idempotency_replay import RunReplayLedger, apply_event
from mind_lite.contracts.provider_routing import select_provider, RoutingInput
from mind_lite.contracts.run_lifecycle import RunState, validate_transition
from mind_lite.contracts.sensitivity_gate import (
    PROTECTED_PATH_PREFIXES,
    PROTECTED_TAGS,
    SECRET_PATTERNS,
    SensitivityInput,
    cloud_eligibility,
)
from mind_lite.contracts.rollback_validation import validate_rollback_request
from mind_lite.contracts.snapshot_rollback import SnapshotStore, apply_batch
from mind_lite.onboarding.analyze_readonly import analyze_folder
from mind_lite.onboarding.proposal_llm import build_note_prompt, parse_llm_candidates


class ApiService:
    def __init__(self, state_file: str | None = None) -> None:
        self._runs: dict[str, dict] = {}
        self._proposals_by_run: dict[str, list[dict]] = {}
        self._gom_queue: list[dict] = []
        self._gom_published: list[dict] = []
        self._snapshot_store = SnapshotStore()
        self._run_counter = 0
        self._state_file = Path(state_file) if state_file is not None else None
        self._monthly_budget_cap = 30.0
        self._monthly_spend = 0.0
        self._local_confidence_threshold = 0.70
        self._ask_replay_ledger = RunReplayLedger()
        self._ask_response_by_event: dict[str, dict] = {}
        self._links_apply_replay_ledger = RunReplayLedger()
        self._links_apply_response_by_event: dict[str, dict] = {}
        self._publish_mark_replay_ledger = RunReplayLedger()
        self._publish_mark_response_by_event: dict[str, dict] = {}
        self._publish_export_replay_ledger = RunReplayLedger()
        self._publish_export_response_by_event: dict[str, dict] = {}
        self._publish_confirm_replay_ledger = RunReplayLedger()
        self._publish_confirm_response_by_event: dict[str, dict] = {}
        self._load_state_if_present()

    def health(self) -> dict:
        return {"status": "ok"}

    def health_ready(self) -> dict:
        return {"status": "ready"}

    def metrics(self) -> str:
        run_count = len(self._runs)
        proposal_count = sum(len(items) for items in self._proposals_by_run.values())
        snapshot_count = len(self._snapshot_store.export_records())
        publish_queue_count = len(self._gom_queue)
        published_count = len(self._gom_published)
        lines = [
            "# HELP mind_lite_runs_total Total runs recorded",
            "# TYPE mind_lite_runs_total gauge",
            f"mind_lite_runs_total {run_count}",
            "# HELP mind_lite_proposals_total Total proposals recorded",
            "# TYPE mind_lite_proposals_total gauge",
            f"mind_lite_proposals_total {proposal_count}",
            "# HELP mind_lite_snapshots_total Total snapshots recorded",
            "# TYPE mind_lite_snapshots_total gauge",
            f"mind_lite_snapshots_total {snapshot_count}",
            "# HELP mind_lite_publish_queue_total Total drafts queued for publish",
            "# TYPE mind_lite_publish_queue_total gauge",
            f"mind_lite_publish_queue_total {publish_queue_count}",
            "# HELP mind_lite_publish_published_total Total drafts published",
            "# TYPE mind_lite_publish_published_total gauge",
            f"mind_lite_publish_published_total {published_count}",
            "",
        ]
        return "\n".join(lines)

    def analyze_folder(self, payload: dict) -> dict:
        folder_path = payload.get("folder_path")
        if not isinstance(folder_path, str) or not folder_path:
            raise ValueError("folder_path is required")

        profile = analyze_folder(folder_path)
        profile_payload = asdict(profile)
        run_id = self._next_run_id()
        run = {
            "run_id": run_id,
            "state": RunState.QUEUED.value,
            "profile": profile_payload,
            "diagnostics": [],
        }
        self._runs[run_id] = run
        self._transition_run_state(run, RunState.ANALYZING)
        note_proposals, diagnostics, note_success_count = self._build_note_candidate_proposals(
            run_id, profile_payload.get("notes", [])
        )
        run["diagnostics"] = diagnostics
        note_count = profile_payload.get("note_count", 0)

        if note_success_count == 0 and diagnostics:
            self._transition_run_state(run, RunState.FAILED_NEEDS_ATTENTION)
            self._proposals_by_run[run_id] = []
        elif note_count == 0:
            self._proposals_by_run[run_id] = []
            self._transition_run_state(run, RunState.AWAITING_REVIEW)
        else:
            proposals = note_proposals or self._build_initial_proposals(run_id)
            self._proposals_by_run[run_id] = proposals
            if any(proposal.get("action_mode") == "auto" for proposal in proposals):
                self._transition_run_state(run, RunState.READY_SAFE_AUTO)
            else:
                self._transition_run_state(run, RunState.AWAITING_REVIEW)
        self._persist_state()
        return deepcopy(run)

    def get_run(self, run_id: str) -> dict:
        if run_id not in self._runs:
            raise ValueError(f"unknown run id: {run_id}")
        return deepcopy(self._runs[run_id])

    def list_runs(self, filters: dict | None = None) -> dict:
        if filters is not None and not isinstance(filters, dict):
            raise ValueError("filters must be an object")

        active_state = None
        if filters is not None and "state" in filters:
            state_value = filters.get("state")
            if not isinstance(state_value, str) or not state_value:
                raise ValueError("state filter must be a non-empty string")
            active_state = state_value

        ordered = [deepcopy(self._runs[run_id]) for run_id in sorted(self._runs.keys())]
        if active_state is not None:
            ordered = [run for run in ordered if run.get("state") == active_state]
        return {"runs": ordered}

    def get_run_proposals(self, run_id: str, filters: dict | None = None) -> dict:
        if run_id not in self._runs:
            raise ValueError(f"unknown run id: {run_id}")

        if filters is not None and not isinstance(filters, dict):
            raise ValueError("filters must be an object")

        allowed_keys = {"risk_tier", "action_mode", "status"}
        active_filters = {}
        for key, value in (filters or {}).items():
            if key not in allowed_keys:
                raise ValueError(f"unsupported proposal filter: {key}")
            if not isinstance(value, str) or not value:
                raise ValueError(f"{key} filter must be a non-empty string")
            active_filters[key] = value

        proposals = [deepcopy(item) for item in self._proposals_by_run.get(run_id, [])]
        for key, value in active_filters.items():
            proposals = [item for item in proposals if item.get(key) == value]
        return {"run_id": run_id, "proposals": proposals}

    def approve_run(self, run_id: str, payload: dict) -> dict:
        if run_id not in self._runs:
            raise ValueError(f"unknown run id: {run_id}")

        run = self._runs[run_id]
        if run.get("state") not in {RunState.AWAITING_REVIEW.value, RunState.READY_SAFE_AUTO.value}:
            raise ValueError("run state must be awaiting_review or ready_safe_auto")

        requested_types = payload.get("change_types")
        if requested_types is not None:
            if not isinstance(requested_types, list) or not all(isinstance(x, str) for x in requested_types):
                raise ValueError("change_types must be a list of strings")
            type_filter = set(requested_types)
        else:
            type_filter = None

        selected: list[dict] = []
        for proposal in self._proposals_by_run.get(run_id, []):
            if proposal["status"] not in {"pending", "approved"}:
                continue
            if type_filter is not None and proposal["change_type"] not in type_filter:
                continue
            selected.append(proposal)

        if not selected:
            raise ValueError("no matching proposals to approve")

        for proposal in selected:
            proposal["status"] = "approved"

        if run.get("state") == RunState.READY_SAFE_AUTO.value:
            self._transition_run_state(run, RunState.AWAITING_REVIEW)
        self._transition_run_state(run, RunState.APPROVED)
        self._persist_state()

        return {
            "run_id": run_id,
            "state": run["state"],
            "approved_count": len(selected),
        }

    def apply_run(self, run_id: str, payload: dict) -> dict:
        if run_id not in self._runs:
            raise ValueError(f"unknown run id: {run_id}")

        run = self._runs[run_id]
        if run.get("state") != RunState.APPROVED.value:
            raise ValueError("run state must be approved")

        requested_types = payload.get("change_types")
        if requested_types is not None:
            if not isinstance(requested_types, list) or not all(isinstance(x, str) for x in requested_types):
                raise ValueError("change_types must be a list of strings")
            type_filter = set(requested_types)
        else:
            type_filter = None

        selected: list[dict] = []
        for proposal in self._proposals_by_run.get(run_id, []):
            if proposal["status"] not in {"pending", "approved"}:
                continue
            if type_filter is not None and proposal["change_type"] not in type_filter:
                continue
            selected.append(proposal)

        if not selected:
            raise ValueError("no matching proposals to apply")

        for proposal in selected:
            proposal["status"] = "applied"

        changed_note_ids = [proposal["proposal_id"] for proposal in selected]
        snapshot = apply_batch(self._snapshot_store, run_id, changed_note_ids)

        self._transition_run_state(run, RunState.APPLIED)
        run["snapshot_id"] = snapshot.snapshot_id
        self._persist_state()

        return {
            "run_id": run_id,
            "state": run["state"],
            "snapshot_id": snapshot.snapshot_id,
            "applied_count": len(selected),
        }

    def rollback_run(self, run_id: str, payload: dict) -> dict:
        if run_id not in self._runs:
            raise ValueError(f"unknown run id: {run_id}")

        requested_snapshot = payload.get("snapshot_id")
        if requested_snapshot is None:
            requested_snapshot = self._runs[run_id].get("snapshot_id")

        if not isinstance(requested_snapshot, str) or not requested_snapshot:
            raise ValueError("snapshot_id is required")

        decision = validate_rollback_request(self._snapshot_store, run_id, requested_snapshot)
        if not decision.allowed:
            raise ValueError(decision.reason)

        run = self._runs[run_id]
        run["state"] = "rolled_back"
        run["rolled_back_snapshot_id"] = requested_snapshot
        self._persist_state()

        return {
            "run_id": run_id,
            "state": run["state"],
            "rolled_back_snapshot_id": requested_snapshot,
        }

    def check_sensitivity(self, payload: dict) -> dict:
        frontmatter = payload.get("frontmatter", {})
        tags = payload.get("tags", [])
        path = payload.get("path", "")
        content = payload.get("content", "")

        if not isinstance(frontmatter, dict):
            raise ValueError("frontmatter must be an object")
        if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
            raise ValueError("tags must be a list of strings")
        if not isinstance(path, str):
            raise ValueError("path must be a string")
        if not isinstance(content, str):
            raise ValueError("content must be a string")

        result = cloud_eligibility(
            SensitivityInput(
                frontmatter=frontmatter,
                tags=tags,
                path=path,
                content=content,
            )
        )
        return {
            "allowed": result.allowed,
            "reasons": list(result.reasons),
        }

    def get_sensitivity_policy(self) -> dict:
        return {
            "protected_tags": sorted(PROTECTED_TAGS),
            "protected_path_prefixes": list(PROTECTED_PATH_PREFIXES),
            "secret_pattern_count": len(SECRET_PATTERNS),
        }

    def get_routing_policy(self) -> dict:
        budget_decision = evaluate_budget(self._monthly_spend, self._monthly_budget_cap)
        cloud_allowed = budget_decision.cloud_allowed
        fallback_reasons = [
            "timeout",
            "grounding_failure",
            "low_confidence",
        ]

        preview = {
            "timeout": select_provider(
                RoutingInput(
                    local_confidence=0.90,
                    local_timed_out=True,
                    grounding_failed=False,
                    cloud_allowed=cloud_allowed,
                )
            ).provider,
            "grounding_failure": select_provider(
                RoutingInput(
                    local_confidence=0.90,
                    local_timed_out=False,
                    grounding_failed=True,
                    cloud_allowed=cloud_allowed,
                )
            ).provider,
            "low_confidence": select_provider(
                RoutingInput(
                    local_confidence=0.60,
                    local_timed_out=False,
                    grounding_failed=False,
                    cloud_allowed=cloud_allowed,
                )
            ).provider,
        }

        return {
            "routing": {
                "local_provider": "local",
                "fallback_provider": "openai",
                "local_confidence_threshold": self._local_confidence_threshold,
                "fallback_reasons": fallback_reasons,
                "fallback_preview": preview,
            },
            "budget": {
                "monthly_spend": self._monthly_spend,
                "monthly_cap": self._monthly_budget_cap,
                "status": budget_decision.status,
                "cloud_allowed": budget_decision.cloud_allowed,
                "local_only_mode": budget_decision.local_only_mode,
            },
        }

    def ask(self, payload: dict) -> dict:
        query = payload.get("query")
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query is required")

        event_id = payload.get("event_id")
        if event_id is not None and (not isinstance(event_id, str) or not event_id.strip()):
            raise ValueError("event_id must be a non-empty string")
        normalized_event_id = event_id.strip() if isinstance(event_id, str) else None

        if normalized_event_id is not None:
            replay = apply_event(self._ask_replay_ledger, "ask", normalized_event_id)
            if replay.duplicate:
                cached = self._ask_response_by_event.get(normalized_event_id)
                if cached is None:
                    raise ValueError("missing replay cache for duplicate event")
                duplicated = deepcopy(cached)
                duplicated["idempotency"] = {
                    "event_id": normalized_event_id,
                    "duplicate": True,
                    "reason": replay.reason,
                }
                return duplicated

        allow_fallback = payload.get("allow_fallback", True)
        if not isinstance(allow_fallback, bool):
            raise ValueError("allow_fallback must be a boolean")

        local_confidence = payload.get("local_confidence", 0.85)
        if not isinstance(local_confidence, (float, int)):
            raise ValueError("local_confidence must be a number")
        local_confidence = float(local_confidence)

        local_timed_out = payload.get("local_timed_out", False)
        if not isinstance(local_timed_out, bool):
            raise ValueError("local_timed_out must be a boolean")

        grounding_failed = payload.get("grounding_failed", False)
        if not isinstance(grounding_failed, bool):
            raise ValueError("grounding_failed must be a boolean")

        frontmatter = payload.get("frontmatter", {})
        tags = payload.get("tags", [])
        path = payload.get("path", "")
        content = payload.get("content", "")

        if not isinstance(frontmatter, dict):
            raise ValueError("frontmatter must be an object")
        if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
            raise ValueError("tags must be a list of strings")
        if not isinstance(path, str):
            raise ValueError("path must be a string")
        if not isinstance(content, str):
            raise ValueError("content must be a string")

        sensitivity = cloud_eligibility(
            SensitivityInput(
                frontmatter=frontmatter,
                tags=tags,
                path=path,
                content=content,
            )
        )

        budget_decision = evaluate_budget(self._monthly_spend, self._monthly_budget_cap)
        cloud_allowed = allow_fallback and sensitivity.allowed and budget_decision.cloud_allowed

        routing = select_provider(
            RoutingInput(
                local_confidence=local_confidence,
                local_timed_out=local_timed_out,
                grounding_failed=grounding_failed,
                cloud_allowed=cloud_allowed,
            )
        )

        response = {
            "answer": {
                "text": f"Draft answer for: {query.strip()}",
                "confidence": local_confidence,
            },
            "provider_trace": {
                "initial": "local",
                "provider": routing.provider,
                "fallback_used": routing.fallback_used,
                "fallback_provider": routing.provider if routing.fallback_used else None,
                "fallback_reason": routing.reason,
            },
            "sensitivity": {
                "allowed": sensitivity.allowed,
                "reasons": list(sensitivity.reasons),
            },
            "budget": {
                "status": budget_decision.status,
                "cloud_allowed": budget_decision.cloud_allowed,
                "local_only_mode": budget_decision.local_only_mode,
            },
        }

        response["idempotency"] = {
            "event_id": normalized_event_id,
            "duplicate": False,
            "reason": "accepted" if normalized_event_id is not None else "not_provided",
        }
        if normalized_event_id is not None:
            self._ask_response_by_event[normalized_event_id] = deepcopy(response)
            self._persist_state()
        return response

    def publish_score(self, payload: dict) -> dict:
        draft_id = payload.get("draft_id")
        if not isinstance(draft_id, str) or not draft_id.strip():
            raise ValueError("draft_id is required")

        content = payload.get("content")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("content is required")

        normalized = content.strip()
        word_count = len(normalized.split())
        has_todo = "todo" in normalized.lower()

        structure = min(1.0, word_count / 70.0)
        if word_count >= 40 and "." in normalized:
            clarity = 0.90
        elif word_count >= 20:
            clarity = 0.60
        else:
            clarity = 0.40
        safety = 0.20 if has_todo else 0.90
        overall = round((structure + clarity + safety) / 3.0, 2)

        return {
            "draft_id": draft_id.strip(),
            "scores": {
                "structure": round(structure, 2),
                "clarity": round(clarity, 2),
                "safety": round(safety, 2),
                "overall": overall,
            },
            "gate_passed": overall >= 0.80,
        }

    def publish_prepare(self, payload: dict) -> dict:
        draft_id = payload.get("draft_id")
        if not isinstance(draft_id, str) or not draft_id.strip():
            raise ValueError("draft_id is required")

        content = payload.get("content")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("content is required")

        target = payload.get("target")
        if not isinstance(target, str) or not target.strip():
            raise ValueError("target is required")

        prepared_content = content.strip().replace("\r\n", "\n")

        return {
            "draft_id": draft_id.strip(),
            "target": target.strip(),
            "prepared_content": prepared_content,
            "sanitized": True,
        }

    def mark_for_gom(self, payload: dict) -> dict:
        event_id = payload.get("event_id")
        if event_id is not None and (not isinstance(event_id, str) or not event_id.strip()):
            raise ValueError("event_id must be a non-empty string")
        normalized_event_id = event_id.strip() if isinstance(event_id, str) else None

        if normalized_event_id is not None:
            replay = apply_event(self._publish_mark_replay_ledger, "publish_mark", normalized_event_id)
            if replay.duplicate:
                cached = self._publish_mark_response_by_event.get(normalized_event_id)
                if cached is None:
                    raise ValueError("missing replay cache for duplicate event")
                duplicated = deepcopy(cached)
                duplicated["idempotency"] = {
                    "event_id": normalized_event_id,
                    "duplicate": True,
                    "reason": replay.reason,
                }
                return duplicated

        draft_id = payload.get("draft_id")
        if not isinstance(draft_id, str) or not draft_id.strip():
            raise ValueError("draft_id is required")

        title = payload.get("title")
        if not isinstance(title, str) or not title.strip():
            raise ValueError("title is required")

        prepared_content = payload.get("prepared_content")
        if not isinstance(prepared_content, str) or not prepared_content.strip():
            raise ValueError("prepared_content is required")

        item: dict[str, object] = {
            "draft_id": draft_id.strip(),
            "title": title.strip(),
            "prepared_content": prepared_content.strip(),
            "status": "queued_for_gom",
        }
        item["idempotency"] = {
            "event_id": normalized_event_id,
            "duplicate": False,
            "reason": "accepted" if normalized_event_id is not None else "not_provided",
        }
        self._gom_queue.append(item)
        if normalized_event_id is not None:
            self._publish_mark_response_by_event[normalized_event_id] = deepcopy(item)
        self._persist_state()
        return deepcopy(item)

    def list_gom_queue(self) -> dict:
        items = deepcopy(self._gom_queue)
        return {
            "count": len(items),
            "items": items,
        }

    def export_for_gom(self, payload: dict) -> dict:
        event_id = payload.get("event_id")
        if event_id is not None and (not isinstance(event_id, str) or not event_id.strip()):
            raise ValueError("event_id must be a non-empty string")
        normalized_event_id = event_id.strip() if isinstance(event_id, str) else None

        if normalized_event_id is not None:
            cached = self._publish_export_response_by_event.get(normalized_event_id)
            if cached is not None:
                replay = apply_event(self._publish_export_replay_ledger, "publish_export", normalized_event_id)
                if not replay.duplicate:
                    replay = apply_event(self._publish_export_replay_ledger, "publish_export", normalized_event_id)
                duplicated = deepcopy(cached)
                duplicated["idempotency"] = {
                    "event_id": normalized_event_id,
                    "duplicate": True,
                    "reason": replay.reason,
                }
                return duplicated

        draft_id = payload.get("draft_id")
        if not isinstance(draft_id, str) or not draft_id.strip():
            raise ValueError("draft_id is required")

        export_format = payload.get("format")
        if not isinstance(export_format, str) or not export_format.strip():
            raise ValueError("format is required")

        if export_format not in {"markdown", "html", "json"}:
            raise ValueError("format must be one of: markdown, html, json")

        matched = None
        for item in self._gom_queue:
            if item.get("draft_id") == draft_id.strip():
                matched = item
                break

        if matched is None:
            raise ValueError(f"unknown draft id: {draft_id}")

        artifact = matched["prepared_content"]
        if export_format == "html":
            artifact = f"<p>{matched['prepared_content']}</p>"
        elif export_format == "json":
            artifact = json.dumps(
                {
                    "draft_id": matched["draft_id"],
                    "title": matched["title"],
                    "prepared_content": matched["prepared_content"],
                },
                sort_keys=True,
            )

        response = {
            "draft_id": matched["draft_id"],
            "format": export_format,
            "status": "export_ready",
            "artifact": artifact,
        }
        response["idempotency"] = {
            "event_id": normalized_event_id,
            "duplicate": False,
            "reason": "accepted" if normalized_event_id is not None else "not_provided",
        }
        if normalized_event_id is not None:
            replay = apply_event(self._publish_export_replay_ledger, "publish_export", normalized_event_id)
            if replay.duplicate:
                raise ValueError("missing replay cache for duplicate event")
            self._publish_export_response_by_event[normalized_event_id] = deepcopy(response)
            self._persist_state()
        return response

    def confirm_gom(self, payload: dict) -> dict:
        event_id = payload.get("event_id")
        if event_id is not None and (not isinstance(event_id, str) or not event_id.strip()):
            raise ValueError("event_id must be a non-empty string")
        normalized_event_id = event_id.strip() if isinstance(event_id, str) else None

        if normalized_event_id is not None:
            replay = apply_event(self._publish_confirm_replay_ledger, "publish_confirm", normalized_event_id)
            if replay.duplicate:
                cached = self._publish_confirm_response_by_event.get(normalized_event_id)
                if cached is None:
                    raise ValueError("missing replay cache for duplicate event")
                duplicated = deepcopy(cached)
                duplicated["idempotency"] = {
                    "event_id": normalized_event_id,
                    "duplicate": True,
                    "reason": replay.reason,
                }
                return duplicated

        draft_id = payload.get("draft_id")
        if not isinstance(draft_id, str) or not draft_id.strip():
            raise ValueError("draft_id is required")

        published_url = payload.get("published_url")
        if not isinstance(published_url, str) or not published_url.strip():
            raise ValueError("published_url is required")

        match_index = None
        for idx, item in enumerate(self._gom_queue):
            if item.get("draft_id") == draft_id.strip():
                match_index = idx
                break

        if match_index is None:
            raise ValueError(f"unknown draft id: {draft_id}")

        queued_item = self._gom_queue.pop(match_index)
        published = {
            "draft_id": queued_item["draft_id"],
            "title": queued_item["title"],
            "published_url": published_url.strip(),
            "status": "published",
        }
        published["idempotency"] = {
            "event_id": normalized_event_id,
            "duplicate": False,
            "reason": "accepted" if normalized_event_id is not None else "not_provided",
        }
        self._gom_published.append(published)
        if normalized_event_id is not None:
            self._publish_confirm_response_by_event[normalized_event_id] = deepcopy(published)
        self._persist_state()
        return deepcopy(published)

    def list_published(self) -> dict:
        items = deepcopy(self._gom_published)
        return {
            "count": len(items),
            "items": items,
        }

    def organize_classify(self, payload: dict) -> dict:
        notes = payload.get("notes")
        if not isinstance(notes, list) or not notes:
            raise ValueError("notes must be a non-empty list")

        results = []
        for note in notes:
            if not isinstance(note, dict):
                raise ValueError("each note must be an object")

            note_id = note.get("note_id")
            title = note.get("title")
            if not isinstance(note_id, str) or not note_id.strip():
                raise ValueError("note_id is required")
            if not isinstance(title, str) or not title.strip():
                raise ValueError("title is required")

            primary, confidence = self._classify_para(title)
            action_mode = decide_action_mode("low", confidence).value
            results.append(
                {
                    "note_id": note_id.strip(),
                    "primary_para": primary,
                    "secondary_para": [],
                    "confidence": confidence,
                    "action_mode": action_mode,
                }
            )

        return {"results": results}

    def organize_propose_structure(self, payload: dict) -> dict:
        notes = payload.get("notes")
        if not isinstance(notes, list) or not notes:
            raise ValueError("notes must be a non-empty list")

        proposals = []
        for note in notes:
            if not isinstance(note, dict):
                raise ValueError("each note must be an object")
            note_id = note.get("note_id")
            title = note.get("title")
            folder = note.get("folder", "Inbox")

            if not isinstance(note_id, str) or not note_id.strip():
                raise ValueError("note_id is required")
            if not isinstance(title, str) or not title.strip():
                raise ValueError("title is required")
            if not isinstance(folder, str):
                raise ValueError("folder must be a string")

            proposed_folder = self._proposed_folder(title, folder)
            proposals.append(
                {
                    "note_id": note_id.strip(),
                    "current_folder": folder,
                    "proposed_folder": proposed_folder,
                    "reason": "folder_standardization",
                    "action_mode": "manual",
                }
            )

        return {"proposals": proposals}

    def links_propose(self, payload: dict) -> dict:
        source_note_id = payload.get("source_note_id")
        if not isinstance(source_note_id, str) or not source_note_id.strip():
            raise ValueError("source_note_id is required")

        candidate_notes = payload.get("candidate_notes")
        if not isinstance(candidate_notes, list) or not candidate_notes:
            raise ValueError("candidate_notes must be a non-empty list")

        suggestions = []
        for note in candidate_notes:
            if not isinstance(note, dict):
                raise ValueError("each candidate note must be an object")
            note_id = note.get("note_id")
            title = note.get("title")
            if not isinstance(note_id, str) or not note_id.strip():
                raise ValueError("candidate note_id is required")
            if not isinstance(title, str) or not title.strip():
                raise ValueError("candidate title is required")

            confidence = self._link_confidence(title)
            suggestions.append(
                {
                    "target_note_id": note_id.strip(),
                    "confidence": confidence,
                    "reason": self._link_reason(title),
                }
            )

        suggestions.sort(key=lambda item: item["confidence"], reverse=True)
        return {
            "source_note_id": source_note_id.strip(),
            "suggestions": suggestions,
        }

    def links_apply(self, payload: dict) -> dict:
        source_note_id = payload.get("source_note_id")
        if not isinstance(source_note_id, str) or not source_note_id.strip():
            raise ValueError("source_note_id is required")

        event_id = payload.get("event_id")
        if event_id is not None and (not isinstance(event_id, str) or not event_id.strip()):
            raise ValueError("event_id must be a non-empty string")
        normalized_event_id = event_id.strip() if isinstance(event_id, str) else None

        if normalized_event_id is not None:
            replay = apply_event(self._links_apply_replay_ledger, "links_apply", normalized_event_id)
            if replay.duplicate:
                cached = self._links_apply_response_by_event.get(normalized_event_id)
                if cached is None:
                    raise ValueError("missing replay cache for duplicate event")
                duplicated = deepcopy(cached)
                duplicated["idempotency"] = {
                    "event_id": normalized_event_id,
                    "duplicate": True,
                    "reason": replay.reason,
                }
                return duplicated

        links = payload.get("links")
        if not isinstance(links, list) or not links:
            raise ValueError("links must be a non-empty list")

        min_confidence = payload.get("min_confidence", 0.0)
        if not isinstance(min_confidence, (float, int)):
            raise ValueError("min_confidence must be a number")
        min_confidence = float(min_confidence)

        applied_links = []
        for link in links:
            if not isinstance(link, dict):
                raise ValueError("each link must be an object")

            target_note_id = link.get("target_note_id")
            confidence = link.get("confidence")
            if not isinstance(target_note_id, str) or not target_note_id.strip():
                raise ValueError("target_note_id is required")
            if not isinstance(confidence, (float, int)):
                raise ValueError("confidence must be a number")

            confidence = float(confidence)
            if confidence < min_confidence:
                continue

            applied_links.append(
                {
                    "target_note_id": target_note_id.strip(),
                    "confidence": confidence,
                    "status": "applied",
                }
            )

        response = {
            "source_note_id": source_note_id.strip(),
            "applied_count": len(applied_links),
            "applied_links": applied_links,
        }
        response["idempotency"] = {
            "event_id": normalized_event_id,
            "duplicate": False,
            "reason": "accepted" if normalized_event_id is not None else "not_provided",
        }
        if normalized_event_id is not None:
            self._links_apply_response_by_event[normalized_event_id] = deepcopy(response)
            self._persist_state()
        return response

    def _next_run_id(self) -> str:
        self._run_counter += 1
        return f"run_{self._run_counter:04d}"

    def _transition_run_state(self, run: dict, target: RunState) -> None:
        current_value = run.get("state")
        try:
            current_state = RunState(current_value)
        except ValueError as exc:
            raise ValueError(f"invalid run state transition: {current_value} -> {target.value}") from exc

        if not validate_transition(current_state, target):
            raise ValueError(f"invalid run state transition: {current_state.value} -> {target.value}")
        run["state"] = target.value

    def _load_state_if_present(self) -> None:
        if self._state_file is None or not self._state_file.exists():
            return
        payload = json.loads(self._state_file.read_text(encoding="utf-8"))
        self._run_counter = int(payload.get("run_counter", 0))
        self._runs = {
            key: dict(value)
            for key, value in payload.get("runs", {}).items()
            if isinstance(value, dict)
        }
        self._proposals_by_run = {
            key: [dict(item) for item in value]
            for key, value in payload.get("proposals", {}).items()
            if isinstance(value, list)
        }
        self._gom_queue = [
            dict(item)
            for item in payload.get("gom_queue", [])
            if isinstance(item, dict)
        ]
        self._gom_published = [
            dict(item)
            for item in payload.get("gom_published", [])
            if isinstance(item, dict)
        ]
        ask_replay_payload = payload.get("ask_replay", {})
        self._ask_response_by_event = {
            key: dict(value)
            for key, value in ask_replay_payload.items()
            if isinstance(key, str) and isinstance(value, dict)
        }
        self._ask_replay_ledger = RunReplayLedger()
        for event_id in sorted(self._ask_response_by_event.keys()):
            apply_event(self._ask_replay_ledger, "ask", event_id)
        links_apply_replay_payload = payload.get("links_apply_replay", {})
        self._links_apply_response_by_event = {
            key: dict(value)
            for key, value in links_apply_replay_payload.items()
            if isinstance(key, str) and isinstance(value, dict)
        }
        self._links_apply_replay_ledger = RunReplayLedger()
        for event_id in sorted(self._links_apply_response_by_event.keys()):
            apply_event(self._links_apply_replay_ledger, "links_apply", event_id)
        publish_mark_replay_payload = payload.get("publish_mark_replay", {})
        self._publish_mark_response_by_event = {
            key: dict(value)
            for key, value in publish_mark_replay_payload.items()
            if isinstance(key, str) and isinstance(value, dict)
        }
        self._publish_mark_replay_ledger = RunReplayLedger()
        for event_id in sorted(self._publish_mark_response_by_event.keys()):
            apply_event(self._publish_mark_replay_ledger, "publish_mark", event_id)
        publish_export_replay_payload = payload.get("publish_export_replay", {})
        self._publish_export_response_by_event = {
            key: dict(value)
            for key, value in publish_export_replay_payload.items()
            if isinstance(key, str) and isinstance(value, dict)
        }
        self._publish_export_replay_ledger = RunReplayLedger()
        for event_id in sorted(self._publish_export_response_by_event.keys()):
            apply_event(self._publish_export_replay_ledger, "publish_export", event_id)
        publish_confirm_replay_payload = payload.get("publish_confirm_replay", {})
        self._publish_confirm_response_by_event = {
            key: dict(value)
            for key, value in publish_confirm_replay_payload.items()
            if isinstance(key, str) and isinstance(value, dict)
        }
        self._publish_confirm_replay_ledger = RunReplayLedger()
        for event_id in sorted(self._publish_confirm_response_by_event.keys()):
            apply_event(self._publish_confirm_replay_ledger, "publish_confirm", event_id)
        snapshot_payload = payload.get("snapshots", {})
        if isinstance(snapshot_payload, dict):
            self._snapshot_store.import_records(snapshot_payload)

    def _persist_state(self) -> None:
        if self._state_file is None:
            return
        if self._state_file.parent != Path(""):
            self._state_file.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "run_counter": self._run_counter,
            "runs": self._runs,
            "proposals": self._proposals_by_run,
            "gom_queue": self._gom_queue,
            "gom_published": self._gom_published,
            "ask_replay": self._ask_response_by_event,
            "links_apply_replay": self._links_apply_response_by_event,
            "publish_mark_replay": self._publish_mark_response_by_event,
            "publish_export_replay": self._publish_export_response_by_event,
            "publish_confirm_replay": self._publish_confirm_response_by_event,
            "snapshots": self._snapshot_store.export_records(),
        }
        self._state_file.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def _build_initial_proposals(self, run_id: str) -> list[dict]:
        proposal_specs = [
            ("tag_enrichment", "low", 0.85),
            ("link_add", "medium", 0.72),
        ]
        proposals: list[dict] = []
        for idx, (change_type, risk_tier, confidence) in enumerate(proposal_specs, start=1):
            proposals.append(
                {
                    "proposal_id": f"{run_id}-prop-{idx:02d}",
                    "change_type": change_type,
                    "risk_tier": risk_tier,
                    "confidence": confidence,
                    "action_mode": decide_action_mode(risk_tier, confidence).value,
                    "status": "pending",
                }
            )
        return proposals

    def _build_note_candidate_proposals(self, run_id: str, notes: list[dict]) -> tuple[list[dict], list[dict], int]:
        if not isinstance(notes, list) or not notes:
            return [], [], 0

        candidates: list[dict] = []
        diagnostics: list[dict] = []
        note_success_count = 0
        for note in notes:
            if not isinstance(note, dict):
                continue

            note_id = note.get("note_id")
            try:
                prompt = build_note_prompt(note)
                raw = self._generate_note_candidate_response(note, prompt)
            except ValueError as exc:
                diagnostics.append(
                    {
                        "note_id": note_id,
                        "stage": "candidate_generation",
                        "error": str(exc),
                    }
                )
                continue
            except Exception as exc:  # pragma: no cover - defensive against provider failures
                diagnostics.append(
                    {
                        "note_id": note_id,
                        "stage": "candidate_generation",
                        "error": str(exc),
                    }
                )
                continue

            if not isinstance(raw, str):
                diagnostics.append(
                    {
                        "note_id": note_id,
                        "stage": "candidate_generation_empty_output",
                        "error": "candidate output must be a non-empty string",
                    }
                )
                continue

            if not raw.strip():
                diagnostics.append(
                    {
                        "note_id": note_id,
                        "stage": "candidate_generation_empty_output",
                        "error": "candidate output was empty",
                    }
                )
                continue
            try:
                parsed = parse_llm_candidates(raw)
            except ValueError as exc:
                diagnostics.append(
                    {
                        "note_id": note_id,
                        "stage": "candidate_parse",
                        "error": str(exc),
                    }
                )
                continue

            if not parsed:
                diagnostics.append(
                    {
                        "note_id": note_id,
                        "stage": "candidate_parse_empty_candidates",
                        "error": "candidate output did not include any proposals",
                    }
                )
                continue

            note_success_count += 1
            candidates.extend(parsed)

        proposals: list[dict] = []
        for index, candidate in enumerate(candidates, start=1):
            risk_tier = candidate["risk_tier"]
            confidence = float(candidate["confidence"])
            proposals.append(
                {
                    "proposal_id": f"{run_id}-prop-{index:02d}",
                    "change_type": candidate["change_type"],
                    "risk_tier": risk_tier,
                    "confidence": confidence,
                    "action_mode": decide_action_mode(risk_tier, confidence).value,
                    "status": "pending",
                    "note_id": candidate["note_id"],
                    "details": dict(candidate["details"]),
                }
            )
        return proposals, diagnostics, note_success_count

    def _generate_note_candidate_response(self, note: dict, prompt: str) -> str:
        del prompt
        note_id = note.get("note_id") if isinstance(note, dict) else None
        if not isinstance(note_id, str) or not note_id.strip():
            note_id = "unknown"

        payload = {
            "proposals": [
                {
                    "note_id": note_id,
                    "change_type": "tag_enrichment",
                    "risk_tier": "low",
                    "confidence": 0.8,
                    "details": {
                        "reason": "default_note_candidate",
                    },
                }
            ]
        }
        return json.dumps(payload, sort_keys=True)

    def _classify_para(self, title: str) -> tuple[str, float]:
        lowered = title.lower()
        if "project" in lowered:
            return "project", 0.86
        if "area" in lowered:
            return "area", 0.83
        if "archive" in lowered:
            return "archive", 0.81
        return "resource", 0.79

    def _link_confidence(self, title: str) -> float:
        lowered = title.lower()
        if "atlas" in lowered or "architecture" in lowered:
            return 0.88
        if "project" in lowered:
            return 0.82
        return 0.61

    def _link_reason(self, title: str) -> str:
        lowered = title.lower()
        if "atlas" in lowered:
            return "shared_project_context"
        if "architecture" in lowered:
            return "structural_overlap"
        return "semantic_similarity"

    def _proposed_folder(self, title: str, current_folder: str) -> str:
        lowered = title.lower()
        if "project" in lowered or "atlas" in lowered:
            return "Projects"
        if "archive" in lowered:
            return "Archive"
        if current_folder.strip():
            return current_folder
        return "Resources"
