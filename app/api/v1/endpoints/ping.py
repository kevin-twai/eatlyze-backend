from fastapi import APIRouter

router = APIRouter()

@router.get("/", summary="Ping service")
async def ping():
    return {"message": "pong"}
