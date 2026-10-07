"""AI engines package. Each engine has a clean, replaceable interface.

AIRequirementEngine  — rule-based requirement/KPI suggestions (officer must accept)
MatchingEngine       — explainable weighted startup matching
DecisionEngine       — evidence-gated recommendation with mandatory abstention
KnowledgeEngine      — lesson extraction + similar-pilot recommendations
"""
from app.engines.decision_engine import get_decision_engine  # noqa: F401
from app.engines.knowledge_engine import get_knowledge_engine  # noqa: F401
from app.engines.matching_engine import get_matching_engine  # noqa: F401
from app.engines.requirements_engine import get_requirements_engine  # noqa: F401
