"""Rule and profile management API routes.

Provides full CRUD operations for screening profiles, rule thresholds,
and returns the catalog specification with realistic limits.
"""

from datetime import datetime, timezone
import logging
from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status

from app.core.logging import DiagnosticLogger
from app.models.rule import RuleRecord, RuleVersionRecord
from app.repositories.rule_repository import rule_repository
from app.schemas.rule import (
    CreateProfileRequest,
    MetricCatalogSpecification,
    RuleMetricItem,
    RuleProfileSchema,
    STANDARD_RULE_CATALOG,
    UpdateProfileRequest,
)

logger = DiagnosticLogger("rules_api")
router = APIRouter(prefix="/api/rules", tags=["rules"])


def _record_to_schema(version: RuleVersionRecord) -> RuleProfileSchema:
    """Map database RuleVersionRecord to API RuleProfileSchema."""
    rule_items: List[RuleMetricItem] = [
        RuleMetricItem(
            id=r.metric_name,
            name=r.label,
            category=r.category,
            mode=r.mode,  # type: ignore
            condition=r.condition,
            value=r.threshold_value,
            value_display=r.threshold_display,
            weight=r.weight,
        )
        for r in version.rules
    ]
    return RuleProfileSchema(
        version_id=version.version_id,
        profile_name=version.profile_name,
        version_number=version.version_number,
        is_active=version.is_active,
        description=version.description,
        sector_limits=version.sector_limits,
        diversification_rules=version.diversification_rules,
        changes=version.changes or [],
        selected_countries=version.selected_countries or [],
        rules=rule_items,
        created_at=version.created_at,
        updated_at=version.updated_at,
    )


@router.get("/catalog", response_model=List[MetricCatalogSpecification])
def get_rule_catalog():
    """Return the official specification for all 16 screening metrics, units, and limits."""
    return STANDARD_RULE_CATALOG


@router.get("/profiles", response_model=List[RuleProfileSchema])
def list_profiles():
    """Retrieve all saved screening strategy profiles from PostgreSQL."""
    versions = rule_repository.list_versions()
    return [_record_to_schema(v) for v in versions]


@router.get("/profiles/active", response_model=RuleProfileSchema)
def get_active_profile():
    """Retrieve the currently active screening profile."""
    active = rule_repository.get_active_version()
    if not active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active screening profile found."
        )
    return _record_to_schema(active)


@router.get("/profiles/{version_id}", response_model=RuleProfileSchema)
def get_profile(version_id: str):
    """Retrieve a specific profile by its version ID."""
    version = rule_repository.get_version_by_id(version_id)
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile '{version_id}' not found."
        )
    return _record_to_schema(version)


@router.post("/profiles", response_model=RuleProfileSchema, status_code=status.HTTP_201_CREATED)
def create_profile(request: CreateProfileRequest):
    """Create a new rule strategy profile in PostgreSQL."""
    now = datetime.now(timezone.utc)
    version_id = f"prof-{uuid4().hex[:8]}"

    changes = list(request.changes or [])
    if not changes:
        all_versions = rule_repository.list_versions()
        matching_prev = [v for v in all_versions if v.profile_name.lower().strip() == request.profile_name.lower().strip()]
        if matching_prev:
            prev_ver = matching_prev[0]
            prev_rules = {r.metric_name: r for r in prev_ver.rules}
            curr_rules = {r.id: r for r in request.rules}
            diffs = []
            for m_id, curr_r in curr_rules.items():
                if m_id in prev_rules:
                    prev_r = prev_rules[m_id]
                    parts = []
                    if prev_r.mode != curr_r.mode:
                        parts.append(f"Mode: {curr_r.mode} (was {prev_r.mode})")
                    if prev_r.condition != curr_r.condition or prev_r.threshold_value != curr_r.value:
                        parts.append(f"Threshold: {curr_r.condition} {curr_r.value} (was {prev_r.condition} {prev_r.threshold_value})")
                    if prev_r.weight != curr_r.weight and curr_r.mode in ("Score", "Both"):
                        parts.append(f"Weight: {curr_r.weight}% (was {prev_r.weight}%)")
                    if parts:
                        diffs.append(f"{curr_r.name}: {', '.join(parts)}")
                else:
                    if curr_r.mode != "Off":
                        diffs.append(f"Added rule {curr_r.name}: {curr_r.mode}, {curr_r.condition} {curr_r.value}")
            for m_id, prev_r in prev_rules.items():
                if m_id not in curr_rules and prev_r.mode != "Off":
                    diffs.append(f"Removed rule: {prev_r.label}")

            # Check country differences
            prev_countries = set(prev_ver.selected_countries or [])
            curr_countries = set(request.selected_countries or [])
            added_countries = curr_countries - prev_countries
            removed_countries = prev_countries - curr_countries
            for c in sorted(added_countries):
                diffs.append(f"Added country: {c}")
            for c in sorted(removed_countries):
                diffs.append(f"Removed country: {c}")

            changes = diffs if diffs else ["No threshold changes compared to previous version."]
        else:
            active_count = sum(1 for r in request.rules if r.mode != "Off")
            changes = [f"Initial profile created with {active_count} active rules."]

    version_record = RuleVersionRecord(
        version_id=version_id,
        profile_name=request.profile_name,
        version_number=request.version_number,
        is_active=request.is_active,
        description=request.description,
        sector_limits=request.sector_limits,
        diversification_rules=request.diversification_rules,
        changes=changes,
        selected_countries=request.selected_countries or [],
        created_at=now,
        updated_at=now,
    )
    rule_repository.save_version(version_record)

    # Save individual metric rules
    rules_to_save: List[RuleMetricItem] = request.rules
    if not rules_to_save:
        # Populate with standard defaults if none provided
        for spec in STANDARD_RULE_CATALOG:
            rule_repository.save_rule(
                RuleRecord(
                    rule_id=f"rule-{version_id}-{spec.id}",
                    version_id=version_id,
                    metric_name=spec.id,
                    label=spec.name,
                    category=spec.category,
                    condition=spec.default_condition,
                    threshold_value=spec.default_value,
                    threshold_display=spec.default_display,
                    mode="Both" if spec.default_weight > 0 else "Off",
                    weight=spec.default_weight,
                    created_at=now,
                )
            )
    else:
        for r in rules_to_save:
            rule_repository.save_rule(
                RuleRecord(
                    rule_id=f"rule-{version_id}-{r.id}",
                    version_id=version_id,
                    metric_name=r.id,
                    label=r.name,
                    category=r.category,
                    condition=r.condition,
                    threshold_value=r.value,
                    threshold_display=r.value_display or f"{r.condition} {r.value}",
                    mode=r.mode,
                    weight=r.weight,
                    created_at=now,
                )
            )

    saved_version = rule_repository.get_version_by_id(version_id)
    if not saved_version:
        raise HTTPException(status_code=500, detail="Failed to retrieve created profile.")

    logger.rule_info("CREATE", request.profile_name, f"Created new rule profile '{version_id}'")
    return _record_to_schema(saved_version)


