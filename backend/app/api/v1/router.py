from fastapi import APIRouter

from app.api.v1 import (
    analytics,
    applications,
    audit,
    auth,
    candidates,
    interviews,
    jobs,
    learning,
    matching,
    reports,
    resumes,
    settings,
)

api_router = APIRouter(prefix="/api/v1")
for r in (auth, jobs, resumes, learning, candidates, applications, matching, settings, interviews, reports,
          analytics, audit):
    api_router.include_router(r.router)
