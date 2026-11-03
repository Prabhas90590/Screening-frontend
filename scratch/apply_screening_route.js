const fs = require('fs');
let p = 'backend/app/api/routes/screening.py';
let content = fs.readFileSync(p, 'utf8');

const endpoints = `


@router.delete("/{run_id}", status_code=status.HTTP_200_OK)
def delete_screening_run(run_id: str):
    """Permanently delete a single screening run from the database."""
    try:
        deleted = screening_repository.delete_run(run_id)
        return {
            "success": True,
            "message": f"Run '{run_id}' deleted successfully." if deleted else f"Run '{run_id}' already removed.",
            "deleted_run_id": run_id,
        }
    except Exception as e:
        logger.error(f"Error deleting run '{run_id}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete run '{run_id}': {str(e)}",
        )


@router.delete("", status_code=status.HTTP_200_OK)
def clear_all_screening_runs():
    """Permanently delete all screening runs and their results from the database."""
    try:
        count = screening_repository.clear_all_runs()
        return {
            "success": True,
            "message": f"Successfully cleared all screening runs ({count} removed).",
            "cleared_count": count,
        }
    except Exception as e:
        logger.error(f"Error clearing screening runs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear screening runs: {str(e)}",
        )
`;

content += endpoints.replace(/\n/g, '\r\n');
fs.writeFileSync(p, content, 'utf8');
console.log('Appended delete endpoints to screening.py');

