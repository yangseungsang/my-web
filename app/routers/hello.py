from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse

from .. import models
from ..config import BASE_DIR
from ..dependencies import verify_active_user

router = APIRouter(prefix="/hello", tags=["hello"])

@router.get("")
async def hello_redirect(request: Request):
    """
    /hello 로 접근 시 /hello/ 로 리다이렉트 (상대 경로 리소스 로딩을 위함)
    """
    return RedirectResponse(url="/hello/")

@router.get("/", response_class=HTMLResponse)
async def hello_index(request: Request, current_user: models.User = Depends(verify_active_user)):
    """
    Hello 서비스 메인 페이지.
    """
    index_path = BASE_DIR / "services/hello" / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return HTMLResponse("Hello service index not found", status_code=404)

@router.get("/{file_path:path}")
async def serve_hello_files(file_path: str, request: Request, current_user: models.User = Depends(verify_active_user)):
    """
    Hello 서비스 정적 파일 서빙 (/hello/assets/...)
    """
    # Hello 서비스 루트 디렉토리
    hello_dir = BASE_DIR / "services/hello"
    requested_path = (hello_dir / file_path).resolve()
    
    # 상위 디렉토리 접근 방지 (Path Traversal 공격 방어)
    if not str(requested_path).startswith(str(hello_dir)):
         raise HTTPException(status_code=403, detail="Access denied")
    
    if requested_path.exists() and requested_path.is_file():
        return FileResponse(requested_path)
    
    raise HTTPException(status_code=404, detail="File not found")
