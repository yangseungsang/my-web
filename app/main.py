import os
from pathlib import Path
from fastapi import FastAPI, Depends, HTTPException, status, Request, Form, Response
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from . import models, auth
from .database import SessionLocal, engine, Base
from .resume_data import resume_data

# 현재 파일(main.py)의 부모 디렉토리 (app/)
# 이를 기준으로 템플릿, 정적 파일 경로를 설정합니다.
BASE_DIR = Path(__file__).resolve().parent

# 데이터베이스 테이블 생성
# 애플리케이션 시작 시 모델에 정의된 테이블이 없으면 자동 생성합니다.
Base.metadata.create_all(bind=engine)

app = FastAPI()

# Jinja2 템플릿 엔진 설정
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# 커스텀 404 예외 핸들러
@app.exception_handler(404)
async def custom_404_handler(request: Request, exc):
    """
    404 에러 발생 시 JSON 대신 사용자 친화적인 HTML 페이지를 반환합니다.
    """
    return templates.TemplateResponse(request=request, name="404.html", status_code=404)

# 정적 파일 (CSS, JS, 이미지 등) 설정
# 로그인 페이지 스타일 등 인증 없이 접근 가능한 공개 리소스용입니다.
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# Homer Dashboard Assets
# Homer가 루트(/)에서 실행될 때 필요한 리소스들을 마운트합니다.
app.mount("/assets", StaticFiles(directory=str(BASE_DIR / "static/homer/assets")), name="homer_assets")
app.mount("/resources", StaticFiles(directory=str(BASE_DIR / "static/homer/resources")), name="homer_resources")

# Homer 루트 레벨 파일들 (manifest.json, sw.js 등)을 위한 서빙
# /logo.png, /manifest.json 등의 요청을 처리하기 위해 별도 라우트나 마운트가 필요하지만,
# 개별 파일이 많지 않으므로 필요 시 추가하거나, Catch-all 라우트 전에 배치해야 합니다.

@app.get("/manifest.json")
async def get_manifest():
    return FileResponse(BASE_DIR / "static/homer/assets/manifest.json")

# DB 세션 의존성 주입 함수
def get_db():
    """
    요청마다 새로운 DB 세션을 생성하고, 요청 처리가 끝나면 닫습니다.
    FastAPI의 Depends를 통해 사용됩니다.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

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

# 현재 사용자 가져오기 (쿠키 기반 인증)
async def get_current_user(request: Request, db: Session = Depends(get_db)):
    """
    요청의 쿠키에서 Access Token을 읽어 사용자를 식별합니다.
    토큰이 없거나 유효하지 않으면 None을 반환합니다.
    """
    token = request.cookies.get("access_token")
    if not token:
        return None
    
    # Bearer 접두사 제거
    if token.startswith("Bearer "):
        token = token.split(" ")[1]
    
    # 토큰 디코딩 및 검증 ('access' 타입 확인)
    payload = auth.decode_token(token)
    if payload is None or payload.get("type") != "access":
        return None
        
    username: str = payload.get("sub")
    if username is None:
        return None
    
    # DB에서 사용자 조회
    user = db.query(models.User).filter(models.User.username == username).first()
    return user

# --- 페이지 라우트 ---

# Homer가 네트워크 체크를 위해 HEAD 요청을 보내므로 GET과 HEAD를 모두 허용합니다.
@app.api_route("/", methods=["GET", "HEAD"], response_class=HTMLResponse)
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
    homer_index = BASE_DIR / "static/homer/index.html"
    if homer_index.exists():
        return FileResponse(homer_index)
    return HTMLResponse("Dashboard not found", status_code=404)

@app.get("/docs/", response_class=HTMLResponse)
async def read_docs(request: Request, current_user: models.User | None = Depends(get_current_user)):
    """
    Docsify 문서 메인 페이지.
    """
    if not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    if not current_user.is_active:
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
        
    index_path = BASE_DIR / "docs" / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return HTMLResponse("Docs index not found", status_code=404)

@app.get("/resume", response_class=HTMLResponse)
async def resume_page(request: Request):
    """
    이력서 페이지 렌더링.
    """
    return templates.TemplateResponse(request=request, name="resume.html", context={"resume": resume_data})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """로그인 페이지 렌더링"""
    return templates.TemplateResponse(request=request, name="login.html")

@app.post("/login")
async def login(response: Response, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    """
    로그인 처리.
    성공 시 Access Token과 Refresh Token을 쿠키에 설정합니다.
    """
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user or not auth.verify_password(password, user.hashed_password):
        return RedirectResponse(url="/login?error=Invalid credentials", status_code=status.HTTP_302_FOUND)
    
    # 토큰 생성
    access_token_expires = auth.timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    refresh_token_expires = auth.timedelta(days=auth.REFRESH_TOKEN_EXPIRE_DAYS)
    refresh_token = auth.create_refresh_token(
        data={"sub": user.username}, expires_delta=refresh_token_expires
    )
    
    # 쿠키 설정
    # access_token: API 인증용
    # refresh_token: 토큰 갱신용 (path=/token/refresh 로 제한)
    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, path="/token/refresh")
    return response

@app.post("/token/refresh")
async def refresh_token(request: Request, db: Session = Depends(get_db)):
    """
    Refresh Token을 사용하여 새로운 Access Token을 발급합니다.
    """
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token missing")
    
    # Refresh Token 검증
    payload = auth.decode_token(refresh_token)
    if payload is None or payload.get("type") != "refresh":
         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    
    username = payload.get("sub")
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        
    # 새 Access Token 생성
    access_token_expires = auth.timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    response = Response(content="Token refreshed", status_code=status.HTTP_200_OK)
    response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)
    return response

@app.get("/logout")
async def logout(response: Response):
    """
    로그아웃 처리.
    모든 인증 쿠키를 삭제하고 로그인 페이지로 리다이렉트합니다.
    """
    response = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token", path="/token/refresh")
    return response

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """회원가입 페이지 렌더링"""
    return templates.TemplateResponse(request=request, name="register.html")

@app.post("/register")
async def register(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    """
    회원가입 처리.
    새 사용자는 기본적으로 비활성(is_active=False) 상태로 생성되며, 관리자의 승인이 필요합니다.
    """
    user = db.query(models.User).filter(models.User.username == username).first()
    if user:
        return RedirectResponse(url="/register?error=Username already registered", status_code=status.HTTP_302_FOUND)
    
    hashed_password = auth.get_password_hash(password)
    new_user = models.User(username=username, hashed_password=hashed_password, is_active=False)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return RedirectResponse(url="/login?msg=Registration successful. Please wait for admin approval.", status_code=status.HTTP_302_FOUND)

@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request, current_user: models.User | None = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    관리자 페이지.
    미승인 사용자 목록을 보여줍니다. 관리자 권한(is_superuser=True)이 필요합니다.
    """
    if not current_user or not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # 미승인 사용자 목록 조회
    pending_users = db.query(models.User).filter(models.User.is_active == False).all()
    # 승인된 사용자 목록 조회 (관리자 자신 제외)
    active_users = db.query(models.User).filter(models.User.is_active == True).all()
    
    return templates.TemplateResponse(request=request, name="admin.html", context={
        "pending_users": pending_users, 
        "active_users": active_users, 
        "user": current_user
    })

