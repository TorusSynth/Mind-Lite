from dataclasses import asdict
import json
from pathlib import Path

from mind_lite.contracts.action_tiering import decide_action_mode
from mind_lite.contracts.budget_guardrails import evaluate_budget
from mind_lite.contracts.provider_routing import select_provider, RoutingInput
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


class ApiService:
    def __init__(self, state_file: str | None = None) -> None:
        self._runs: dict[str, dict] = {}
        self._proposals_by_run: dict[str, list[dict]] = {}
        self._gom_queue: list[dict] = []
        self._snapshot_store = SnapshotStore()
        self._run_counter = 0
        self._state_file = Path(state_file) if state_file is not None else None
        self._monthly_budget_cap = 30.0
        self._monthly_spend = 0.0
        self._local_confidence_threshold = 0.70
        self._load_state_if_present()

    def health(self) -> dict:
        return {"status": "ok"}

    def health_ready(self) -> dict:
        return {"status": "ready"}

    def metrics(self) -> str:
        run_count = len(self._runs)
        proposal_count = sum(len(items) for items in self._proposals_by_run.values())
        snapshot_count = len(self._snapshot_store.export_records())
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
            "",
        ]
        return "\n".join(lines)

    def analyze_folder(self, payload: dict) -> dict:
        folder_path = payload.get("folder_path")
        if not isinstance(folder_path, str) or not folder_path:
            raise ValueError("folder_path is required")

        profile = analyze_folder(folder_path)
        run_id = self._next_run_id()
        run = {
            "run_id": run_id,
            "state": "analyzing",
            "profile": asdict(profile),
        }
        self._runs[run_id] = run
        self._proposals_by_run[run_id] = self._build_initial_proposals(run_id)
        self._persist_state()
        return run

    def get_run(self, run_id: str) -> dict:
        if run_id not in self._runs:
            raise ValueError(f"unknown run id: {run_id}")
        return dict(self._runs[run_id])

    def list_runs(self) -> dict:
        ordered = [dict(self._runs[run_id]) for run_id in sorted(self._runs.keys())]
        return {"runs": ordered}

    def get_run_proposals(self, run_id: str) -> dict:
        if run_id not in self._runs:
            raise ValueError(f"unknown run id: {run_id}")
        proposals = [dict(item) for item in self._proposals_by_run.get(run_id, [])]
        return {"run_id": run_id, "proposals": proposals}

    def approve_run(self, run_id: str, payload: dict) -> dict:
        if run_id not in self._runs:
            raise ValueError(f"unknown run id: {run_id}")

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

        run = self._runs[run_id]
        run["state"] = "approved"
        self._persist_state()

        return {
            "run_id": run_id,
            "state": run["state"],
            "approved_count": len(selected),
        }

    def apply_run(self, run_id: str, payload: dict) -> dict:
        if run_id not in self._runs:
            raise ValueError(f"unknown run id: {run_id}")

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

        run = self._runs[run_id]
        run["state"] = "applied"
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

        return {
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
        draft_id = payload.get("draft_id")
        if not isinstance(draft_id, str) or not draft_id.strip():
            raise ValueError("draft_id is required")

        title = payload.get("title")
        if not isinstance(title, str) or not title.strip():
            raise ValueError("title is required")

        prepared_content = payload.get("prepared_content")
        if not isinstance(prepared_content, str) or not prepared_content.strip():
            raise ValueError("prepared_content is required")

        item = {
            "draft_id": draft_id.strip(),
            "title": title.strip(),
            "prepared_content": prepared_content.strip(),
            "status": "queued_for_gom",
        }
        self._gom_queue.append(item)
        self._persist_state()
        return dict(item)

    def list_gom_queue(self) -> dict:
        items = [dict(item) for item in self._gom_queue]
        return {
            "count": len(items),
            "items": items,
        }

    def _next_run_id(self) -> str:
        self._run_counter += 1
        return f"run_{self._run_counter:04d}"

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
