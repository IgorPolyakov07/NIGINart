import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.database import get_db
from src.models.account import Account
from src.models.instagram_story_snapshot import InstagramStorySnapshot
from src.models.schemas import (
    InstagramStoriesCollectionResponse,
    InstagramStoryHistoryResponse,
    InstagramStorySnapshotResponse,
)
from src.services.instagram.stories_collector_service import (
    InstagramStoriesCollectorService,
)
logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/instagram/stories", tags=["Instagram Stories"])
@router.post(
    "/collect",
    response_model=InstagramStoriesCollectionResponse,
    status_code=status.HTTP_200_OK,
)
async def trigger_stories_collection(
    account_id: Optional[UUID] = Query(
        None, description="Optional: Collect for specific account"
    ),
    db: AsyncSession = Depends(get_db),
) -> InstagramStoriesCollectionResponse:
    service = None
    try:
        service = InstagramStoriesCollectorService(db)
        if account_id:
            result = await service.collect_account_stories(account_id)
            return InstagramStoriesCollectionResponse(
                status="success",
                accounts_processed=1,
                accounts_failed=0,
                total_snapshots_saved=result["snapshots_saved"],
                details=[
                    {
                        "account_id": str(account_id),
                        "stories_collected": result["stories_collected"],
                        "snapshots_saved": result["snapshots_saved"],
                    }
                ],
            )
        else:
            result = await service.collect_all()
            total_snapshots = sum(
                d.get("snapshots_saved", 0) for d in result.success_details
            )
            return InstagramStoriesCollectionResponse(
                status=result.status,
                accounts_processed=result.accounts_processed,
                accounts_failed=result.accounts_failed,
                total_snapshots_saved=total_snapshots,
                details=result.success_details,
                errors=result.error_details if result.error_details else None,
            )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to trigger stories collection: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Collection failed: {str(e)}",
        )
    finally:
        if service:
            await service.close()
@router.get(
    "/{account_id}",
    response_model=InstagramStoryHistoryResponse,
    status_code=status.HTTP_200_OK,
)
async def get_account_story_history(
    account_id: UUID = Path(..., description="Account UUID"),
    since_hours: int = Query(
        48, description="Fetch stories from past N hours (default: 48)"
    ),
    db: AsyncSession = Depends(get_db),
) -> InstagramStoryHistoryResponse:
    try:
        account_result = await db.execute(select(Account).where(Account.id == account_id))
        account = account_result.scalar_one_or_none()
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Account {account_id} not found",
            )
        if account.platform != "instagram":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Account is not Instagram (platform={account.platform})",
            )
        cutoff_time = datetime.utcnow() - timedelta(hours=since_hours)
        query = (
            select(InstagramStorySnapshot)
            .where(
                InstagramStorySnapshot.account_id == account_id,
                InstagramStorySnapshot.collected_at >= cutoff_time,
            )
            .order_by(
                InstagramStorySnapshot.story_id,
                InstagramStorySnapshot.collected_at.desc(),
            )
        )
        result = await db.execute(query)
        snapshots = list(result.scalars().all())
        stories_grouped: Dict[str, List[InstagramStorySnapshot]] = {}
        for snapshot in snapshots:
            if snapshot.story_id not in stories_grouped:
                stories_grouped[snapshot.story_id] = []
            stories_grouped[snapshot.story_id].append(snapshot)
        stories = []
        for story_id, story_snapshots in stories_grouped.items():
            story_snapshots.sort(key=lambda s: s.collected_at, reverse=True)
            latest_snapshot = story_snapshots[0]
            stories.append(
                {
                    "story_id": story_id,
                    "posted_at": latest_snapshot.posted_at,
                    "expires_at": latest_snapshot.retention_expires_at,
                    "media_type": latest_snapshot.media_type,
                    "snapshot_count": len(story_snapshots),
                    "latest_snapshot": InstagramStorySnapshotResponse.model_validate(
                        latest_snapshot
                    ),
                    "all_snapshots": [
                        InstagramStorySnapshotResponse.model_validate(s)
                        for s in story_snapshots
                    ],
                }
            )
        return InstagramStoryHistoryResponse(
            account_id=account_id,
            account_name=account.display_name,
            since_hours=since_hours,
            total_stories=len(stories),
            total_snapshots=len(snapshots),
            stories=stories,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch story history: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch story history: {str(e)}",
        )
@router.get(
    "/{account_id}/{story_id}",
    response_model=List[InstagramStorySnapshotResponse],
    status_code=status.HTTP_200_OK,
)
async def get_story_snapshots(
    account_id: UUID = Path(..., description="Account UUID"),
    story_id: str = Path(..., description="Instagram story media ID"),
    db: AsyncSession = Depends(get_db),
) -> List[InstagramStorySnapshotResponse]:
    try:
        query = (
            select(InstagramStorySnapshot)
            .where(
                InstagramStorySnapshot.account_id == account_id,
                InstagramStorySnapshot.story_id == story_id,
            )
            .order_by(InstagramStorySnapshot.collected_at.asc())
        )
        result = await db.execute(query)
        snapshots = list(result.scalars().all())
        if not snapshots:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No snapshots found for story {story_id} on account {account_id}",
            )
        return [InstagramStorySnapshotResponse.model_validate(s) for s in snapshots]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch story snapshots: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch snapshots: {str(e)}",
        )
