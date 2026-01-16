from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List, Any

from bff.database import get_db
from bff.schemas import ReviewItem, ResolveRequest

router = APIRouter(prefix="/workflow", tags=["Workflow & Governance"])


@router.get("/queue", response_model=List[ReviewItem])
async def get_review_queue(
    limit: int = 50, db: AsyncSession = Depends(get_db)
) -> List[dict[str, Any]]:
    """
    Fetches pending exceptions that need human review (Status = UNKNOWN).
    Includes all context needed for the UI to display the 'Before/After'.
    """
    # Complex join to fetch Diff + Record + Reason
    query = text(
        """
        SELECT 
            a.attribution_id, a.confidence_score, a.status,
            d.diff_id, d.field_name, d.value_a, d.value_b, d.diff_type,
            r.source_a_ref_id, r.source_b_ref_id,
            rc.reason_id, rc.code, rc.description, rc.is_functional
        FROM recon.attributions a
        JOIN recon.data_differences d ON a.diff_id = d.diff_id
        JOIN recon.recon_records r ON d.record_id = r.record_id
        LEFT JOIN recon.reason_codes rc ON a.reason_id = rc.reason_id
        WHERE a.status = 'UNKNOWN'
        ORDER BY a.confidence_score ASC
        LIMIT :limit
    """
    )

    result = await db.execute(query, {"limit": limit})
    rows = result.fetchall()

    # Map raw SQL result to Pydantic structure
    response = []
    for row in rows:
        response.append(
            {
                "attribution_id": row.attribution_id,
                "confidence_score": (
                    float(row.confidence_score) if row.confidence_score else 0.0
                ),
                "status": row.status,
                "source_a_ref_id": row.source_a_ref_id,
                "source_b_ref_id": row.source_b_ref_id,
                "difference": {
                    "diff_id": row.diff_id,
                    "field_name": row.field_name,
                    "value_a": row.value_a,
                    "value_b": row.value_b,
                    "diff_type": row.diff_type,
                },
                "current_reason": (
                    {
                        "reason_id": row.reason_id,
                        "code": row.code,
                        "description": row.description,
                        "is_functional": row.is_functional,
                    }
                    if row.reason_id
                    else None
                ),
            }
        )
    return response


@router.post("/resolve", status_code=status.HTTP_200_OK)
async def resolve_exception(
    payload: ResolveRequest, db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Handles the 4-Eye Check Logic.
    - If APPROVE: Marks as ACCEPTED.
    - If OVERRIDE: Updates Reason, Logs Audit, and potentially flags for Checker.
    """
    # 1. Fetch current state
    stmt = text(
        "SELECT status, reason_id FROM recon.attributions WHERE attribution_id = :aid"
    )
    result = await db.execute(stmt, {"aid": payload.attribution_id})
    current = result.fetchone()

    if not current:
        raise HTTPException(status_code=404, detail="Attribution record not found")

    # 2. Logic Branching
    new_status = "ACCEPTED"
    new_reason_id = current.reason_id

    # If overriding, we need to find the new reason ID
    if payload.action == "OVERRIDE":
        if not payload.new_reason_code:
            raise HTTPException(
                status_code=400, detail="New reason code required for OVERRIDE"
            )

        reason_query = await db.execute(
            text("SELECT reason_id FROM recon.reason_codes WHERE code = :code"),
            {"code": payload.new_reason_code},
        )
        reason_row = reason_query.fetchone()

        if not reason_row:
            raise HTTPException(status_code=400, detail="Invalid Reason Code provided")

        new_reason_id = reason_row.reason_id
        # NOTE: Here is where you would set status='PENDING_AUTH' if implementing 4-eye check strict mode

    # 3. Update Attribution Table
    update_sql = text(
        """
        UPDATE recon.attributions 
        SET status = :status, reason_id = :rid, assigned_by = :actor, assigned_at = NOW()
        WHERE attribution_id = :aid
    """
    )

    await db.execute(
        update_sql,
        {
            "status": new_status,
            "rid": new_reason_id,
            "actor": payload.actor_id,
            "aid": payload.attribution_id,
        },
    )

    # 4. Write to Audit Trail (Critical for Governance)
    audit_sql = text(
        """
        INSERT INTO recon.audit_trail 
        (attribution_id, actor_id, action_type, comments, previous_value)
        VALUES (:aid, :actor, :action, :comments, :prev)
    """
    )

    await db.execute(
        audit_sql,
        {
            "aid": payload.attribution_id,
            "actor": payload.actor_id,
            "action": payload.action,
            "comments": payload.comments,
            "prev": f'{{"status": "{current.status}", "reason_id": {current.reason_id}}}',
        },
    )

    await db.commit()
    return {"message": "Resolution processed successfully"}
