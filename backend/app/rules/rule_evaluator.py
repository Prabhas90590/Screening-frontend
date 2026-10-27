"""Rule Evaluator - Pure condition comparison and score interpolation logic.

Handles mathematical comparisons, bank exemptions, near-miss margin detection,
and proportional linear score distribution across metrics.
"""

from typing import Optional, Tuple


def evaluate_condition(
    actual_value: Optional[float],
    condition: str,
    threshold: float,
    is_exempt: bool = False,
) -> Tuple[bool, Optional[str]]:
    """Evaluate whether an actual value satisfies a rule threshold.

    Args:
        actual_value: Measured company metric value (or None if missing)
        condition: Operator string ('>=', '<=', '=', '>', '<')
        threshold: Required numeric cut-off
        is_exempt: Flag indicating the company is exempt (e.g. Banks for leverage)

    Returns:
        (passed, failure_reason)
    """
    if is_exempt:
        return True, None

    if actual_value is None:
        return False, "Metric value is missing or could not be calculated"

    cond = condition.strip()

    if cond in (">=", "discount"):
        passed = actual_value >= threshold
        reason = None if passed else f"Value {actual_value:.2f} is below required minimum >={threshold:.2f}"
        return passed, reason

    elif cond == "<=":
        passed = actual_value <= threshold
        reason = None if passed else f"Value {actual_value:.2f} exceeds required maximum <={threshold:.2f}"
        return passed, reason

    elif cond in ("=", "=="):
        passed = abs(actual_value - threshold) < 1e-4
        reason = None if passed else f"Value {actual_value:.2f} does not match required ={threshold:.2f}"
        return passed, reason

    elif cond == ">":
        passed = actual_value > threshold
        reason = None if passed else f"Value {actual_value:.2f} is not strictly greater than >{threshold:.2f}"
        return passed, reason

    elif cond == "<":
        passed = actual_value < threshold
        reason = None if passed else f"Value {actual_value:.2f} is not strictly less than <{threshold:.2f}"
        return passed, reason

    else:
        # Default fallback to >=
        passed = actual_value >= threshold
        return passed, None if passed else f"Value {actual_value} failed {cond} {threshold}"


def calculate_rule_score(
    actual_value: Optional[float],
    condition: str,
    threshold: float,
    weight: float,
    metric_name: str = "",
    is_exempt: bool = False,
) -> Tuple[float, str]:
    """Calculate points earned (0.0 to weight) and score status.

    Status categories returned:
      - 'full': Outperformed benchmark or achieved top tier score
      - 'threshold': Passed threshold, awarded base/moderate points
      - 'miss': Failed threshold or within near-miss zone (0 points)
      - 'off': Rule disabled or 0 weight
      - 'exempt': Metric exempt for company type (awarded neutral benchmark score)

    Args:
        actual_value: Measured company metric value
        condition: Operator string ('>=', '<=', etc.)
        threshold: Numeric cut-off
        weight: Maximum points allocated to this rule
        metric_name: Key for domain-specific best benchmarks
        is_exempt: Bank exemption flag

    Returns:
        (points_earned, status)
    """
    if weight <= 0:
        return 0.0, "off"

    if is_exempt:
        # Banks get fair neutral score (75% of weight) so they aren't penalized
        return round(weight * 0.75, 2), "exempt"

    if actual_value is None:
        return 0.0, "miss"

    cond = condition.strip()

    # Case A: Lower is better (e.g. Forward P/E <= 25, EV/EBITDA <= 15, Beta <= 1.2)
    if cond == "<=":
        if actual_value <= threshold:
            # Passed! Scale between 50% (at threshold) and 100% (at excellent benchmark)
            # Benchmark target is 40% of threshold (e.g., if threshold is 25x, target is 10x)
            target = max(threshold * 0.4, 0.0)
            if actual_value <= target:
                return round(weight, 2), "full"
            else:
                # Linear scale between target (100%) and threshold (50%)
                ratio = (threshold - actual_value) / max(threshold - target, 1e-4)
                points = weight * (0.5 + 0.5 * ratio)
                status = "full" if points >= weight * 0.85 else "threshold"
                return round(min(weight, max(0.0, points)), 2), status
        else:
            return 0.0, "miss"

    # Case B: Higher is better (e.g. EPS Growth >= 10%, Dividend Yield >= 2%, Market Cap >= 500M)
    elif cond in (">=", ">", "discount"):
        if actual_value >= threshold:
            # Passed! Benchmark target is 2x the threshold
            target = threshold * 2.0 if threshold > 0 else threshold + 10.0
            if actual_value >= target:
                return round(weight, 2), "full"
            else:
                # Linear scale between threshold (50%) and target (100%)
                ratio = (actual_value - threshold) / max(target - threshold, 1e-4)
                points = weight * (0.5 + 0.5 * ratio)
                status = "full" if points >= weight * 0.85 else "threshold"
                return round(min(weight, max(0.0, points)), 2), status
        else:
            return 0.0, "miss"

    # Case C: Equality (e.g. Data Confidence == 3.0)
    elif cond in ("=", "=="):
        if abs(actual_value - threshold) < 1e-4:
            return round(weight, 2), "full"
        else:
            return 0.0, "miss"

    # Default fallback
    return 0.0, "miss"

