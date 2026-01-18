from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from .config import settings

# 설정에서 데이터베이스 URL을 가져옵니다.
SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

# SQLAlchemy 엔진 생성
# connect_args={"check_same_thread": False}는 SQLite에서만 필요하며,
# 한 스레드에서 생성된 객체를 다른 스레드에서 사용할 수 있게 합니다.
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# 데이터베이스 세션 클래스 생성
# autocommit=False: 트랜잭션을 수동으로 제어
# autoflush=False: 세션의 변경 사항을 자동으로 DB에 반영하지 않음 (수동 flush/commit 필요)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ORM 모델들이 상속받을 기본 클래스
Base = declarative_base()