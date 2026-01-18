import os
from pathlib import Path
from fastapi import FastAPI, Depends, HTTPException, status, Request, Form, Response
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from . import models, auth
from .database import SessionLocal, engine, Base

# 현재 파일(main.py)의 부모 디렉토리 (app/)
BASE_DIR = Path(__file__).resolve().parent

# 데이터베이스 테이블 생성
Base.metadata.create_all(bind=engine)

app = FastAPI()

# 템플릿 설정
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

@app.exception_handler(404)
async def custom_404_handler(request: Request, exc):
    return templates.TemplateResponse(request=request, name="404.html", status_code=404)

# 정적 파일 (로그인 페이지 스타일 등 공개 리소스용)
# app/static 폴더를 /static 경로로 마운트
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# 템플릿 설정
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# DB 세션 의존성
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 초기 관리자 계정 생성
def create_initial_admin():
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

create_initial_admin()

# 현재 사용자 가져오기 (쿠키 기반)
async def get_current_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token:
        return None
    
    # Bearer 접두사 제거
    if token.startswith("Bearer "):
        token = token.split(" ")[1]
    
    payload = auth.decode_token(token)
    if payload is None or payload.get("type") != "access":
        return None
        
    username: str = payload.get("sub")
    if username is None:
        return None
    
    user = db.query(models.User).filter(models.User.username == username).first()
    return user

# --- 페이지 라우트 ---

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, current_user: models.User | None = Depends(get_current_user)):
    if not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    if not current_user.is_active:
        return templates.TemplateResponse(request=request, name="pending.html", context={"username": current_user.username})
    
    # 로그인하고 승인된 사용자는 docsify 페이지로 (index.html 직접 서빙)
    # docs/index.html 경로는 app/docs/index.html
    index_path = BASE_DIR / "docs" / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return HTMLResponse("Docs index not found", status_code=404)

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html")

@app.post("/login")
async def login(response: Response, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user or not auth.verify_password(password, user.hashed_password):
        return RedirectResponse(url="/login?error=Invalid credentials", status_code=status.HTTP_302_FOUND)
    
    access_token_expires = auth.timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    refresh_token_expires = auth.timedelta(days=auth.REFRESH_TOKEN_EXPIRE_DAYS)
    refresh_token = auth.create_refresh_token(
        data={"sub": user.username}, expires_delta=refresh_token_expires
    )
    
    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, path="/token/refresh")
    return response

@app.post("/token/refresh")
async def refresh_token(request: Request, db: Session = Depends(get_db)):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token missing")
    
    payload = auth.decode_token(refresh_token)
    if payload is None or payload.get("type") != "refresh":
         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    
    username = payload.get("sub")
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        
    access_token_expires = auth.timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    response = Response(content="Token refreshed", status_code=status.HTTP_200_OK)
    response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)
    return response

@app.get("/logout")
async def logout(response: Response):
    response = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token", path="/token/refresh")
    return response

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse(request=request, name="register.html")

@app.post("/register")
async def register(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
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
    if not current_user or not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # 미승인 사용자 목록 조회
    pending_users = db.query(models.User).filter(models.User.is_active == False).all()
    return templates.TemplateResponse(request=request, name="admin.html", context={"users": pending_users, "user": current_user})

@app.post("/admin/approve/{user_id}")
async def approve_user(user_id: int, current_user: models.User | None = Depends(get_current_user), db: Session = Depends(get_db)):
    if not current_user or not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    user_to_approve = db.query(models.User).filter(models.User.id == user_id).first()
    if user_to_approve:
        user_to_approve.is_active = True
        db.commit()
    
    return RedirectResponse(url="/admin", status_code=status.HTTP_302_FOUND)

@app.get("/{file_path:path}")
async def serve_docs(file_path: str, request: Request, current_user: models.User | None = Depends(get_current_user)):
    if not current_user:
        return RedirectResponse(url="/login")
    if not current_user.is_active:
        return RedirectResponse(url="/")
    
    # docs 폴더 경로
    docs_dir = BASE_DIR / "docs"
    requested_path = (docs_dir / file_path).resolve()
    
    # 보안: 요청된 경로가 docs 폴더 내부에 있는지 확인
    if not str(requested_path).startswith(str(docs_dir)):
         raise HTTPException(status_code=403, detail="Access denied")
    
    if requested_path.exists() and requested_path.is_file():
        return FileResponse(requested_path)
    
    raise HTTPException(status_code=404, detail="File not found")
