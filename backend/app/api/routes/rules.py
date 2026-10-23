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
        rules=rule_items,
        created_at=version.created_at,
        updated_at=version.updated_at,
    )


def _seed_default_profile_if_empty() -> None:
    """Seed a default 'Conservative Value' profile if DB is completely empty."""
    existing = rule_repository.list_versions()
    if not existing:
        now = datetime.now(timezone.utc)
        default_version = RuleVersionRecord(
            version_id="prof-conservative-v1",
            profile_name="Conservative Value",
            version_number="1.0",
            is_active=True,
            description="Focuses on profitable cash generative firms with leverage below 3.0x",
            sector_limits={"Information Technology": 3.0, "Energy": 3.5, "Health Care": 3.0},
            diversification_rules={"max_sector_weight": 25.0},
            created_at=now,
            updated_at=now,
        )
        rule_repository.save_version(default_version)

        # Seed standard default rules
        for spec in STANDARD_RULE_CATALOG:
            rule_repository.save_rule(
                RuleRecord(
                    rule_id=f"rule-{default_version.version_id}-{spec.id}",
                    version_id=default_version.version_id,
                    metric_name=spec.id,
                    label=spec.name,
                    category=spec.category,
                    condition=spec.default_condition,
                    threshold_value=spec.default_value,
                    threshold_display=spec.default_display,
                    mode="Both" if spec.default_weight > 0 else "Req.",
                    weight=spec.default_weight,
                    created_at=now,
                )
            )


@router.get("/catalog", response_model=List[MetricCatalogSpecification])
def get_rule_catalog():
    """Return the official specification for all 16 screening metrics, units, and limits."""
    return STANDARD_RULE_CATALOG


@router.get("/profiles", response_model=List[RuleProfileSchema])
def list_profiles():
    """Retrieve all saved screening strategy profiles from PostgreSQL."""
    _seed_default_profile_if_empty()
    versions = rule_repository.list_versions()
    return [_record_to_schema(v) for v in versions]


@router.get("/profiles/active", response_model=RuleProfileSchema)
def get_active_profile():
    """Retrieve the currently active screening profile."""
    _seed_default_profile_if_empty()
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

    version_record = RuleVersionRecord(
        version_id=version_id,
        profile_name=request.profile_name,
        version_number=request.version_number,
        is_active=request.is_active,
        description=request.description,
        sector_limits=request.sector_limits,
        diversification_rules=request.diversification_rules,
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
