from dataclasses import asdict

from mind_lite.onboarding.analyze_readonly import analyze_folder


class ApiService:
    def __init__(self) -> None:
        self._runs: dict[str, dict] = {}
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
        return run

    def get_run(self, run_id: str) -> dict:
        if run_id not in self._runs:
            raise ValueError(f"unknown run id: {run_id}")
        return dict(self._runs[run_id])

    def _next_run_id(self) -> str:
        self._run_counter += 1
        return f"run_{self._run_counter:04d}"
