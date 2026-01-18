def test_read_root_redirect(client):
    response = client.get("/", follow_redirects=True)
    assert response.status_code == 200
    # 로그인 페이지로 리다이렉트 확인 (HTML 내용에 Login 관련 텍스트가 있어야 함)
    # templates/login.html의 내용을 정확히 모르지만 보통 Login 단어가 있을 것임
    assert "login" in response.text.lower()

def test_register_and_login_flow(client):
    # 1. 회원가입
    response = client.post("/register", data={"username": "testuser", "password": "password"}, follow_redirects=True)
    assert response.status_code == 200
    assert "registration successful" in response.text.lower() or "login" in response.text.lower()

    # 2. 로그인
    response = client.post("/login", data={"username": "testuser", "password": "password"}, follow_redirects=False)
    assert response.status_code == 302 # 리다이렉트 발생
    assert "access_token" in response.cookies
    assert "refresh_token" in response.cookies

    # 3. 루트 접근 (미승인 상태)
    # 쿠키를 사용하여 접근
    client.cookies = response.cookies
    response = client.get("/", follow_redirects=True)
    assert response.status_code == 200
    # pending.html 내용 확인
    assert "pending" in response.text.lower() or "approval" in response.text.lower()

def test_token_refresh(client):
    # 1. 회원가입 및 로그인하여 토큰 획득
    client.post("/register", data={"username": "refreshuser", "password": "password"})
    login_res = client.post("/login", data={"username": "refreshuser", "password": "password"}, follow_redirects=False)
    
    refresh_token = login_res.cookies["refresh_token"]
    
    # 2. Refresh Token으로 새 Access Token 요청
    # client.cookies를 비우고 refresh_token만 설정해서 테스트
    client.cookies.clear()
    client.cookies.set("refresh_token", refresh_token)
    
    response = client.post("/token/refresh")
    assert response.status_code == 200
    assert "access_token" in response.cookies
    # 쿠키 값에 따옴표가 포함될 수 있으므로 제거 후 확인
    assert response.cookies["access_token"].strip('"').startswith("Bearer ")

from app import models, auth



def test_404_page(client, db):

    # 테스트 DB에는 초기 Admin이 없으므로 생성

    hashed_password = auth.get_password_hash("admin")

    admin_user = models.User(username="admin", hashed_password=hashed_password, is_active=True, is_superuser=True)

    db.add(admin_user)

    db.commit()

    

    # 404를 보려면 로그인이 되어 있어야 함

    client.post("/register", data={"username": "404user", "password": "password"})

    

    # 유저 ID 조회

    user = db.query(models.User).filter(models.User.username == "404user").first()

    user_id = user.id

    

    # Admin으로 로그인하여 승인

    admin_login = client.post("/login", data={"username": "admin", "password": "admin"}, follow_redirects=False)

    client.post(f"/admin/approve/{user_id}", cookies=admin_login.cookies)

    

    # 일반 유저로 로그인

    login_res = client.post("/login", data={"username": "404user", "password": "password"}, follow_redirects=False)

    

    # 존재하지 않는 페이지 요청

    response = client.get("/non-existent-page", cookies=login_res.cookies)

    

    assert response.status_code == 404

    assert "Page Not Found" in response.text

    assert "Oops!" in response.text


