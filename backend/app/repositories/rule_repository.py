"""Repository for screening rule profiles and individual metrics in PostgreSQL."""

from datetime import datetime
import json
import logging
from typing import Any, List, Optional

from app.db.connection import db_manager
from app.models.rule import RuleRecord, RuleVersionRecord

logger = logging.getLogger("app.repositories.rule")


class RuleRepository:
    """SQL repository for 'rule_versions' and 'rules' tables in PostgreSQL."""

    def __init__(self):
        db_manager.init_tables()

    # -------------------------------------------------------------
    # RULE VERSIONS / PROFILES
    # -------------------------------------------------------------

    def save_version(self, version: RuleVersionRecord) -> str:
        """Insert or update a rule profile version."""
        conn = db_manager.get_connection()
        target_owner = version.owner_email
        target_user_id = version.user_id

        insert_sql = """
            INSERT INTO rule_versions (
                version_id, profile_name, version_number, is_active,
                description, sector_limits, diversification_rules, changes, selected_countries, owner_email, user_id, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (version_id) DO UPDATE SET
                profile_name = EXCLUDED.profile_name,
                is_active = EXCLUDED.is_active,
                description = EXCLUDED.description,
                sector_limits = EXCLUDED.sector_limits,
                diversification_rules = EXCLUDED.diversification_rules,
                changes = EXCLUDED.changes,
                selected_countries = EXCLUDED.selected_countries,
                owner_email = EXCLUDED.owner_email,
                user_id = EXCLUDED.user_id,
                updated_at = EXCLUDED.updated_at;
        """

        sector_limits_json = json.dumps(version.sector_limits)
        diversification_json = json.dumps(version.diversification_rules)
        changes_json = json.dumps(version.changes or [])
        countries_json = json.dumps(version.selected_countries or [])

        values = (
            version.version_id,
            version.profile_name,
            version.version_number,
            version.is_active,
            version.description,
            sector_limits_json,
            diversification_json,
            changes_json,
            countries_json,
            target_owner,
            target_user_id,
            version.created_at,
            version.updated_at,
        )

        try:
            cursor = conn.cursor()
            cursor.execute(insert_sql, values)

            # If this is marked active, deactivate other profiles for THIS OWNER ONLY
            if version.is_active and target_owner:
                deact_sql = "UPDATE rule_versions SET is_active = FALSE WHERE version_id != %s AND LOWER(owner_email) = LOWER(%s)"
                cursor.execute(deact_sql, (version.version_id, target_owner))

            conn.commit()
            return version.version_id
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to save rule version '{version.version_id}': {e}")
            raise
        finally:
            conn.close()

    def get_active_version(self, owner_email: Optional[str] = None, user_id: Optional[str] = None) -> Optional[RuleVersionRecord]:
        """Fetch the currently active screening profile for the specified owner."""
        if not owner_email and not user_id:
            return None

        conn = db_manager.get_connection()

        if user_id and owner_email:
            query = (
                "SELECT version_id, profile_name, version_number, is_active, description, sector_limits, "
                "diversification_rules, changes, selected_countries, owner_email, created_at, updated_at, user_id "
                "FROM rule_versions WHERE is_active = TRUE AND (user_id = %s OR LOWER(owner_email) = LOWER(%s)) LIMIT 1"
            )
            params = (user_id, owner_email)
        elif user_id:
            query = (
                "SELECT version_id, profile_name, version_number, is_active, description, sector_limits, "
                "diversification_rules, changes, selected_countries, owner_email, created_at, updated_at, user_id "
                "FROM rule_versions WHERE is_active = TRUE AND user_id = %s LIMIT 1"
            )
            params = (user_id,)
        else:
            query = (
                "SELECT version_id, profile_name, version_number, is_active, description, sector_limits, "
                "diversification_rules, changes, selected_countries, owner_email, created_at, updated_at, user_id "
                "FROM rule_versions WHERE is_active = TRUE AND LOWER(owner_email) = LOWER(%s) LIMIT 1"
            )
            params = (owner_email,)

        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            row = cursor.fetchone()
            if not row:
                versions = self.list_versions(owner_email=owner_email, user_id=user_id)
                return versions[0] if versions else None
            version = self._row_to_version(row)
            version.rules = self.get_rules_for_version(version.version_id)
            return version
        finally:
            conn.close()

    def list_versions(self, owner_email: Optional[str] = None, user_id: Optional[str] = None) -> List[RuleVersionRecord]:
        """List all saved rule profiles for the specified owner."""
        if not owner_email and not user_id:
            return []

        conn = db_manager.get_connection()

        if user_id and owner_email:
            query = (
                "SELECT version_id, profile_name, version_number, is_active, description, sector_limits, "
                "diversification_rules, changes, selected_countries, owner_email, created_at, updated_at, user_id "
                "FROM rule_versions WHERE (user_id = %s OR LOWER(owner_email) = LOWER(%s)) ORDER BY is_active DESC, updated_at DESC"
            )
            params = (user_id, owner_email)
        elif user_id:
            query = (
                "SELECT version_id, profile_name, version_number, is_active, description, sector_limits, "
                "diversification_rules, changes, selected_countries, owner_email, created_at, updated_at, user_id "
                "FROM rule_versions WHERE user_id = %s ORDER BY is_active DESC, updated_at DESC"
            )
            params = (user_id,)
        else:
            query = (
                "SELECT version_id, profile_name, version_number, is_active, description, sector_limits, "
                "diversification_rules, changes, selected_countries, owner_email, created_at, updated_at, user_id "
                "FROM rule_versions WHERE LOWER(owner_email) = LOWER(%s) ORDER BY is_active DESC, updated_at DESC"
            )
            params = (owner_email,)

        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            if not rows:
                return []

            versions = [self._row_to_version(row) for row in rows]
            for v in versions:
                v.rules = self.get_rules_for_version(v.version_id)
            return versions
        finally:
            conn.close()

    def get_version_by_id(self, version_id: str, owner_email: Optional[str] = None, user_id: Optional[str] = None) -> Optional[RuleVersionRecord]:
        """Fetch a specific rule profile by its version ID, optionally scoped to owner."""
        conn = db_manager.get_connection()

        if user_id and owner_email:
            query = (
                "SELECT version_id, profile_name, version_number, is_active, description, sector_limits, "
                "diversification_rules, changes, selected_countries, owner_email, created_at, updated_at, user_id "
                "FROM rule_versions WHERE version_id = %s AND (user_id = %s OR LOWER(owner_email) = LOWER(%s))"
            )
            params = (version_id, user_id, owner_email)
        elif user_id:
            query = (
                "SELECT version_id, profile_name, version_number, is_active, description, sector_limits, "
                "diversification_rules, changes, selected_countries, owner_email, created_at, updated_at, user_id "
                "FROM rule_versions WHERE version_id = %s AND user_id = %s"
            )
            params = (version_id, user_id)
        elif owner_email:
            query = (
                "SELECT version_id, profile_name, version_number, is_active, description, sector_limits, "
                "diversification_rules, changes, selected_countries, owner_email, created_at, updated_at, user_id "
                "FROM rule_versions WHERE version_id = %s AND LOWER(owner_email) = LOWER(%s)"
            )
            params = (version_id, owner_email)
        else:
            query = (
                "SELECT version_id, profile_name, version_number, is_active, description, sector_limits, "
                "diversification_rules, changes, selected_countries, owner_email, created_at, updated_at, user_id "
                "FROM rule_versions WHERE version_id = %s"
            )
            params = (version_id,)

        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            row = cursor.fetchone()
            if not row:
                return None
            version = self._row_to_version(row)
            version.rules = self.get_rules_for_version(version.version_id)
            return version
        finally:
            conn.close()

    def activate_version(self, version_id: str, owner_email: Optional[str] = None) -> bool:
        """Mark a profile as active and deactivate all other profiles for this owner."""
        if not owner_email:
            return False

        conn = db_manager.get_connection()
        target_owner = owner_email

        try:
            cursor = conn.cursor()
            deact_sql = "UPDATE rule_versions SET is_active = FALSE WHERE LOWER(owner_email) = LOWER(%s)"
            cursor.execute(deact_sql, (target_owner,))

            act_sql = "UPDATE rule_versions SET is_active = TRUE, updated_at = CURRENT_TIMESTAMP WHERE version_id = %s AND LOWER(owner_email) = LOWER(%s)"
            cursor.execute(act_sql, (version_id, target_owner))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to activate rule version '{version_id}': {e}")
            raise
        finally:
            conn.close()

    def delete_version(self, version_id: str, owner_email: Optional[str] = None) -> bool:
        """Delete a rule profile and its associated rules."""
        conn = db_manager.get_connection()

        try:
            cursor = conn.cursor()
            # Rules cascade-delete via foreign key, but delete explicitly for safety
            self.delete_rules_for_version(version_id)

            if owner_email:
                del_sql = "DELETE FROM rule_versions WHERE version_id = %s AND LOWER(owner_email) = LOWER(%s)"
                cursor.execute(del_sql, (version_id, owner_email))
            else:
                del_sql = "DELETE FROM rule_versions WHERE version_id = %s"
                cursor.execute(del_sql, (version_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to delete rule version '{version_id}': {e}")
            raise
        finally:
            conn.close()

    def delete_rules_for_version(self, version_id: str) -> int:
        """Delete all rules associated with a profile version."""
        conn = db_manager.get_connection()
        del_sql = "DELETE FROM rules WHERE version_id = %s"

        try:
            cursor = conn.cursor()
            cursor.execute(del_sql, (version_id,))
            conn.commit()
            return cursor.rowcount
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to delete rules for version '{version_id}': {e}")
            raise
        finally:
            conn.close()

    # -------------------------------------------------------------
    # RULES
    # -------------------------------------------------------------

    def save_rule(self, rule: RuleRecord) -> str:
        """Insert or update a specific rule metric threshold."""
        conn = db_manager.get_connection()

        insert_sql = """
            INSERT INTO rules (
                rule_id, version_id, metric_name, label, category,
                condition, threshold_value, threshold_display, mode, weight, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (rule_id) DO UPDATE SET
                condition = EXCLUDED.condition,
                threshold_value = EXCLUDED.threshold_value,
                threshold_display = EXCLUDED.threshold_display,
                mode = EXCLUDED.mode,
                weight = EXCLUDED.weight;
        """

        values = (
            rule.rule_id,
            rule.version_id,
            rule.metric_name,
            rule.label,
            rule.category,
            rule.condition,
            rule.threshold_value,
            rule.threshold_display,
            rule.mode,
            rule.weight,
            rule.created_at,
        )

        try:
            cursor = conn.cursor()
            cursor.execute(insert_sql, values)
            conn.commit()
            return rule.rule_id
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to save rule '{rule.rule_id}': {e}")
            raise
        finally:
            conn.close()

    def get_rules_for_version(self, version_id: str) -> List[RuleRecord]:
        """Retrieve all individual rules configured for a profile version."""
        conn = db_manager.get_connection()
        query = "SELECT * FROM rules WHERE version_id = %s"

        try:
            cursor = conn.cursor()
            cursor.execute(query, (version_id,))
            rows = cursor.fetchall()
            return [self._row_to_rule(row) for row in rows]
        finally:
            conn.close()

    # -------------------------------------------------------------
    # ROW MAPPERS (PostgreSQL)
    # -------------------------------------------------------------

    def _row_to_version(self, row: Any) -> RuleVersionRecord:
        raw_changes = row[7]
        if isinstance(raw_changes, list):
            parsed_changes = raw_changes
        elif isinstance(raw_changes, str):
            try:
                parsed_changes = json.loads(raw_changes)
            except Exception:
                parsed_changes = [raw_changes] if raw_changes else []
        else:
            parsed_changes = []

        raw_countries = row[8]
        if isinstance(raw_countries, list):
            parsed_countries = raw_countries
        elif isinstance(raw_countries, str):
            try:
                parsed_countries = json.loads(raw_countries)
            except Exception:
                parsed_countries = [raw_countries] if raw_countries else []
        else:
            parsed_countries = []

        return RuleVersionRecord(
            version_id=row[0],
            profile_name=row[1],
            version_number=row[2],
            is_active=bool(row[3]),
            description=row[4],
            sector_limits=row[5] if isinstance(row[5], dict) else json.loads(row[5] or "{}"),
            diversification_rules=row[6] if isinstance(row[6], dict) else json.loads(row[6] or "{}"),
            changes=parsed_changes,
            selected_countries=parsed_countries,
            owner_email=row[9],
            user_id=row[12] if len(row) > 12 else None,
            created_at=row[10] if isinstance(row[10], datetime) else datetime.fromisoformat(str(row[10])),
            updated_at=row[11] if isinstance(row[11], datetime) else datetime.fromisoformat(str(row[11])),
        )

    def _row_to_rule(self, row: Any) -> RuleRecord:
        return RuleRecord(
            rule_id=row[0],
            version_id=row[1],
            metric_name=row[2],
            label=row[3],
            category=row[4],
            condition=row[5],
            threshold_value=float(row[6] or 0.0),
            threshold_display=row[7] or "",
            mode=row[8] or "Both",
            weight=float(row[9] or 0.0),
            created_at=row[10] if isinstance(row[10], datetime) else datetime.fromisoformat(str(row[10])),
        )


# Global repository instance
rule_repository = RuleRepository()
