from datetime import datetime, timedelta, timezone
from typing import Union
from jose import JWTError, jwt
from passlib.context import CryptContext
from .config import settings

# config.py에서 설정을 가져옵니다.
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS

# 비밀번호 해싱을 위한 컨텍스트 설정 (bcrypt 알고리즘 사용)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    """
    평문 비밀번호와 해시된 비밀번호를 비교하여 일치 여부를 확인합니다.
    """
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    """
    비밀번호를 해시하여 저장 가능한 형태(문자열)로 반환합니다.
    """
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Union[timedelta, None] = None):
    """
    사용자 인증을 위한 Access Token을 생성합니다.
    
    Args:
        data (dict): 토큰 페이로드에 포함할 데이터
        expires_delta (timedelta, optional): 토큰 유효 기간. 지정하지 않으면 기본값(15분) 사용.
        
    Returns:
        str: 인코딩된 JWT 문자열
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    
    # 'type': 'access'를 추가하여 토큰 용도를 명시합니다.
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict, expires_delta: Union[timedelta, None] = None):
    """
    Access Token 갱신을 위한 Refresh Token을 생성합니다.
    Access Token보다 긴 유효 기간을 가집니다.
    
    Args:
        data (dict): 토큰 페이로드에 포함할 데이터
        expires_delta (timedelta, optional): 토큰 유효 기간. 지정하지 않으면 설정값(기본 7일) 사용.
        
    Returns:
        str: 인코딩된 JWT 문자열
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        
    # 'type': 'refresh'를 추가하여 토큰 용도를 명시합니다.
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_token(token: str):
    """
    JWT 토큰을 디코딩하고 검증합니다.
    
    Args:
        token (str): 인코딩된 JWT 문자열
        
    Returns:
        dict | None: 유효한 토큰일 경우 디코딩된 페이로드(dict), 그렇지 않으면 None 반환.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None