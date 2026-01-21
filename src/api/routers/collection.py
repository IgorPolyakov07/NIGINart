from typing import Optional
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.database import get_db
from src.services.collector_service import CollectorService
from src.models.schemas import CollectionTriggerRequest, CollectionTriggerResponse
logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["collection"])
@router.post("/collect", response_model=CollectionTriggerResponse, status_code=status.HTTP_200_OK)
async def trigger_collection(
    request: CollectionTriggerRequest,
    db: AsyncSession = Depends(get_db)
) -> CollectionTriggerResponse:
    try:
        logger.info(f"Collection triggered via API. Platform filter: {request.platform or 'None'}")
        service = CollectorService(db)
        result = await service.collect_all(platform_filter=request.platform)
        logger.info(
            f"Collection completed. Status: {result.status}, "
            f"Processed: {result.accounts_processed}, Failed: {result.accounts_failed}"
        )
        return CollectionTriggerResponse(
            log_id=result.log_id,
            status=result.status,
            started_at=result.started_at,
            finished_at=result.finished_at,
            accounts_processed=result.accounts_processed,
            accounts_failed=result.accounts_failed,
            success_details=result.success_details,
            error_details=result.error_details
        )
    except Exception as e:
        logger.error(f"Collection failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Collection failed: {str(e)}"
        )
