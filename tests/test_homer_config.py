def test_homer_config_accessible(client):
    # Homer 설정 파일 접근 테스트
    response = client.get("/assets/config.yml")
    assert response.status_code == 200
    assert "title: \"My Web Dashboard\"" in response.text
