from sqlalchemy import Boolean, Column, Integer, String
from .database import Base

class User(Base):
    """
    사용자(User) 정보를 저장하는 데이터베이스 모델입니다.
    """
    __tablename__ = "users"

    # 기본 키 (Primary Key)
    id = Column(Integer, primary_key=True, index=True)
    
    # 사용자 이름 (고유값, 인덱스 설정됨)
    username = Column(String, unique=True, index=True)
    
    # 해시된 비밀번호 (평문 비밀번호 저장 금지)
    hashed_password = Column(String)
    
    # 계정 활성 상태 (관리자 승인 여부). 기본값은 False(비활성)입니다.
    is_active = Column(Boolean, default=False)
    
    # 관리자 권한 여부. True일 경우 관리자 페이지 접근 가능.
    is_superuser = Column(Boolean, default=False)