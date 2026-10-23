"""Repository for screening rule profiles and individual metrics."""

from datetime import datetime
import json
import logging
from typing import Any, List, Optional

from app.db.connection import db_manager
from app.models.rule import RuleRecord, RuleVersionRecord

logger = logging.getLogger("app.repositories.rule")


class RuleRepository:
    """SQL repository for 'rule_versions' and 'rules' tables."""

    def __init__(self):
        db_manager.init_tables()

    # -------------------------------------------------------------
    # RULE VERSIONS / PROFILES
    # -------------------------------------------------------------

    def save_version(self, version: RuleVersionRecord) -> str:
        """Insert or update a rule profile version."""
        conn = db_manager.get_connection()
        is_postgres = hasattr(conn, "info") or "psycopg2" in str(type(conn))

        insert_sql = """
            INSERT INTO rule_versions (
                version_id, profile_name, version_number, is_active,
                description, sector_limits, diversification_rules, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (version_id) DO UPDATE SET
                profile_name = EXCLUDED.profile_name,
                is_active = EXCLUDED.is_active,
                description = EXCLUDED.description,
                sector_limits = EXCLUDED.sector_limits,
                diversification_rules = EXCLUDED.diversification_rules,
                updated_at = EXCLUDED.updated_at;
        """ if is_postgres else """
            INSERT INTO rule_versions (
                version_id, profile_name, version_number, is_active,
                description, sector_limits, diversification_rules, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (version_id) DO UPDATE SET
                profile_name = excluded.profile_name,
                is_active = excluded.is_active,
                description = excluded.description,
                sector_limits = excluded.sector_limits,
                diversification_rules = excluded.diversification_rules,
                updated_at = excluded.updated_at;
        """

        sector_limits_json = json.dumps(version.sector_limits)
        diversification_json = json.dumps(version.diversification_rules)
        created_at_val = version.created_at if is_postgres else version.created_at.isoformat()
        updated_at_val = version.updated_at if is_postgres else version.updated_at.isoformat()
        is_active_val = version.is_active if is_postgres else (1 if version.is_active else 0)

        values = (
            version.version_id,
            version.profile_name,
            version.version_number,
            is_active_val,
            version.description,
            sector_limits_json,
            diversification_json,
            created_at_val,
            updated_at_val,
        )

        try:
            cursor = conn.cursor()
            cursor.execute(insert_sql, values)

            # If this is marked active, deactivate other profiles
            if version.is_active:
                deact_sql = "UPDATE rule_versions SET is_active = FALSE WHERE version_id != %s" if is_postgres else "UPDATE rule_versions SET is_active = 0 WHERE version_id != ?"
                cursor.execute(deact_sql, (version.version_id,))

            conn.commit()
            return version.version_id
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to save rule version '{version.version_id}': {e}")
            raise
        finally:
            conn.close()

    def get_active_version(self) -> Optional[RuleVersionRecord]:
        """Fetch the currently active screening profile."""
        conn = db_manager.get_connection()
        is_postgres = hasattr(conn, "info") or "psycopg2" in str(type(conn))
        query = "SELECT * FROM rule_versions WHERE is_active = TRUE LIMIT 1" if is_postgres else "SELECT * FROM rule_versions WHERE is_active = 1 LIMIT 1"

        try:
            cursor = conn.cursor()
            cursor.execute(query)
            row = cursor.fetchone()
            if not row:
                return None
            version = self._row_to_version(row, is_postgres)
            version.rules = self.get_rules_for_version(version.version_id)
            return version
        finally:
            conn.close()

    def list_versions(self) -> List[RuleVersionRecord]:
        """List all saved rule profiles."""
        conn = db_manager.get_connection()
        is_postgres = hasattr(conn, "info") or "psycopg2" in str(type(conn))
        query = "SELECT * FROM rule_versions ORDER BY is_active DESC, updated_at DESC"

        try:
            cursor = conn.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
            versions = [self._row_to_version(row, is_postgres) for row in rows]
            for v in versions:
                v.rules = self.get_rules_for_version(v.version_id)
            return versions
        finally:
            conn.close()

    def get_version_by_id(self, version_id: str) -> Optional[RuleVersionRecord]:
        """Fetch a specific rule profile by its version ID."""
        conn = db_manager.get_connection()
        is_postgres = hasattr(conn, "info") or "psycopg2" in str(type(conn))
        query = "SELECT * FROM rule_versions WHERE version_id = %s" if is_postgres else "SELECT * FROM rule_versions WHERE version_id = ?"

        try:
            cursor = conn.cursor()
            cursor.execute(query, (version_id,))
            row = cursor.fetchone()
            if not row:
                return None
            version = self._row_to_version(row, is_postgres)
            version.rules = self.get_rules_for_version(version.version_id)
            return version
        finally:
            conn.close()

    def activate_version(self, version_id: str) -> bool:
        """Mark a profile as active and deactivate all other profiles."""
        conn = db_manager.get_connection()
        is_postgres = hasattr(conn, "info") or "psycopg2" in str(type(conn))

        try:
            cursor = conn.cursor()
            deact_sql = "UPDATE rule_versions SET is_active = FALSE" if is_postgres else "UPDATE rule_versions SET is_active = 0"
            cursor.execute(deact_sql)

            act_sql = "UPDATE rule_versions SET is_active = TRUE, updated_at = CURRENT_TIMESTAMP WHERE version_id = %s" if is_postgres else "UPDATE rule_versions SET is_active = 1, updated_at = CURRENT_TIMESTAMP WHERE version_id = ?"
            cursor.execute(act_sql, (version_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to activate rule version '{version_id}': {e}")
            raise
        finally:
            conn.close()

    def delete_version(self, version_id: str) -> bool:
        """Delete a rule profile and its associated rules."""
        conn = db_manager.get_connection()
        is_postgres = hasattr(conn, "info") or "psycopg2" in str(type(conn))

        try:
            cursor = conn.cursor()
            # Rules cascade-delete via foreign key, but delete explicitly for safety
            self.delete_rules_for_version(version_id)

            del_sql = "DELETE FROM rule_versions WHERE version_id = %s" if is_postgres else "DELETE FROM rule_versions WHERE version_id = ?"
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
        is_postgres = hasattr(conn, "info") or "psycopg2" in str(type(conn))
        del_sql = "DELETE FROM rules WHERE version_id = %s" if is_postgres else "DELETE FROM rules WHERE version_id = ?"

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
        is_postgres = hasattr(conn, "info") or "psycopg2" in str(type(conn))

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
        """ if is_postgres else """
            INSERT INTO rules (
                rule_id, version_id, metric_name, label, category,
                condition, threshold_value, threshold_display, mode, weight, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (rule_id) DO UPDATE SET
                condition = excluded.condition,
                threshold_value = excluded.threshold_value,
                threshold_display = excluded.threshold_display,
                mode = excluded.mode,
                weight = excluded.weight;
        """

        created_at_val = rule.created_at if is_postgres else rule.created_at.isoformat()
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
            created_at_val,
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
        is_postgres = hasattr(conn, "info") or "psycopg2" in str(type(conn))
        query = "SELECT * FROM rules WHERE version_id = %s" if is_postgres else "SELECT * FROM rules WHERE version_id = ?"

        try:
            cursor = conn.cursor()
            cursor.execute(query, (version_id,))
            rows = cursor.fetchall()
            return [self._row_to_rule(row, is_postgres) for row in rows]
        finally:
            conn.close()

    # -------------------------------------------------------------
    # ROW PARSERS
    # -------------------------------------------------------------

    def _row_to_version(self, row: Any, is_postgres: bool) -> RuleVersionRecord:
        if is_postgres:
            return RuleVersionRecord(
                version_id=row[0],
                profile_name=row[1],
                version_number=row[2],
                is_active=bool(row[3]),
                description=row[4],
                sector_limits=row[5] if isinstance(row[5], dict) else json.loads(row[5] or "{}"),
                diversification_rules=row[6] if isinstance(row[6], dict) else json.loads(row[6] or "{}"),
                created_at=row[7] if isinstance(row[7], datetime) else datetime.fromisoformat(str(row[7])),
                updated_at=row[8] if isinstance(row[8], datetime) else datetime.fromisoformat(str(row[8])),
            )
        else:
            return RuleVersionRecord(
                version_id=row["version_id"],
                profile_name=row["profile_name"],
                version_number=row["version_number"],
                is_active=bool(row["is_active"]),
                description=row["description"],
                sector_limits=json.loads(row["sector_limits"] or "{}"),
                diversification_rules=json.loads(row["diversification_rules"] or "{}"),
                created_at=datetime.fromisoformat(str(row["created_at"])),
                updated_at=datetime.fromisoformat(str(row["updated_at"])),
            )

    def _row_to_rule(self, row: Any, is_postgres: bool) -> RuleRecord:
        if is_postgres:
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
        else:
            return RuleRecord(
                rule_id=row["rule_id"],
                version_id=row["version_id"],
                metric_name=row["metric_name"],
                label=row["label"],
                category=row["category"],
                condition=row["condition"],
                threshold_value=float(row["threshold_value"] or 0.0),
                threshold_display=row["threshold_display"] or "",
                mode=row["mode"] or "Both",
                weight=float(row["weight"] or 0.0),
                created_at=datetime.fromisoformat(str(row["created_at"])),
            )


# Global repository instance
rule_repository = RuleRepository()

