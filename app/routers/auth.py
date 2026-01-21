from fastapi import APIRouter, Request, Response, Form, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from .. import models, auth
from ..config import templates
from ..dependencies import get_db

router = APIRouter()

@router.get("/login", response_class=RedirectResponse)
async def login_page(request: Request):
    """로그인 페이지 렌더링"""
    return templates.TemplateResponse(request=request, name="login.html")

@router.post("/login")
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

@router.post("/token/refresh")
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

@router.get("/logout")
async def logout(response: Response):
    """
    로그아웃 처리.
    모든 인증 쿠키를 삭제하고 로그인 페이지로 리다이렉트합니다.
    """
    response = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token", path="/token/refresh")
    return response

@router.get("/register", response_class=RedirectResponse)
async def register_page(request: Request):
    """회원가입 페이지 렌더링"""
    return templates.TemplateResponse(request=request, name="register.html")

@router.post("/register")
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
