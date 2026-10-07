"""Import all models so Base.metadata.create_all sees every table."""
from app.models.user import AuditLog, Department, User  # noqa: F401
from app.models.challenge import AiSuggestion, Challenge, Kpi  # noqa: F401
from app.models.startup import Startup, StartupMatch  # noqa: F401
from app.models.evaluation import (  # noqa: F401
    CoiDeclaration,
    Evaluation,
    EvaluationAggregate,
    ExpertAssignment,
)
from app.models.pilot import Milestone, PaymentPlan, Pilot, PilotKpi  # noqa: F401
from app.models.evidence import (  # noqa: F401
    Evidence,
    EvidenceVersion,
    ValidationFinding,
    ValidationPackage,
    ValidationReport,
    ValidatorAssignment,
)
from app.models.govdata import (  # noqa: F401
    DataRefreshLog,
    DataSource,
    DatasetVersion,
    GovernmentDataset,
)
from app.models.decision import (  # noqa: F401
    DecisionRecommendation,
    GovernmentDecision,
    KnowledgeLesson,
    ProcurementPackage,
    RepilotPlan,
    ScaleUpPlan,
    SimilarPilot,
)
