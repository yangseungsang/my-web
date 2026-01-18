from app import auth

def test_hash_password():
    password = "secret"
    hashed = auth.get_password_hash(password)
    assert auth.verify_password(password, hashed)
    assert not auth.verify_password("wrong", hashed)

def test_access_token():
    data = {"sub": "testuser"}
    token = auth.create_access_token(data)
    decoded = auth.decode_token(token)
    assert decoded["sub"] == "testuser"
    assert decoded["type"] == "access"

def test_refresh_token():
    data = {"sub": "testuser"}
    token = auth.create_refresh_token(data)
    decoded = auth.decode_token(token)
    assert decoded["sub"] == "testuser"
    assert decoded["type"] == "refresh"
