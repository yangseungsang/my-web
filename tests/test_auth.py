from app import auth

def test_hash_password():
    """
    비밀번호 해싱 및 검증 로직 테스트.
    """
    password = "secret"
    hashed = auth.get_password_hash(password)
    # 올바른 비밀번호 검증
    assert auth.verify_password(password, hashed)
    # 틀린 비밀번호 검증
    assert not auth.verify_password("wrong", hashed)

def test_access_token():
    """
    Access Token 생성 및 디코딩 테스트.
    토큰 타입('access')이 올바르게 설정되었는지 확인합니다.
    """
    data = {"sub": "testuser"}
    token = auth.create_access_token(data)
    decoded = auth.decode_token(token)
    assert decoded["sub"] == "testuser"
    assert decoded["type"] == "access"

def test_refresh_token():
    """
    Refresh Token 생성 및 디코딩 테스트.
    토큰 타입('refresh')이 올바르게 설정되었는지 확인합니다.
    """
    data = {"sub": "testuser"}
    token = auth.create_refresh_token(data)
    decoded = auth.decode_token(token)
    assert decoded["sub"] == "testuser"
    assert decoded["type"] == "refresh"