"""Database repositories package."""

from app.repositories.company_metrics_repository import (
    CompanyMetricsRepository,
    company_metrics_repository,
)
from app.repositories.company_repository import (
    CompanyRepository,
    company_repository,
)
from app.repositories.decision_repository import (
    DecisionRepository,
    decision_repository,
)
from app.repositories.raw_response_repository import (
    RawResponseRepository,
    raw_response_repository,
)
from app.repositories.rule_repository import (
    RuleRepository,
    rule_repository,
)
from app.repositories.screening_repository import (
    ScreeningRepository,
    screening_repository,
)
from app.repositories.user_repository import (  # Phase 2 – authentication
    UserRepository,
    user_repository,
)

__all__ = [
    "CompanyRepository",
    "company_repository",
    "CompanyMetricsRepository",
    "company_metrics_repository",
    "RawResponseRepository",
    "raw_response_repository",
    "ScreeningRepository",
    "screening_repository",
    "DecisionRepository",
    "decision_repository",
    "RuleRepository",
    "rule_repository",
    "UserRepository",          # Phase 2 – authentication
    "user_repository",         # Phase 2 – authentication
]
