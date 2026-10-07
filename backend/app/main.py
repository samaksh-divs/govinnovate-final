"""GovInnovate Maharashtra API entrypoint.

Evidence-Gated Decision Intelligence for SIH26136.
Tagline: From Government Problem to Proven Innovation.
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers.auth_router import router as auth_router
from app.routers.challenges_router import router as challenges_router
from app.routers.decisions_router import (proc_router, repilot_router, router as decisions_router,
                                          scale_router)
from app.routers.evaluations_router import router as evaluations_router
from app.routers.evidence_router import router as evidence_router
from app.routers.govdata_router import router as govdata_router
from app.routers.knowledge_router import router as knowledge_router
from app.routers.meta_routers import (analytics_router, audit_router, search_router,
                                      system_router)
from app.routers.pilots_router import router as pilots_router
from app.routers.startups_router import match_router, router as startups_router
from app.routers.validation_router import router as validation_router
from app.services.demo_router import router as demo_router
from app.services.govdata import ensure_govdata_seeded
from app.services.system_bootstrap import ensure_seeded

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("govinnovate")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description=(
        "**GovInnovate Maharashtra — From Government Problem to Proven Innovation**\n\n"
        "Evidence-Gated Decision Intelligence platform for SIH26136.\n\n"
        "Core principle: **Claim ≠ Evidence ≠ Validation ≠ Government Decision**.\n\n"
        "AI assists; evidence supports; experts evaluate; independent validators validate; "
        "government decides. AI never approves procurement, payments or awards.\n\n"
        "Demo authentication: `POST /api/auth/login` with any seeded account "
        "(all demo passwords: `govinnovate-demo`), or send an `X-Demo-Role` header "
        "with one of the seeded roles."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (auth_router, challenges_router, startups_router, match_router, evaluations_router,
          pilots_router, evidence_router, validation_router, knowledge_router, decisions_router,
          scale_router, proc_router, repilot_router, analytics_router, audit_router, system_router,
          search_router, govdata_router, demo_router):
    app.include_router(r)


@app.get("/api/health", tags=["system"])
def root_health():
    """Unauthenticated liveness probe for the SPA and container healthchecks."""
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.VERSION,
            "problem_statement": settings.SIH_PROBLEM_ID}


@app.on_event("startup")
def on_startup():
    try:
        ensure_seeded()
        logger.info("Demo dataset ensured (seeded automatically on first run).")
        ensure_govdata_seeded()
        logger.info("Government public-data layer ensured (versioned snapshots).")
    except Exception as exc:  # pragma: no cover
        logger.error("Seeding failed: %s", exc)


@app.on_event("shutdown")
def on_shutdown():
    logger.info("GovInnovate API shutting down.")
