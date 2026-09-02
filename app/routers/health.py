from fastapi import APIRouter, HTTPException, Request, status

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/database")
async def database_health(request: Request) -> dict[str, str]:
    try:
        await request.app.state.mongo.ping()
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MongoDB is unavailable. Check MONGODB_URI and Atlas network access.",
        ) from error
    return {"status": "ok", "database": "connected"}

