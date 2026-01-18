def test_resume_page(client):
    # 이력서 페이지 접근 테스트
    response = client.get("/resume")
    assert response.status_code == 200
    assert "Yang Seungmin" in response.text
    assert "Work Experience" in response.text
