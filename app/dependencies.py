from fastapi import Depends, Request
from sqlalchemy.orm import Session
from . import models, auth
from .database import SessionLocal
from .core.exceptions import PageLoginRequired, PageUserInactive, PageAdminRequired

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

async def verify_active_user(current_user: models.User | None = Depends(get_current_user)) -> models.User:
    """
    페이지 접근 권한 확인 의존성.
    로그인하지 않았거나 승인되지 않은 경우 예외를 발생시켜 리다이렉트 처리합니다.
    """
    if not current_user:
        raise PageLoginRequired()
    if not current_user.is_active:
        raise PageUserInactive()
    return current_user

async def verify_admin_user(current_user: models.User = Depends(verify_active_user)) -> models.User:
    """
    관리자 권한 확인 의존성.
    활성 사용자이면서 슈퍼 유저여야 합니다.
    """
    if not current_user.is_superuser:
        raise PageAdminRequired()
    return current_user
