"""manageQuestions router (NEW). Table: nnp_km_qa."""

from fastapi import APIRouter, HTTPException, Request
from fastapi.concurrency import run_in_threadpool

from src.api.deps import current_user
from src.models.question import QuestionCreate, QuestionUpdate
from src.repositories import question_repo

router = APIRouter(prefix="/manageQuestions", tags=["manageQuestions"])


@router.get("/getDetails")
async def get_details(bucketIds: str, includeDeleted: bool = False):
    """Return curated Q&A across one or more buckets.

    bucketIds is a comma-separated list of bucket UUIDs.
    """
    ids = [b for b in (bucketIds or "").split(",") if b.strip()]
    return await run_in_threadpool(question_repo.get_by_buckets, ids, includeDeleted)


@router.post("/addQDetails", status_code=201)
async def add_q_details(payload: QuestionCreate, request: Request):
    """Create a curated Q&A pair (answer is plain text; rank 1..5).

    Question embedding is handled by a separate process — question_embedding_id
    stays null here.
    """
    user = current_user(request)
    return await run_in_threadpool(question_repo.create, payload.model_dump(), user)


@router.delete("/deleteQDetail/{qa_id}")
async def delete_q_detail(qa_id: str):
    """Soft-delete a Q&A pair (status → DELETED)."""
    row = await run_in_threadpool(question_repo.delete, qa_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Q&A not found")
    return row


@router.put("/updateQDetails/{qa_id}")
async def update_q_details(qa_id: str, payload: QuestionUpdate, request: Request):
    """Update a curated Q&A pair."""
    user = current_user(request)
    data = payload.model_dump(exclude_unset=True)
    row = await run_in_threadpool(question_repo.update, qa_id, data, user)
    if row is None:
        raise HTTPException(status_code=404, detail="Q&A not found")
    return row