@router.put("/profiles/{version_id}", response_model=RuleProfileSchema)
def update_profile(version_id: str, request: UpdateProfileRequest):
    """Update thresholds, weights, and limits of an existing profile."""
    existing = rule_repository.get_version_by_id(version_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile '{version_id}' not found."
        )

    now = datetime.now(timezone.utc)
    updated_record = RuleVersionRecord(
        version_id=version_id,
        profile_name=request.profile_name or existing.profile_name,
        version_number=existing.version_number,
        is_active=existing.is_active,
        description=request.description if request.description is not None else existing.description,
        sector_limits=request.sector_limits if request.sector_limits is not None else existing.sector_limits,
        diversification_rules=request.diversification_rules if request.diversification_rules is not None else existing.diversification_rules,
        changes=request.changes if request.changes is not None else existing.changes,
        selected_countries=request.selected_countries if request.selected_countries is not None else existing.selected_countries,
        created_at=existing.created_at,
        updated_at=now,
    )
    rule_repository.save_version(updated_record)

    # If rules array provided, replace rules
    if request.rules is not None:
        rule_repository.delete_rules_for_version(version_id)
        for r in request.rules:
            rule_repository.save_rule(
                RuleRecord(
                    rule_id=f"rule-{version_id}-{r.id}",
                    version_id=version_id,
                    metric_name=r.id,
                    label=r.name,
                    category=r.category,
                    condition=r.condition,
                    threshold_value=r.value,
                    threshold_display=r.value_display or f"{r.condition} {r.value}",
                    mode=r.mode,
                    weight=r.weight,
                    created_at=now,
                )
            )

    saved = rule_repository.get_version_by_id(version_id)
    if not saved:
        raise HTTPException(status_code=500, detail="Failed to retrieve updated profile.")

    logger.rule_info("UPDATE", saved.profile_name, f"Updated profile '{version_id}'")
    return _record_to_schema(saved)


@router.put("/profiles/{version_id}/activate", response_model=RuleProfileSchema)
def activate_profile(version_id: str):
    """Set a strategy profile as active and deactivate all other profiles."""
    existing = rule_repository.get_version_by_id(version_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile '{version_id}' not found."
        )

    rule_repository.activate_version(version_id)
    updated = rule_repository.get_version_by_id(version_id)
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to activate profile.")

    logger.rule_info("ACTIVATE", updated.profile_name, f"Activated rule profile '{version_id}'")
    return _record_to_schema(updated)


@router.delete("/profiles/{version_id}", status_code=status.HTTP_200_OK)
def delete_profile(version_id: str):
    """Delete a profile and all its criteria from PostgreSQL."""
    existing = rule_repository.get_version_by_id(version_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile '{version_id}' not found."
        )

    rule_repository.delete_version(version_id)
    logger.rule_info("DELETE", existing.profile_name, f"Deleted profile '{version_id}'")
    return {"status": "deleted", "version_id": version_id, "profile_name": existing.profile_name}
