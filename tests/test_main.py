from app import models, auth

def test_read_root_redirect(client):
    """
    로그인하지 않은 사용자가 루트 경로 접근 시 로그인 페이지로 리다이렉트되는지 테스트.
    """
    response = client.get("/", follow_redirects=True)
    assert response.status_code == 200
    # 리다이렉트된 최종 페이지(login.html)에 'login' 텍스트가 포함되어 있는지 확인
    assert "login" in response.text.lower()

def test_register_and_login_flow(client):
    """
    회원가입 -> 로그인 -> 루트 페이지 접근(미승인) 흐름을 통합 테스트.
    """
    # 1. 회원가입 요청
    response = client.post("/register", data={"username": "testuser", "password": "password"}, follow_redirects=True)
    assert response.status_code == 200
    assert "registration successful" in response.text.lower() or "login" in response.text.lower()

    # 2. 로그인 요청
    response = client.post("/login", data={"username": "testuser", "password": "password"}, follow_redirects=False)
    assert response.status_code == 302 # 성공 시 리다이렉트(302)
    
    # 쿠키에 토큰이 설정되었는지 확인
    assert "access_token" in response.cookies
    assert "refresh_token" in response.cookies

    # 3. 루트 접근 (미승인 상태 확인)
    # 로그인 응답에서 받은 쿠키 사용
    client.cookies = response.cookies
    response = client.get("/", follow_redirects=True)
    assert response.status_code == 200
    # pending.html 내용 확인 (대기 중 메시지)
    assert "pending" in response.text.lower() or "approval" in response.text.lower()

def test_token_refresh(client):
    """
    Refresh Token을 이용해 Access Token을 갱신하는 기능 테스트.
    """
    # 1. 회원가입 및 로그인하여 초기 토큰 획득
    client.post("/register", data={"username": "refreshuser", "password": "password"})
    login_res = client.post("/login", data={"username": "refreshuser", "password": "password"}, follow_redirects=False)
    
    refresh_token = login_res.cookies["refresh_token"]
    
    # 2. Access Token 없이 Refresh Token만으로 갱신 요청
    client.cookies.clear()
    client.cookies.set("refresh_token", refresh_token)
    
    response = client.post("/token/refresh")
    assert response.status_code == 200
    
    # 새로운 Access Token 발급 확인
    assert "access_token" in response.cookies
    # 쿠키 값 포맷 확인 (따옴표 제거 후 Bearer 시작 여부)
    assert response.cookies["access_token"].strip('"').startswith("Bearer ")

def test_404_page(client, db):
    """
    로그인한 사용자가 존재하지 않는 페이지 요청 시 커스텀 404 페이지가 표시되는지 테스트.
    """
    # 1. 테스트 DB에 초기 Admin 사용자 수동 생성 (fixture는 빈 DB 제공)
    hashed_password = auth.get_password_hash("admin")
    admin_user = models.User(username="admin", hashed_password=hashed_password, is_active=True, is_superuser=True)
    db.add(admin_user)
    db.commit()
    
    # 2. 테스트용 일반 유저 생성
    client.post("/register", data={"username": "404user", "password": "password"})
    
    # 생성된 유저 ID 조회
    user = db.query(models.User).filter(models.User.username == "404user").first()
    user_id = user.id
    
    # 3. Admin으로 로그인하여 일반 유저 승인 처리
    admin_login = client.post("/login", data={"username": "admin", "password": "admin"}, follow_redirects=False)
    client.post(f"/admin/approve/{user_id}", cookies=admin_login.cookies)
    
    # 4. 승인된 일반 유저로 다시 로그인
    login_res = client.post("/login", data={"username": "404user", "password": "password"}, follow_redirects=False)
    
    # 5. 존재하지 않는 페이지 요청
    response = client.get("/non-existent-page", cookies=login_res.cookies)
    
    # 6. 404 상태 코드 및 커스텀 페이지 내용 확인
    assert response.status_code == 404
    assert "Page Not Found" in response.text
    assert "Oops!" in response.text