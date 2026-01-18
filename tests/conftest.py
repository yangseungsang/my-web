import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.database import Base
from app.main import app, get_db

# 테스트용 인메모리 SQLite DB URL
# 메모리 내에서만 동작하므로 속도가 빠르고 테스트 간 격리가 쉽습니다.
SQLALCHEMY_DATABASE_URL = "sqlite://"

# 테스트용 DB 엔진 생성
# StaticPool: 모든 연결이 동일한 스레드와 메모리 연결을 공유하도록 설정 (인메모리 DB 특성상 필요)
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db():
    """
    각 테스트 함수마다 실행되는 DB 세션 Fixture.
    테스트 시작 전 테이블을 생성하고, 종료 후 모두 삭제(drop)하여 상태를 초기화합니다.
    """
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db):
    """
    FastAPI TestClient Fixture.
    앱의 'get_db' 의존성을 테스트용 DB 세션으로 덮어씌웁니다(override).
    """
    def override_get_db():
        try:
            yield db
        finally:
            db.close()
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c