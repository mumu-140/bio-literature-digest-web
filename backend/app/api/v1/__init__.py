from fastapi import APIRouter

from . import audit, auth, literature, reports, rules

router = APIRouter(prefix="/v1")


@router.get("")
def api_version() -> dict[str, str]:
    return {"api_version": "v1", "service": "bio-literature-digest-web"}
router.include_router(auth.router)
router.include_router(literature.router)
router.include_router(reports.router)
router.include_router(rules.router)
router.include_router(audit.router)
