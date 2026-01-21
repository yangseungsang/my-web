from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import RedirectResponse, FileResponse

from .. import models
from ..config import BASE_DIR
from ..dependencies import verify_active_user

router = APIRouter(prefix="/resume", tags=["resume"])

@router.get("")
async def resume_redirect(request: Request):
    """
    /resume 로 접근 시 /resume/ 로 리다이렉트 (상대 경로 리소스 로딩을 위함)
    """
    return RedirectResponse(url="/resume/")

@router.get("/", response_class=FileResponse)
async def resume_index(request: Request, current_user: models.User = Depends(verify_active_user)):
    """
    이력서 메인 페이지.
    """
    index_path = BASE_DIR / "services/resume" / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return FileResponse("Resume index not found", status_code=404)

@router.get("/{file_path:path}")
async def serve_resume_files(file_path: str, request: Request, current_user: models.User = Depends(verify_active_user)):
    """
    이력서 정적 파일 서빙 (/resume/style.css 등)
    """
    resume_dir = BASE_DIR / "services/resume"
    requested_path = (resume_dir / file_path).resolve()
    
    # 상위 디렉토리 접근 방지
    if not str(requested_path).startswith(str(resume_dir)):
         raise HTTPException(status_code=403, detail="Access denied")
    
    if requested_path.exists() and requested_path.is_file():
        return FileResponse(requested_path)
    
    raise HTTPException(status_code=404, detail="File not found")