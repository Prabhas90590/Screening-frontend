const fs = require('fs');

// 1. Update backend/app/repositories/screening_repository.py
let repoPath = 'backend/app/repositories/screening_repository.py';
let repoContent = fs.readFileSync(repoPath, 'utf8');

const targetMethod = `            col_names = [desc[0] for desc in cursor.description]
            rows = [dict(zip(col_names, r)) for r in cursor.fetchall()]
            return [self._row_to_run(row, is_postgres=False) for row in rows]
        finally:
            conn.close()`;

const repoMethodsToAdd = `            col_names = [desc[0] for desc in cursor.description]
            rows = [dict(zip(col_names, r)) for r in cursor.fetchall()]
            return [self._row_to_run(row, is_postgres=False) for row in rows]
        finally:
            conn.close()

    def delete_run(self, run_id: str) -> bool:
        """Permanently delete a single screening run and its associated records."""
        conn = db_manager.get_connection()
        is_postgres = hasattr(conn, "info") or "psycopg2" in str(type(conn))
        p = "%s" if is_postgres else "?"
        try:
            cursor = conn.cursor()
            cursor.execute(f"DELETE FROM screening_results WHERE run_id = {p}", (run_id,))
            cursor.execute(f"DELETE FROM funnel_counts WHERE run_id = {p}", (run_id,))
            cursor.execute(f"DELETE FROM raw_responses WHERE run_id = {p}", (run_id,))
            cursor.execute(f"DELETE FROM decisions WHERE run_id = {p}", (run_id,))
            cursor.execute(f"DELETE FROM screening_runs WHERE run_id = {p}", (run_id,))
            deleted = cursor.rowcount > 0
            conn.commit()
            logger.info(f"[REPOSITORY:DELETE_RUN] Successfully deleted run '{run_id}' (affected: {deleted})")
            return deleted
        except Exception as e:
            conn.rollback()
            logger.error(f"[REPOSITORY:DELETE_RUN:ERROR] Could not delete run '{run_id}': {e}")
            raise
        finally:
            conn.close()

    def clear_all_runs(self) -> int:
        """Permanently delete all screening runs and their results."""
        conn = db_manager.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM screening_results")
            cursor.execute("DELETE FROM funnel_counts")
            cursor.execute("DELETE FROM raw_responses")
            cursor.execute("DELETE FROM decisions")
            cursor.execute("DELETE FROM screening_runs")
            count = cursor.rowcount
            conn.commit()
            logger.info(f"[REPOSITORY:CLEAR_RUNS] Successfully cleared all screening runs")
            return count
        except Exception as e:
            conn.rollback()
            logger.error(f"[REPOSITORY:CLEAR_RUNS:ERROR] Could not clear screening runs: {e}")
            raise
        finally:
            conn.close()`;

// Normalize line endings for replacement
const normalizedRepo = repoContent.replace(/\r\n/g, '\n');
const normalizedTarget = targetMethod.replace(/\r\n/g, '\n');
const normalizedReplacement = repoMethodsToAdd.replace(/\r\n/g, '\n');

if (normalizedRepo.includes(normalizedTarget)) {
  const updatedRepo = normalizedRepo.replace(normalizedTarget, normalizedReplacement).replace(/\n/g, '\r\n');
  fs.writeFileSync(repoPath, updatedRepo, 'utf8');
  console.log('Successfully updated screening_repository.py');
} else {
  console.error('Target not found in screening_repository.py');
}