@app.post("/admin/approve/{user_id}")
async def approve_user(user_id: int, current_user: models.User | None = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    사용자 승인 처리 (관리자 전용).
    """
    if not current_user or not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    user_to_approve = db.query(models.User).filter(models.User.id == user_id).first()
    if user_to_approve:
        user_to_approve.is_active = True
        db.commit()
    
    return RedirectResponse(url="/admin", status_code=status.HTTP_302_FOUND)

@app.post("/admin/delete/{user_id}")
async def delete_user(user_id: int, current_user: models.User | None = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    사용자 삭제 처리 (관리자 전용).
    """
    if not current_user or not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    user_to_delete = db.query(models.User).filter(models.User.id == user_id).first()
    if user_to_delete:
        # 자기 자신 삭제 방지
        if user_to_delete.id == current_user.id:
             return RedirectResponse(url="/admin?error=Cannot delete yourself", status_code=status.HTTP_302_FOUND)

        db.delete(user_to_delete)
        db.commit()
    
    return RedirectResponse(url="/admin", status_code=status.HTTP_302_FOUND)

@app.get("/docs/{file_path:path}")

async def serve_docs_files(file_path: str, request: Request, current_user: models.User | None = Depends(get_current_user)):

    """

    Docsify 문서 파일 서빙 (/docs/...)

    """

    if not current_user:

        return RedirectResponse(url="/login")

    if not current_user.is_active:

        return RedirectResponse(url="/")

    

    docs_dir = BASE_DIR / "docs"

    requested_path = (docs_dir / file_path).resolve()

    

    if not str(requested_path).startswith(str(docs_dir)):

         raise HTTPException(status_code=403, detail="Access denied")

    

    if requested_path.exists() and requested_path.is_file():

        if requested_path.is_relative_to(docs_dir / "downloads"):

            return FileResponse(requested_path, filename=requested_path.name, media_type="application/octet-stream")

        return FileResponse(requested_path)

    

    raise HTTPException(status_code=404, detail="File not found")



@app.get("/{file_path:path}")

async def serve_dashboard_files(file_path: str, request: Request, current_user: models.User | None = Depends(get_current_user)):

    """

    Homer Dashboard 관련 루트 파일 서빙 (logo.png, sw.js 등) 및 기타 404 처리.

    """

    if not current_user:

        return RedirectResponse(url="/login")

    if not current_user.is_active:

        return RedirectResponse(url="/")



    # Homer 정적 파일 경로

    homer_dir = BASE_DIR / "static/homer"

    requested_path = (homer_dir / file_path).resolve()



    # 보안 체크

    if not str(requested_path).startswith(str(homer_dir)):

        raise HTTPException(status_code=403, detail="Access denied")



    if requested_path.exists() and requested_path.is_file():

        return FileResponse(requested_path)



    # 파일이 없으면 커스텀 404

    raise HTTPException(status_code=404, detail="File not found")



    