import json
from datetime import datetime

from fastapi import APIRouter, Depends, Query

from app.repositories.audit_logs import get_audit_logs_paginated
from app.utils.dependencies import require_admin
from app.utils.responses import success_response
from app.utils.time import to_utc_iso

router = APIRouter(prefix="/api/audit-logs", tags=["audit-logs"])


@router.get("")
async def list_audit_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    operator_id: str | None = None,
    action: str | None = None,
    target_id: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    current_user=Depends(require_admin),
):
    logs, total = get_audit_logs_paginated(
        page=page,
        page_size=page_size,
        operator_id=operator_id,
        action=action,
        target_id=target_id,
        start_time=to_utc_iso(start_time),
        end_time=to_utc_iso(end_time),
    )

    items = [
        {
            "id": log["id"],
            "operator_id": log["operator_id"],
            "action": log["action"],
            "target_type": log["target_type"],
            "target_id": log["target_id"],
            "success": bool(log["success"]),
            "detail": json.loads(log["detail"]) if log["detail"] else None,
            "created_at": log["created_at"],
        }
        for log in logs
    ]
    return success_response(
        data={
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )
