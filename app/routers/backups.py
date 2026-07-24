from fastapi import APIRouter, Depends, HTTPException, Request

from app.repositories.audit_logs import create_audit_log
from app.repositories.backups import create_backup, get_all_backups, restore_backup
from app.utils.dependencies import require_admin
from app.utils.responses import success_response

router = APIRouter(
    prefix="/api/admin/backups",
    tags=["admin-backups"],
)


@router.post("", status_code=201)
async def create_backup_route(current_user=Depends(require_admin)):
    backup = create_backup()
    create_audit_log(
        operator_id=current_user["id"],
        action="CREATE_BACKUP",
        target_type="backup",
        target_id=backup["backup_id"],
        success=True,
        detail={"created_at": backup["created_at"]},
    )
    return success_response(
        code=201,
        message="backup created",
        data=backup,
    )


@router.get("")
async def list_backups(current_user=Depends(require_admin)):
    backups = get_all_backups()
    return success_response(
        data=[
            {
                "backup_id": backup["id"],
                "created_at": backup["created_at"],
            }
            for backup in backups
        ]
    )


@router.post("/{backup_id}/restore")
async def restore_backup_route(
    backup_id: str,
    request: Request,
    current_user=Depends(require_admin),
):
    try:
        backup = restore_backup(backup_id)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    if backup is None:
        raise HTTPException(status_code=404, detail="backup not found")

    create_audit_log(
        operator_id=current_user["id"],
        action="RESTORE_BACKUP",
        target_type="backup",
        target_id=backup_id,
        success=True,
        detail={"created_at": backup["created_at"]},
    )

    # Restored user data can differ from the live session, so invalidate it.
    request.session.clear()
    return success_response(message="backup restored", data=backup)
