from fastapi import APIRouter, Request, Depends, HTTPException, status, Response
from fastapi.responses import FileResponse

from .. import models
from ..config import BASE_DIR
from ..dependencies import verify_active_user

router = APIRouter(tags=["services"])

@router.get("/services/{file_path:path}")
async def serve_service_files(file_path: str, request: Request, current_user: models.User = Depends(verify_active_user)):
    """
    공용 서비스 파일 서빙 (/services/...) - 인증 필요
    (구 static 폴더 대체)
    """
    services_dir = BASE_DIR / "services"
    requested_path = (services_dir / file_path).resolve()

    if not str(requested_path).startswith(str(services_dir)):
        raise HTTPException(status_code=403, detail="Access denied")

    if requested_path.exists() and requested_path.is_file():
        return FileResponse(requested_path)
    
    raise HTTPException(status_code=404, detail="File not found")
