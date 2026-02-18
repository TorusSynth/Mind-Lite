from dataclasses import dataclass


@dataclass(frozen=True)
class BudgetDecision:
    status: str
    cloud_allowed: bool
    local_only_mode: bool


def evaluate_budget(monthly_spend: float, monthly_cap: float) -> BudgetDecision:
    if monthly_spend < 0.0:
        raise ValueError("monthly_spend must be >= 0")
    if monthly_cap <= 0.0:
        raise ValueError("monthly_cap must be > 0")

    utilization = monthly_spend / monthly_cap

    if utilization >= 1.0:
        return BudgetDecision(status="hard_stop", cloud_allowed=False, local_only_mode=True)
    if utilization >= 0.9:
        return BudgetDecision(status="warn_90", cloud_allowed=True, local_only_mode=False)
    if utilization >= 0.7:
        return BudgetDecision(status="warn_70", cloud_allowed=True, local_only_mode=False)
    return BudgetDecision(status="normal", cloud_allowed=True, local_only_mode=False)
