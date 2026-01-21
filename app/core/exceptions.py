from fastapi import Request, status
from fastapi.responses import RedirectResponse
from ..config import templates

class PageLoginRequired(Exception):
    """로그인이 필요한 페이지 접근 시 발생하는 예외"""
    pass

class PageUserInactive(Exception):
    """비활성 사용자(승인 대기)가 접근 시 발생하는 예외"""
    pass

class PageAdminRequired(Exception):
    """관리자 권한이 필요한 페이지 접근 시 발생하는 예외"""
    pass

async def page_login_required_handler(request: Request, exc: PageLoginRequired):
    return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

async def page_user_inactive_handler(request: Request, exc: PageUserInactive):
    # 비활성 사용자는 대기 페이지(/)로 이동
    return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)

async def page_admin_required_handler(request: Request, exc: PageAdminRequired):
    """권한 없음 페이지(403) 렌더링"""
    return templates.TemplateResponse(request=request, name="403.html", status_code=status.HTTP_403_FORBIDDEN)
