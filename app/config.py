import os
from dotenv import load_dotenv

# .env 파일에서 환경 변수를 로드합니다.
load_dotenv()

class Settings:
    """
    애플리케이션 전반에서 사용되는 설정 값들을 관리하는 클래스입니다.
    환경 변수에서 값을 읽어오며, 값이 없을 경우 기본값을 사용합니다.
    """
    # JWT 토큰 서명에 사용할 비밀키 (운영 환경에서는 반드시 강력한 비밀키로 변경 필요)
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-fallback-secret-key")
    
    # JWT 토큰 암호화 알고리즘
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    
    # Access Token 유효 시간 (분)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
    
    # Refresh Token 유효 기간 (일)
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))
    
    # 데이터베이스 연결 URL (기본값: 로컬 SQLite 파일)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./app.db")

# 설정 인스턴스 생성 (싱글톤처럼 사용)
settings = Settings()