"""Phase 12: Funnel attrition, score breakdown, and run comparison service.

Explains how companies move through the screening funnel:
Universe -> Markets -> Floors -> Gates -> Score -> Shortlist -> Selected,
and generates metric-level score breakdowns and run delta comparisons.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime

from app.core.logging import DiagnosticLogger
from app.models.screening_run import FunnelCountRecord, ScreeningResultRecord, ScreeningRunRecord
from app.schemas.screening import (
    FunnelStageCounts,
    MetricScoreBreakdownItem,
    ScreenedSecurityResult,
)

logger = DiagnosticLogger("funnel_service")


class FunnelService:
    """Computes funnel stage progression, score breakdowns, and delta run comparisons."""

    def compute_funnel_counts(
        self,
        universe_count: int,
        markets_count: int,
        floors_count: int,
        gates_count: int,
        scored_count: int,
        shortlist_count: int,
        selected_count: int,
    ) -> FunnelStageCounts:
        """Construct audit funnel progression counts across all 7 stages."""
        return FunnelStageCounts(
            universe=universe_count,
            markets=markets_count,
            floors=floors_count,
            gates=gates_count,
            score=scored_count,
            shortlist=shortlist_count,
            selected=selected_count,
        )

    def compute_score_breakdown(
        self,
        company_metrics: Dict[str, Any],
        active_rules: List[Dict[str, Any]],
    ) -> List[MetricScoreBreakdownItem]:
        """Generate metric-by-metric score points, max scores, and statuses for a company."""
        breakdown: List[MetricScoreBreakdownItem] = []

        total_weight = sum(r.get("weight", 0.0) for r in active_rules if r.get("mode") in ("Score", "Both"))
        scale = 100.0 / total_weight if total_weight > 0 else 1.0

        for r in active_rules:
            metric_id = r.get("id") or r.get("metric_name")
            name = r.get("name") or r.get("label") or metric_id
            mode = r.get("mode", "Off")
            weight = float(r.get("weight", 0.0))
            condition = r.get("condition", ">=")
            threshold = float(r.get("threshold_value", r.get("value", 0.0)))

            if mode == "Off":
                continue

            max_pts = round(weight * scale, 1) if mode in ("Score", "Both") else 0.0
            actual_val = company_metrics.get(metric_id)

            if actual_val is None:
                breakdown.append(
                    MetricScoreBreakdownItem(
                        name=name,
                        score=0.0,
                        max_score=max_pts,
                        value_display="n/a",
                        benchmark_display=f"{condition} {threshold}",
                        percentage=0.0,
                        status="miss",
                    )
                )
                continue

            # Pass condition test
            passed = False
            if condition == ">=":
                passed = actual_val >= threshold
            elif condition == "<=":
                passed = actual_val <= threshold
            elif condition == ">":
                passed = actual_val > threshold
            elif condition == "<":
                passed = actual_val < threshold
            elif condition == "=":
                passed = abs(actual_val - threshold) < 1e-4

            awarded = max_pts if passed else 0.0
            percentage = 100.0 if passed else 0.0
            status_val = "full" if passed else "miss"

            # Check near-miss within 10%
            if not passed and max_pts > 0 and threshold != 0:
                pct_off = abs(actual_val - threshold) / abs(threshold)
                if pct_off <= 0.10:
                    status_val = "threshold"
                    awarded = round(max_pts * 0.5, 1)
                    percentage = 50.0

            breakdown.append(
                MetricScoreBreakdownItem(
                    name=name,
                    score=awarded,
                    max_score=max_pts,
                    value_display=f"{actual_val:.1f}" if isinstance(actual_val, float) else str(actual_val),
                    benchmark_display=f"{condition} {threshold}",
                    percentage=percentage,
                    status=status_val,
                )
            )

        return breakdown

    def compare_runs(
        self,
        curr_run: ScreeningRunRecord,
        prev_run: ScreeningRunRecord,
        curr_results: List[ScreeningResultRecord],
        prev_results: List[ScreeningResultRecord],
    ) -> Dict[str, Any]:
        """Compare two screening executions, detecting rule diffs, entered/exited stocks, and root causes."""
        # 1. Rule Diffs
        rule_diffs: List[str] = []
        curr_rules_map = {r.get("id"): r for r in curr_run.rules_snapshot}
        prev_rules_map = {r.get("id"): r for r in prev_run.rules_snapshot}

        for r_id, curr_r in curr_rules_map.items():
            name = curr_r.get("name", r_id)
            if r_id in prev_rules_map:
                prev_r = prev_rules_map[r_id]
                parts = []
                if curr_r.get("mode") != prev_r.get("mode"):
                    parts.append(f"Mode: {curr_r.get('mode')} (was {prev_r.get('mode')})")
                if curr_r.get("condition") != prev_r.get("condition") or curr_r.get("threshold_value") != prev_r.get("threshold_value"):
                    parts.append(f"Threshold: {curr_r.get('condition')} {curr_r.get('threshold_value')} (was {prev_r.get('condition')} {prev_r.get('threshold_value')})")
                if curr_r.get("weight") != prev_r.get("weight"):
                    parts.append(f"Weight: {curr_r.get('weight')}% (was {prev_r.get('weight')}%)")
                if parts:
                    rule_diffs.append(f"{name}: {', '.join(parts)}")
            else:
                rule_diffs.append(f"Added rule {name}: {curr_r.get('condition')} {curr_r.get('threshold_value')}")

        for r_id, prev_r in prev_rules_map.items():
            if r_id not in curr_rules_map:
                rule_diffs.append(f"Removed rule: {prev_r.get('name', r_id)}")

        # Country diffs
        prev_countries = set(prev_run.selected_countries or [])
        curr_countries = set(curr_run.selected_countries or [])
        for c in sorted(curr_countries - prev_countries):
            rule_diffs.append(f"Added country: {c}")
        for c in sorted(prev_countries - curr_countries):
            rule_diffs.append(f"Removed country: {c}")

        # 2. Top 20 Diffs
        curr_top20 = [r for r in curr_results if r.rank <= 20]
        prev_top20 = [r for r in prev_results if r.rank <= 20]

        curr_top20_ids = {r.canonical_company_id: r for r in curr_top20}
        prev_top20_ids = {r.canonical_company_id: r for r in prev_top20}

        entered_ids = set(curr_top20_ids.keys()) - set(prev_top20_ids.keys())
        exited_ids = set(prev_top20_ids.keys()) - set(curr_top20_ids.keys())
        retained_ids = set(curr_top20_ids.keys()) & set(prev_top20_ids.keys())

        # Cause attribution for entered
        entered_list = []
        for cid in entered_ids:
            sec = curr_top20_ids[cid]
            cause = "MARKET_MOVEMENT"
            reason = "Score and ranking improved"
            if sec.country in (curr_countries - prev_countries):
                cause = "UNIVERSE_CHANGE"
                reason = f"Qualified from newly enabled market: {sec.country}"
            entered_list.append({
                "ticker": sec.ticker,
                "name": sec.company_name,
                "country": sec.country,
                "sector": sec.sector,
                "current_rank": sec.rank,
                "score": sec.score,
                "cause": cause,
                "reason": reason,
            })

        # Cause attribution for exited
        exited_list = []
        for cid in exited_ids:
            sec = prev_top20_ids[cid]
            cause = "DISPLACEMENT"
            reason = "Displaced by higher scoring companies"
            # Check if knocked out by a tightened gate
            for r_diff in rule_diffs:
                if "Threshold:" in r_diff or "Mode:" in r_diff:
                    cause = "RULE_CHANGE"
                    reason = f"Eliminated due to rule change: {r_diff.split(':')[0]}"
                    break
            exited_list.append({
                "ticker": sec.ticker,
                "name": sec.company_name,
                "country": sec.country,
                "sector": sec.sector,
                "previous_rank": sec.rank,
                "score": sec.score,
                "cause": cause,
                "reason": reason,
            })

        retained_list = []
        for cid in retained_ids:
            curr_sec = curr_top20_ids[cid]
            prev_sec = prev_top20_ids[cid]
            rank_delta = prev_sec.rank - curr_sec.rank
            score_delta = curr_sec.score - prev_sec.score
            retained_list.append({
                "ticker": curr_sec.ticker,
                "name": curr_sec.company_name,
                "current_rank": curr_sec.rank,
                "previous_rank": prev_sec.rank,
                "rank_delta": rank_delta,
                "score_delta": score_delta,
            })

        return {
            "current_run_id": curr_run.run_id,
            "previous_run_id": prev_run.run_id,
            "current_profile": curr_run.profile_name,
            "previous_profile": prev_run.profile_name,
            "rule_diffs": rule_diffs,
            "entered_count": len(entered_list),
            "exited_count": len(exited_list),
            "retained_count": len(retained_list),
            "entered": entered_list,
            "exited": exited_list,
            "retained": retained_list,
        }


# Global funnel service instance
funnel_service = FunnelService()

