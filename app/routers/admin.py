from fastapi import APIRouter, Request, Depends, HTTPException, status, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from .. import models
from ..config import templates
from ..dependencies import get_db, verify_admin_user

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("", response_class=RedirectResponse)
async def admin_page(request: Request, current_user: models.User = Depends(verify_admin_user), db: Session = Depends(get_db)):
    """
    관리자 페이지.
    미승인 사용자 목록을 보여줍니다. 관리자 권한(is_superuser=True)이 필요합니다.
    """
    # 미승인 사용자 목록 조회
    pending_users = db.query(models.User).filter(models.User.is_active == False).all()
    # 승인된 사용자 목록 조회 (관리자 자신 제외)
    active_users = db.query(models.User).filter(models.User.is_active == True).all()
    
    return templates.TemplateResponse(request=request, name="admin.html", context={
        "pending_users": pending_users, 
        "active_users": active_users, 
        "user": current_user
    })

@router.post("/approve/{user_id}")
async def approve_user(user_id: int, current_user: models.User = Depends(verify_admin_user), db: Session = Depends(get_db)):
    """
    사용자 승인 처리 (관리자 전용).
    """
    user_to_approve = db.query(models.User).filter(models.User.id == user_id).first()
    if user_to_approve:
        user_to_approve.is_active = True
        db.commit()
    
    return RedirectResponse(url="/admin", status_code=status.HTTP_302_FOUND)

@router.post("/change_role/{user_id}")
async def change_role(user_id: int, role: str = Form(...), current_user: models.User = Depends(verify_admin_user), db: Session = Depends(get_db)):
    """
    사용자 권한 변경 (관리자 전용).
    """
    if user_id == current_user.id:
        return RedirectResponse(url="/admin?error=Cannot change your own role", status_code=status.HTTP_302_FOUND)

    user_to_update = db.query(models.User).filter(models.User.id == user_id).first()
    if user_to_update:
        user_to_update.is_superuser = (role == "admin")
        db.commit()
    
    return RedirectResponse(url="/admin", status_code=status.HTTP_302_FOUND)

@router.post("/delete/{user_id}")
async def delete_user(user_id: int, current_user: models.User = Depends(verify_admin_user), db: Session = Depends(get_db)):
    """
    사용자 삭제 처리 (관리자 전용).
    """
    user_to_delete = db.query(models.User).filter(models.User.id == user_id).first()
    if user_to_delete:
        # 자기 자신 삭제 방지
        if user_to_delete.id == current_user.id:
             return RedirectResponse(url="/admin?error=Cannot delete yourself", status_code=status.HTTP_302_FOUND)

        db.delete(user_to_delete)
        db.commit()
    
    return RedirectResponse(url="/admin", status_code=status.HTTP_302_FOUND)
