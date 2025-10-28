from fastapi import APIRouter

router = APIRouter()

@router.get("/", summary="Health check")
async def health_root():
    return {"status": "ok"}
