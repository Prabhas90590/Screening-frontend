"""Phase 11: Versioned Rule Engine.

Evaluates companies against versioned rule profiles across all 4 modes:
  - 'Off': Bypassed completely.
  - 'Req.' (Gate): Strict knock-out criteria.
  - 'Score': Quality ranking points (0 to weight).
  - 'Both': Must pass knock-out gate AND earns quality ranking points.

Features:
  - Bank exemption: Financial institutions are exempt from leverage gates without penalty.
  - Weight auto-normalization: Total score is strictly scaled to 0-100 regardless of active weight sum.
  - Near-miss detection: Flags securities that failed by <= 5% or failed only 1 gate.
  - Complete explainability: Produces itemized score breakdown for frontend drawer.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from app.core.logging import DiagnosticLogger
from app.models.company_metrics import CompanyMetricsRecord
from app.models.rule import RuleRecord, RuleVersionRecord
from app.rules.rule_evaluator import calculate_rule_score, evaluate_condition
from app.schemas.rule import RuleMetricItem, RuleProfileSchema
from app.schemas.screening import MetricScoreBreakdownItem

logger = DiagnosticLogger("rule_engine")

# Metrics classified as preliminary Size & Liquidity floors
FLOOR_METRIC_KEYS = {
    "market_cap",
    "market_cap_usd",
    "price_usd",
    "avg_volume",
    "avg_daily_volume",
    "avg_traded_value",
    "avg_daily_traded_value",
}


@dataclass
class RuleEvaluationDetail:
    """Detailed audit verdict for a single rule evaluated on a company."""
    rule_id: str
    metric_name: str
    label: str
    category: str
    mode: str
    condition: str
    threshold_value: float
    actual_value: Optional[float]
    passed: bool
    is_exempt: bool = False
    weight: float = 0.0
    points_earned: float = 0.0
    max_points: float = 0.0
    failure_reason: Optional[str] = None
    status: str = "full"  # full, threshold, miss, off, exempt


@dataclass
class CompanyRuleEvaluation:
    """Complete rule evaluation verdict for one company against a profile."""
    canonical_company_id: str
    ticker: str
    profile_version_id: str
    profile_name: str

    # Stage outcomes
    passed_floors: bool = True
    passed_gates: bool = True
    passed_overall: bool = True

    # Scoring (0 to 100 normalized)
    total_score: float = 0.0
    raw_points_earned: float = 0.0
    total_active_weight: float = 0.0

    # Near-miss analytics (for Phase 12)
    near_miss: bool = False
    near_miss_reason: Optional[str] = None
    failed_gate_count: int = 0

    # Detailed collections
    evaluations: List[RuleEvaluationDetail] = field(default_factory=list)
    score_breakdown: List[MetricScoreBreakdownItem] = field(default_factory=list)
    failed_rules: List[RuleEvaluationDetail] = field(default_factory=list)
    passed_rules: List[RuleEvaluationDetail] = field(default_factory=list)


class RuleEngine:
    """
    Stateless versioned rule evaluation engine.

    Executes screening profiles against company metrics. Pure logic with
    deterministic outcomes for auditability and replay.
    """

    @classmethod
    def evaluate_company(
        cls,
        metrics: CompanyMetricsRecord,
        profile: Union[RuleVersionRecord, RuleProfileSchema],
        is_bank: bool = False,
    ) -> CompanyRuleEvaluation:
        """Evaluate a single company against a rule profile.

        Args:
            metrics: Standardized metrics record for the company
            profile: Rule profile configuration containing rules to evaluate
            is_bank: Flag indicating bank status for leverage exemptions

        Returns:
            CompanyRuleEvaluation with stage passes, scores, and breakdowns
        """
        if isinstance(profile, list):
            raw_rules = profile
            version_id = "prof-custom"
            profile_name = "Custom Strategy"
        else:
            version_id = getattr(profile, "version_id", "prof-custom")
            profile_name = getattr(profile, "profile_name", "Custom Strategy")
            raw_rules = getattr(profile, "rules", []) or []

        output = CompanyRuleEvaluation(
            canonical_company_id=metrics.canonical_company_id,
            ticker=metrics.ticker,
            profile_version_id=version_id,
            profile_name=profile_name,
        )

        logger.rule_info("START", metrics.ticker, f"Evaluating against profile '{profile_name}' ({version_id})")

        sum_points_earned = 0.0
        sum_active_weights = 0.0
        failed_gates = []
        near_miss_candidates = []

        for r in raw_rules:
            _gv = lambda k, d=None: r.get(k, d) if isinstance(r, dict) else getattr(r, k, d)
            metric_key = _gv("metric_name") or _gv("id", "")
            norm_key = metric_key.lower().replace("-", "_")
            rule_id = _gv("rule_id") or _gv("id", norm_key)
            label = _gv("label") or _gv("name", metric_key)
            category = _gv("category", "Valuation")
            raw_mode = _gv("mode", "Both")
            if raw_mode:
                m_str = str(raw_mode).lower().strip()
                if m_str in ("gate", "req", "req."):
                    mode = "Req."
                elif m_str in ("score", "scoring"):
                    mode = "Score"
                elif m_str in ("both", "all"):
                    mode = "Both"
                elif m_str in ("off", "disabled", "false"):
                    mode = "Off"
                else:
                    mode = raw_mode
            else:
                mode = "Both"
            condition = _gv("condition", ">=")
            threshold = float(_gv("threshold_value") if _gv("threshold_value") is not None else (_gv("value", 0.0) or 0.0))
            weight = float(_gv("weight", 0.0) or 0.0)

            # Skip Off rules
            if mode == "Off":
                continue

            # Look up actual value on company_metrics record
            actual_val = cls._extract_metric_value(metrics, norm_key)

            # Bank exemption check for leverage metrics
            is_exempt = False
            if is_bank and ("debt" in norm_key or "leverage" in norm_key):
                is_exempt = True

            # 1. Evaluate condition (Pass / Fail)
            passed, failure_reason = evaluate_condition(
                actual_value=actual_val,
                condition=condition,
                threshold=threshold,
                is_exempt=is_exempt,
            )

            # 2. Calculate score points (0 to weight)
            effective_weight = weight if mode in ("Score", "Both") else 0.0
            points_earned, status = calculate_rule_score(
                actual_value=actual_val,
                condition=condition,
                threshold=threshold,
                weight=effective_weight,
                metric_name=norm_key,
                is_exempt=is_exempt,
            )

            if mode in ("Score", "Both"):
                sum_points_earned += points_earned
                sum_active_weights += effective_weight

            # 3. Handle Gate requirements (Req. and Both)
            is_gate = mode in ("Req.", "Both")
            if is_gate and not passed and not is_exempt:
                is_floor = norm_key in FLOOR_METRIC_KEYS
                if is_floor:
                    output.passed_floors = False
                else:
                    output.passed_gates = False
                    failed_gates.append(label)

                # Check for near-miss (failed within 5% margin)
                if actual_val is not None and threshold != 0:
                    margin_pct = abs(actual_val - threshold) / abs(threshold) * 100
                    if margin_pct <= 5.0:
                        near_miss_candidates.append(f"{label} ({margin_pct:.1f}% margin)")

            # 4. Construct detailed item verdict
            detail = RuleEvaluationDetail(
                rule_id=rule_id,
                metric_name=norm_key,
                label=label,
                category=category,
                mode=mode,
                condition=condition,
                threshold_value=threshold,
                actual_value=actual_val,
                passed=passed,
                is_exempt=is_exempt,
                weight=effective_weight,
                points_earned=points_earned,
                max_points=effective_weight,
                failure_reason=failure_reason,
                status=status,
            )

            output.evaluations.append(detail)
            if passed:
                output.passed_rules.append(detail)
            else:
                output.failed_rules.append(detail)

            # 5. Build frontend Score Breakdown Item
            val_display = f"{actual_val:.2f}" if actual_val is not None else "N/A"
            if "market_cap" in norm_key:
                val_display = f"${(actual_val or 0) / 1e9:.1f}B"
            elif "pe" in norm_key or "ev" in norm_key or "peg" in norm_key:
                val_display = f"{actual_val:.2f}x" if actual_val is not None else "N/A"
            elif "pct" in norm_key or "growth" in norm_key or "yield" in norm_key:
                val_display = f"{actual_val:.1f}%" if actual_val is not None else "N/A"

            score_pct = (points_earned / effective_weight * 100) if effective_weight > 0 else 0.0

            output.score_breakdown.append(
                MetricScoreBreakdownItem(
                    name=label,
                    score=points_earned,
                    max_score=effective_weight,
                    value_display=val_display,
                    benchmark_display=f"{condition} {threshold}",
                    percentage=round(score_pct, 1),
                    status="exempt" if is_exempt else status,  # type: ignore
                )
            )

        # Final aggregate score normalization to strictly 0..100 scale
        if sum_active_weights > 0:
            output.total_score = round((sum_points_earned / sum_active_weights) * 100, 1)
        else:
            output.total_score = 0.0

        output.raw_points_earned = round(sum_points_earned, 2)
        output.total_active_weight = round(sum_active_weights, 2)
        output.failed_gate_count = len(failed_gates)
        output.passed_overall = output.passed_floors and output.passed_gates

        # Near miss classification (survived floors, but failed exactly 1 gate or by <= 5%)
        if not output.passed_gates and output.passed_floors:
            if output.failed_gate_count == 1:
                output.near_miss = True
                output.near_miss_reason = f"Failed only 1 gate: {failed_gates[0]}"
            elif near_miss_candidates:
                output.near_miss = True
                output.near_miss_reason = f"Near threshold miss: {', '.join(near_miss_candidates)}"

        logger.rule_info(
            "VERDICT",
            metrics.ticker,
            f"Overall={'PASS' if output.passed_overall else 'FAIL'} | "
            f"Score={output.total_score}/100 | "
            f"Floors={'PASS' if output.passed_floors else 'FAIL'} | "
            f"Gates={'PASS' if output.passed_gates else f'FAIL({output.failed_gate_count})'} | "
            f"NearMiss={output.near_miss}"
        )

        return output

    @classmethod
    def evaluate_batch(
        cls,
        companies_metrics: List[CompanyMetricsRecord],
        profile: Union[RuleVersionRecord, RuleProfileSchema],
        bank_ids: Optional[set] = None,
    ) -> List[CompanyRuleEvaluation]:
        """Evaluate a batch of companies, sort by score descending, and assign ranks.

        Args:
            companies_metrics: List of metric records for all evaluated companies
            profile: Rule profile configuration
            bank_ids: Set of canonical_company_id strings that are banks

        Returns:
            List of CompanyRuleEvaluation objects sorted by total_score descending
        """
        bank_set = bank_ids or set()
        results: List[CompanyRuleEvaluation] = []

        for m in companies_metrics:
            is_bank = m.canonical_company_id in bank_set
            eval_res = cls.evaluate_company(metrics=m, profile=profile, is_bank=is_bank)
            results.append(eval_res)

        # Sort: Passing companies first (by score DESC), then Near-misses, then Failures
        results.sort(
            key=lambda x: (
                1 if x.passed_overall else (0.5 if x.near_miss else 0),
                x.total_score,
            ),
            reverse=True,
        )

        return results

    @staticmethod
    def _extract_metric_value(metrics: CompanyMetricsRecord, key: str) -> Optional[float]:
        """Resolve metric key string to numeric value on CompanyMetricsRecord."""
        def _parse_val(val: Any) -> Optional[float]:
            if val is None:
                return None
            if isinstance(val, (int, float)):
                return float(val)
            if isinstance(val, str):
                v_clean = val.strip().lower()
                if v_clean == "high":
                    return 3.0
                elif v_clean == "medium":
                    return 2.0
                elif v_clean == "low":
                    return 1.0
                try:
                    return float(val)
                except ValueError:
                    return None
            return None

        # Direct attribute match
        if hasattr(metrics, key):
            val = getattr(metrics, key)
            return _parse_val(val)

        # Common aliased mappings
        alias_map = {
            "market_cap": "market_cap_usd",
            "price": "price_usd",
            "avg_volume": "avg_daily_volume",
            "avg_traded_value": "avg_daily_traded_value",
            "peg": "peg_ratio",
            "forward_pe_vs_s_p_500": "pe_vs_benchmark",
            "pe_vs_benchmark": "pe_vs_benchmark",
            "net_debt_ebitda": "net_debt_ebitda",
            "dividend_yield": "dividend_yield",
            "eps_growth": "eps_growth_fwd",
            "revenue_growth": "revenue_growth_fwd",
            "data_confidence": "data_confidence",
        }

        attr = alias_map.get(key)
        if attr and hasattr(metrics, attr):
            val = getattr(metrics, attr)
            return _parse_val(val)

        # Fuzzy lookup
        for prop in dir(metrics):
            if key in prop.lower():
                val = getattr(metrics, prop)
                res = _parse_val(val)
                if res is not None:
                    return res

        return None


# Global singleton instance
rule_engine = RuleEngine()
