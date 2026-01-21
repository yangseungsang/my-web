from fastapi import APIRouter, Request, Depends, HTTPException, status, Response
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse

from .. import models
from ..config import templates, BASE_DIR
from ..dependencies import get_current_user, verify_active_user

router = APIRouter(tags=["homer"])

# Homer가 네트워크 체크를 위해 HEAD 요청을 보내므로 GET과 HEAD를 모두 허용합니다.
@router.api_route("/", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def read_root(request: Request, current_user: models.User | None = Depends(get_current_user)):
    """
    메인 페이지 핸들러 (Dashboard).
    1. 로그인하지 않음 -> 로그인 페이지로 리다이렉트
    2. 로그인했으나 미승인 -> 대기 페이지(pending.html) 표시
    3. 승인된 사용자 -> Homer 대시보드 (static/homer/index.html) 표시
    """
    # HEAD 요청인 경우 body 없이 헤더만 반환
    if request.method == "HEAD":
        return Response(status_code=status.HTTP_200_OK)

    if not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    if not current_user.is_active:
        return templates.TemplateResponse(request=request, name="pending.html", context={"username": current_user.username})
    
    # Homer 대시보드 서빙
    homer_index = BASE_DIR / "services/homer/index.html"
    if homer_index.exists():
        return FileResponse(homer_index)
    return HTMLResponse("Dashboard not found", status_code=404)

@router.get("/manifest.json")
async def get_manifest(current_user: models.User | None = Depends(get_current_user)):
    if not current_user or not current_user.is_active:
        return Response(status_code=status.HTTP_403_FORBIDDEN)
    return FileResponse(BASE_DIR / "services/homer/assets/manifest.json")

@router.get("/assets/{file_path:path}")
async def serve_homer_assets(file_path: str, request: Request, current_user: models.User = Depends(verify_active_user)):
    """
    Homer Dashboard Assets 서빙 (/assets/...) - 인증 필요
    """
    assets_dir = BASE_DIR / "services/homer/assets"
    requested_path = (assets_dir / file_path).resolve()

    if not str(requested_path).startswith(str(assets_dir)):
        raise HTTPException(status_code=403, detail="Access denied")

    if requested_path.exists() and requested_path.is_file():
        return FileResponse(requested_path)
    
    raise HTTPException(status_code=404, detail="File not found")

@router.get("/resources/{file_path:path}")
async def serve_homer_resources(file_path: str, request: Request, current_user: models.User = Depends(verify_active_user)):
    """
    Homer Dashboard Resources 서빙 (/resources/...) - 인증 필요
    """
    resources_dir = BASE_DIR / "services/homer/resources"
    requested_path = (resources_dir / file_path).resolve()

    if not str(requested_path).startswith(str(resources_dir)):
        raise HTTPException(status_code=403, detail="Access denied")

    if requested_path.exists() and requested_path.is_file():
        return FileResponse(requested_path)
    
    raise HTTPException(status_code=404, detail="File not found")

@router.get("/{file_path:path}")
async def serve_dashboard_files(file_path: str, request: Request, current_user: models.User = Depends(verify_active_user)):
    """
    Homer Dashboard 관련 루트 파일 서빙 (logo.png, sw.js 등) 및 기타 404 처리.
    """
    # Homer 정적 파일 경로
    homer_dir = BASE_DIR / "services/homer"
    requested_path = (homer_dir / file_path).resolve()

    # 보안 체크
    if not str(requested_path).startswith(str(homer_dir)):
        raise HTTPException(status_code=403, detail="Access denied")

    if requested_path.exists() and requested_path.is_file():
        return FileResponse(requested_path)

    # 파일이 없으면 커스텀 404
    raise HTTPException(status_code=404, detail="File not found")
