from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, FileResponse

from .. import models
from ..config import BASE_DIR
from ..dependencies import verify_active_user

router = APIRouter(prefix="/docs", tags=["docs"])

@router.get("/", response_class=HTMLResponse)
async def read_docs(request: Request, current_user: models.User = Depends(verify_active_user)):
    """
    Docsify 문서 메인 페이지.
    """
    index_path = BASE_DIR / "services/docs" / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return HTMLResponse("Docs index not found", status_code=404)

@router.get("/{file_path:path}")
async def serve_docs_files(file_path: str, request: Request, current_user: models.User = Depends(verify_active_user)):
    """
    Docsify 문서 파일 서빙 (/docs/...)
    """
    docs_dir = BASE_DIR / "services/docs"
    requested_path = (docs_dir / file_path).resolve()
    
    if not str(requested_path).startswith(str(docs_dir)):
         raise HTTPException(status_code=403, detail="Access denied")
    
    if requested_path.exists() and requested_path.is_file():
        if requested_path.is_relative_to(docs_dir / "downloads"):
            return FileResponse(requested_path, filename=requested_path.name, media_type="application/octet-stream")
        return FileResponse(requested_path)
    
    raise HTTPException(status_code=404, detail="File not found")
