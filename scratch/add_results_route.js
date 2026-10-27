const fs = require('fs');
const path = require('path');

const filePath = path.join(__dirname, '..', 'backend', 'app', 'api', 'routes', 'screening.py');
let content = fs.readFileSync(filePath, 'utf8').replace(/\r\n/g, '\n');

const marker = 'def get_screening_run(run_id: str):';
const index = content.indexOf(marker);
console.log('Marker found at:', index);

const target = `    return run\n\n\n@router.get("/{run_id}/funnel"`;
const replacement = `    return run


@router.get("/{run_id}/results")
def get_screening_results(
    run_id: str,
    view: str = Query(default="all"),
    sector: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=500),
):
    """Retrieve individual security results, ranks, and score breakdowns for a screening run."""
    run = screening_service.get_run(run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Screening run '{run_id}' not found.",
        )
    return screening_repository.get_results_by_run(run_id, view=view, sector=sector, limit=limit)


@router.get("/{run_id}/funnel"`;

if (content.indexOf('return run\n\n\n@router.get("/{run_id}/funnel"') !== -1) {
  content = content.replace('return run\n\n\n@router.get("/{run_id}/funnel"', replacement);
  fs.writeFileSync(filePath, content, 'utf8');
  console.log('Successfully added results route to screening.py!');
} else {
  console.log('Could not find target chunk');
}

