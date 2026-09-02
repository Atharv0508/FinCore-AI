from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.core.config import get_settings
from app.core.security import get_current_user
from app.models.razorpay import RazorpayConnectionStatus, RazorpayCredentialsRequest, SyncSummary
from app.services.crypto import CredentialCipher
from app.services.razorpay import RazorpayService

router = APIRouter(prefix="/razorpay", tags=["razorpay"])


def get_service(request: Request) -> RazorpayService:
    return RazorpayService(request.app.state.mongo.database, CredentialCipher(get_settings()))


@router.post("/credentials", response_model=RazorpayConnectionStatus)
async def connect_razorpay(
    payload: RazorpayCredentialsRequest,
    request: Request,
    user: dict = Depends(get_current_user),
) -> RazorpayConnectionStatus:
    try:
        await get_service(request).save_credentials(user["google_sub"], payload.key_id, payload.key_secret)
    except (LookupError, RuntimeError) as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    return RazorpayConnectionStatus(connected=True, message="Razorpay credentials encrypted and stored.")


@router.post("/sync", response_model=SyncSummary)
async def sync_razorpay(request: Request, user: dict = Depends(get_current_user)) -> SyncSummary:
    try:
        counts = await get_service(request).sync(user["google_sub"])
    except LookupError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error
    return SyncSummary(**counts)
