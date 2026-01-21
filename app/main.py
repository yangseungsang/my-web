from fastapi import FastAPI, Request, Depends
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from . import models, auth
from .database import SessionLocal, engine, Base
from .config import templates
from .dependencies import verify_active_user
from .core.exceptions import (
    PageLoginRequired, page_login_required_handler,
    PageUserInactive, page_user_inactive_handler,
    PageAdminRequired, page_admin_required_handler
)
from .routers import (
    auth as auth_router,
    admin as admin_router,
    services as services_router,
    hello as hello_router,
    docs as docs_router,
    resume as resume_router,
    homer as homer_router
)

# 데이터베이스 테이블 생성
Base.metadata.create_all(bind=engine)

# 기본 문서 URL 비활성화 (보안 적용을 위해)
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

# 커스텀 예외 핸들러 등록
app.add_exception_handler(PageLoginRequired, page_login_required_handler)
app.add_exception_handler(PageUserInactive, page_user_inactive_handler)
app.add_exception_handler(PageAdminRequired, page_admin_required_handler)

# 404 예외 핸들러
@app.exception_handler(404)
async def custom_404_handler(request: Request, exc):
    return templates.TemplateResponse(request=request, name="404.html", status_code=404)

# --- Swagger UI & OpenAPI 보안 설정 ---

@app.get("/api/docs", include_in_schema=False)
async def get_swagger_documentation(current_user: models.User = Depends(verify_active_user)):
    """
    Swagger UI 페이지 (로그인 필요)
    """
    return get_swagger_ui_html(openapi_url="/api/openapi.json", title="API Docs")

@app.get("/api/openapi.json", include_in_schema=False)
async def get_open_api_endpoint(current_user: models.User = Depends(verify_active_user)):
    """
    OpenAPI 스키마 JSON (로그인 필요)
    """
    return JSONResponse(get_openapi(title="My Web API", version="1.0.0", routes=app.routes))

# --- 라우터 등록 ---
# 순서가 중요합니다. 구체적인 경로가 먼저 오고, Catch-all 패턴이 있는 라우터는 나중에 와야 합니다.
app.include_router(auth_router.router)
app.include_router(admin_router.router)
app.include_router(services_router.router)
app.include_router(hello_router.router)
app.include_router(docs_router.router)
app.include_router(resume_router.router)
app.include_router(homer_router.router) # Catch-all 라우트 포함

# 초기 관리자 계정 생성 함수
def create_initial_admin():
    """
    앱 시작 시 'admin' 사용자가 없으면 자동으로 생성합니다.
    기본 비밀번호: admin (운영 환경에서는 변경 필수)
    """
    db = SessionLocal()
    try:
        user = db.query(models.User).filter(models.User.username == "admin").first()
        if not user:
            hashed_password = auth.get_password_hash("admin")
            db_user = models.User(username="admin", hashed_password=hashed_password, is_active=True, is_superuser=True)
            db.add(db_user)
            db.commit()
            print("Initial admin user created: admin / admin")
    finally:
        db.close()

# 앱 시작 시 관리자 계정 확인 및 생성
create_initial_admin()
