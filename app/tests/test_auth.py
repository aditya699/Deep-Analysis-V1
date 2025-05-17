import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

@pytest.mark.asyncio
async def test_request_login():
    """Test the login request endpoint with a real email send"""
    response = client.post(
        "/auth/request-login",
        json={"email": "meenakshi.bhtt@gmail.com"}
    )
    
    # Assert response
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Login instructions sent to your email"
    assert data["success"] is True
    assert data["email"] == "meenakshi.bhtt@gmail.com"
