from pydantic import BaseModel

# 공통 사용자 속성
class UserBase(BaseModel):
    username: str

# 회원가입 시 클라이언트로부터 받는 데이터 모델
class UserCreate(BaseModel):
    username: str
    password: str

# API 응답 등으로 사용자 정보를 반환할 때 사용하는 모델 (DB 모델과 매핑)
class User(UserBase):
    id: int
    is_active: bool
    is_superuser: bool

    class Config:
        # ORM 모델(SQLAlchemy) 객체로부터 데이터를 읽을 수 있도록 설정
        from_attributes = True

# 토큰 응답 모델
class Token(BaseModel):
    access_token: str
    token_type: str

# 토큰 디코딩 후 추출한 데이터 모델
class TokenData(BaseModel):
    username: str | None = None