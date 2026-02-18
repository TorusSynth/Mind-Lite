from dataclasses import asdict

from mind_lite.contracts.action_tiering import decide_action_mode
from mind_lite.contracts.snapshot_rollback import SnapshotStore, apply_batch
from mind_lite.onboarding.analyze_readonly import analyze_folder


class ApiService:
    def __init__(self) -> None:
        self._runs: dict[str, dict] = {}
        self._proposals_by_run: dict[str, list[dict]] = {}
        self._snapshot_store = SnapshotStore()
        self._run_counter = 0

    def health(self) -> dict:
        return {"status": "ok"}

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
        return run

    def get_run(self, run_id: str) -> dict:
        if run_id not in self._runs:
            raise ValueError(f"unknown run id: {run_id}")
        return dict(self._runs[run_id])

    def get_run_proposals(self, run_id: str) -> dict:
        if run_id not in self._runs:
            raise ValueError(f"unknown run id: {run_id}")
        proposals = [dict(item) for item in self._proposals_by_run.get(run_id, [])]
        return {"run_id": run_id, "proposals": proposals}

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
            if proposal["status"] != "pending":
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

        return {
            "run_id": run_id,
            "state": run["state"],
            "snapshot_id": snapshot.snapshot_id,
            "applied_count": len(selected),
        }

    def _next_run_id(self) -> str:
        self._run_counter += 1
        return f"run_{self._run_counter:04d}"

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
